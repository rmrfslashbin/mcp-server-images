"""ModelsLab image generation client."""

import asyncio
import logging
from enum import Enum
from pathlib import Path
from typing import Any, Dict, Optional

import httpx

logger = logging.getLogger(__name__)


class ModelsLabModel(str, Enum):
    """Valid models for ModelsLab API"""

    FLUX = "flux"


class ModelsLabClient:
    """Client for ModelsLab image generation."""

    def __init__(self, api_key: str, base_url: str = "https://modelslab.com/api/v6/images"):
        self.api_key = api_key
        self.base_url = base_url
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "accept": "application/json",
                "Content-Type": "application/json",
            },
            timeout=120.0,
        )

    def _validate_model(self, model: str) -> str:
        """Validate and normalize model name."""
        try:
            return ModelsLabModel(model).value
        except ValueError:
            logger.warning(f"Invalid ModelsLab model {model}, using default flux")
            return ModelsLabModel.FLUX.value

    def _convert_aspect_ratio_to_dimensions(self, aspect_ratio: str) -> tuple[int, int]:
        """Convert aspect ratio to width/height dimensions."""
        aspect_map = {
            "16:9": (1024, 576),
            "1:1": (1024, 1024),
            "21:9": (1024, 440),
            "2:3": (680, 1024),
            "3:2": (1024, 680),
            "4:5": (816, 1024),
            "5:4": (1024, 816),
            "9:16": (576, 1024),
            "9:21": (440, 1024),
        }

        return aspect_map.get(aspect_ratio, (1024, 1024))

    async def _download_image(self, image_url: str, output_path: Optional[Path]) -> bytes:
        """Download generated image and optionally save it to disk."""
        async with httpx.AsyncClient() as dl_client:
            img_response = await dl_client.get(image_url)
            img_response.raise_for_status()

            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(img_response.content)
                logger.info(f"Image saved to: {output_path}")

            return img_response.content

    async def _poll_result(self, request_id: str) -> Dict[str, Any]:
        """Poll ModelsLab fetch endpoint until a queued image is ready."""
        max_attempts = 120
        attempt = 0

        while attempt < max_attempts:
            await asyncio.sleep(1.0)
            attempt += 1

            response = await self.client.post(
                "/fetch",
                json={"key": self.api_key, "request_id": request_id},
            )
            response.raise_for_status()
            data = response.json()
            status = data.get("status")
            logger.debug(f"ModelsLab generation status: {status} (attempt {attempt})")

            if status == "success":
                return data
            if status == "error":
                message = data.get("message") or data.get("messege") or "Unknown error"
                raise RuntimeError(f"ModelsLab API Error: {message}")

        raise RuntimeError(f"ModelsLab generation timed out after {max_attempts} seconds")

    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        model: str = "flux",
        aspect_ratio: str = "1:1",
        cfg_scale: float = 7.0,
        seed: Optional[int] = None,
        output_path: Path = None,
    ) -> Dict[str, Any]:
        """Generate image using ModelsLab API."""

        model = self._validate_model(model)
        width, height = self._convert_aspect_ratio_to_dimensions(aspect_ratio)
        cfg_scale = max(1.0, min(20.0, cfg_scale))

        try:
            payload = {
                "key": self.api_key,
                "model_id": model,
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "width": width,
                "height": height,
                "samples": 1,
                "num_inference_steps": 31,
                "guidance_scale": cfg_scale,
                "safety_checker": "yes",
            }

            if seed is not None:
                payload["seed"] = seed

            logger.info(f"Generating image with ModelsLab: {model}")
            logger.debug(f"Prompt: {prompt[:100]}...")

            response = await self.client.post("/text2img", json=payload)

            if response.status_code == 429:
                raise RuntimeError("ModelsLab rate limit exceeded")
            if response.status_code != 200:
                try:
                    error_json = response.json()
                    error_msg = (
                        error_json.get("message")
                        or error_json.get("messege")
                        or f"HTTP {response.status_code}"
                    )
                    raise RuntimeError(f"ModelsLab API Error: {error_msg}")
                except Exception:
                    raise RuntimeError(
                        f"ModelsLab API Error: {response.status_code} - {response.text}"
                    )

            data = response.json()
            status = data.get("status")

            if status == "processing":
                request_id = str(data["id"])
                logger.info(f"ModelsLab generation queued, ID: {request_id}")
                data = await self._poll_result(request_id)
            elif status == "error":
                message = data.get("message") or data.get("messege") or "Unknown error"
                raise RuntimeError(f"ModelsLab API Error: {message}")
            elif status != "success":
                raise RuntimeError(f"Unexpected ModelsLab API status: {status}")

            output = data.get("output") or []
            if not output:
                raise RuntimeError("ModelsLab API did not return an output image")

            image_url = output[0]
            image_content = await self._download_image(image_url, output_path)
            meta = data.get("meta") or {}

            return {
                "success": True,
                "provider": "modelslab",
                "model": model,
                "image_size": len(image_content),
                "parameters": {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "model": model,
                    "width": width,
                    "height": height,
                    "aspect_ratio": aspect_ratio,
                    "cfg_scale": cfg_scale,
                    "seed": seed,
                    "actual_seed": meta.get("seed", seed),
                    "output_format": "png",
                },
                "request_id": data.get("id"),
                "image_url": image_url,
            }

        except httpx.TimeoutException:
            raise RuntimeError("Request timed out - ModelsLab API took too long to respond")
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to generate image: {str(e)}")

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()
