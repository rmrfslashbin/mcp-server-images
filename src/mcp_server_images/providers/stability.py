"""Stability AI image generation client."""

import httpx
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class StabilityModel(str, Enum):
    """Valid models for Stability AI API"""
    SD3_LARGE = "sd3-large"
    SD3_LARGE_TURBO = "sd3-large-turbo"
    SD3_MEDIUM = "sd3-medium"
    SD35_LARGE = "sd3.5-large"
    SD35_LARGE_TURBO = "sd3.5-large-turbo"
    SD35_MEDIUM = "sd3.5-medium"


class AspectRatio(str, Enum):
    """Valid aspect ratios for Stability AI API"""
    RATIO_16_9 = "16:9"
    RATIO_1_1 = "1:1"
    RATIO_21_9 = "21:9"
    RATIO_2_3 = "2:3"
    RATIO_3_2 = "3:2"
    RATIO_4_5 = "4:5"
    RATIO_5_4 = "5:4"
    RATIO_9_16 = "9:16"
    RATIO_9_21 = "9:21"


class StabilityClient:
    """Client for Stability AI image generation."""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.client = httpx.AsyncClient(
            base_url="https://api.stability.ai",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Accept": "image/*",
                "stability-client-id": "mcp-server-images",
                "stability-client-version": "1.0.0"
            },
            timeout=120.0  # Extended timeout for image generation
        )
    
    def _validate_model(self, model: str) -> str:
        """Validate and normalize model name."""
        try:
            return StabilityModel(model).value
        except ValueError:
            logger.warning(f"Invalid model {model}, using default sd3.5-large")
            return StabilityModel.SD35_LARGE.value
    
    def _validate_aspect_ratio(self, aspect_ratio: str) -> str:
        """Validate and normalize aspect ratio."""
        try:
            return AspectRatio(aspect_ratio).value
        except ValueError:
            logger.warning(f"Invalid aspect ratio {aspect_ratio}, using default 1:1")
            return AspectRatio.RATIO_1_1.value
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,
        model: str = "sd3.5-large",
        aspect_ratio: str = "1:1",
        cfg_scale: float = 7.0,
        seed: Optional[int] = None,
        output_path: Path = None
    ) -> Dict[str, Any]:
        """Generate image using Stability AI API."""
        
        # Validate inputs
        model = self._validate_model(model)
        aspect_ratio = self._validate_aspect_ratio(aspect_ratio)
        
        # Validate prompt length
        if len(prompt) > 10000:
            raise ValueError("Prompt must be 10000 characters or less")
        if negative_prompt and len(negative_prompt) > 10000:
            raise ValueError("Negative prompt must be 10000 characters or less")
        
        # Don't use negative prompt with turbo models
        if negative_prompt and model in [StabilityModel.SD3_LARGE_TURBO, StabilityModel.SD35_LARGE_TURBO]:
            logger.warning("Negative prompts not supported with turbo models. Ignoring negative prompt.")
            negative_prompt = None
        
        # Clamp cfg_scale
        cfg_scale = max(1.0, min(10.0, cfg_scale))
        
        try:
            # Prepare form data
            form_data = {
                "prompt": (None, prompt),
                "output_format": (None, "png"),
                "cfg_scale": (None, str(cfg_scale)),
                "aspect_ratio": (None, aspect_ratio)
            }
            
            # Add optional parameters
            if seed is not None:
                form_data["seed"] = (None, str(seed))
            
            if negative_prompt:
                form_data["negative_prompt"] = (None, negative_prompt)
            
            logger.info(f"Generating image with Stability AI: {model}")
            logger.debug(f"Prompt: {prompt[:100]}...")
            
            # Make API request
            response = await self.client.post(
                "/v2beta/stable-image/generate/sd3",
                files=form_data,
                timeout=120.0
            )
            
            # Check response
            if response.status_code != 200:
                try:
                    error_json = response.json()
                    error_msg = error_json.get('message', f'HTTP {response.status_code}')
                    raise RuntimeError(f"Stability AI API Error: {error_msg}")
                except Exception:
                    raise RuntimeError(f"Stability AI API Error: {response.status_code} - {response.text}")
            
            # Extract seed from response headers
            response_seed = response.headers.get("Seed")
            
            # Save image if output path provided
            if output_path:
                output_path.parent.mkdir(parents=True, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(response.content)
                logger.info(f"Image saved to: {output_path}")
            
            # Return generation result
            result = {
                "success": True,
                "provider": "stability",
                "model": model,
                "image_size": len(response.content),
                "parameters": {
                    "prompt": prompt,
                    "negative_prompt": negative_prompt,
                    "model": model,
                    "aspect_ratio": aspect_ratio,
                    "cfg_scale": cfg_scale,
                    "seed": seed,
                    "output_format": "png"
                }
            }
            
            # Add response seed if available
            if response_seed:
                try:
                    result["parameters"]["actual_seed"] = int(response_seed)
                except ValueError:
                    logger.warning(f"Invalid seed in response: {response_seed}")
            
            return result
            
        except httpx.TimeoutException:
            raise RuntimeError("Request timed out - image generation took too long")
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to generate image: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()