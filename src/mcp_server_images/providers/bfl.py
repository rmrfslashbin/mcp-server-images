"""Black Forest Labs image generation client."""

import httpx
import asyncio
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from enum import Enum

logger = logging.getLogger(__name__)


class BFLModel(str, Enum):
    """Valid models for Black Forest Labs API"""
    FLUX_PRO_11_ULTRA = "flux-pro-1.1-ultra"
    FLUX_PRO_11 = "flux-pro-1.1"
    FLUX_PRO = "flux-pro"
    FLUX_DEV = "flux-dev"


class BFLClient:
    """Client for Black Forest Labs image generation."""
    
    def __init__(self, api_key: str, base_url: str = "https://api.us1.bfl.ai/v1"):
        self.api_key = api_key
        self.base_url = base_url
        
        # Clean API key (remove prefix if present)
        api_key_clean = api_key.replace('bfl_', '') if api_key.startswith('bfl_') else api_key
        
        self.client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "x-key": api_key_clean,
                "accept": "application/json",
                "Content-Type": "application/json"
            },
            timeout=120.0
        )
    
    def _validate_model(self, model: str) -> str:
        """Validate and normalize model name."""
        try:
            return BFLModel(model).value
        except ValueError:
            logger.warning(f"Invalid BFL model {model}, using default flux-pro-1.1")
            return BFLModel.FLUX_PRO_11.value
    
    def _convert_aspect_ratio_to_dimensions(self, aspect_ratio: str) -> tuple[int, int]:
        """Convert aspect ratio to width/height dimensions."""
        # BFL uses pixel dimensions, not aspect ratio strings
        aspect_map = {
            "16:9": (1344, 768),
            "1:1": (1024, 1024),
            "21:9": (1536, 640),
            "2:3": (832, 1216),
            "3:2": (1216, 832),
            "4:5": (896, 1152),
            "5:4": (1152, 896),
            "9:16": (768, 1344),
            "9:21": (640, 1536),
        }
        
        return aspect_map.get(aspect_ratio, (1024, 1024))
    
    async def generate_image(
        self,
        prompt: str,
        negative_prompt: Optional[str] = None,  # Ignored - BFL doesn't support negative prompts
        model: str = "flux-pro-1.1",
        aspect_ratio: str = "1:1",
        cfg_scale: float = 7.0,  # Ignored - BFL doesn't support CFG scale
        seed: Optional[int] = None,  # Ignored - BFL doesn't support custom seeds
        output_path: Path = None
    ) -> Dict[str, Any]:
        """Generate image using Black Forest Labs API."""
        
        # Validate and normalize model
        model = self._validate_model(model)
        
        # Convert aspect ratio to dimensions
        width, height = self._convert_aspect_ratio_to_dimensions(aspect_ratio)
        
        # Log ignored parameters
        if negative_prompt:
            logger.info("BFL doesn't support negative prompts - parameter ignored")
        if cfg_scale != 7.0:
            logger.info("BFL doesn't support cfg_scale - parameter ignored")
        if seed is not None:
            logger.info("BFL doesn't support custom seeds - parameter ignored")
        
        try:
            logger.info(f"Generating image with BFL: {model}")
            logger.debug(f"Prompt: {prompt[:100]}...")
            
            # Submit generation request
            response = await self.client.post(
                f"/{model}",
                json={
                    "prompt": prompt,
                    "width": width,
                    "height": height
                }
            )
            
            # Handle specific BFL error codes
            if response.status_code == 402:
                raise RuntimeError("Insufficient BFL credits")
            elif response.status_code == 429:
                raise RuntimeError("Too many active BFL tasks")
            elif response.status_code != 200:
                try:
                    error_json = response.json()
                    error_msg = error_json.get('message', f'HTTP {response.status_code}')
                    raise RuntimeError(f"BFL API Error: {error_msg}")
                except Exception:
                    raise RuntimeError(f"BFL API Error: {response.status_code} - {response.text}")
            
            # Get request ID
            request_data = response.json()
            request_id = request_data["id"]
            logger.info(f"BFL generation started, ID: {request_id}")
            
            # Poll for results
            max_attempts = 120  # 2 minutes at 1 second intervals
            attempt = 0
            
            while attempt < max_attempts:
                await asyncio.sleep(1.0)  # Wait 1 second between polls
                attempt += 1
                
                result_response = await self.client.get(
                    "/get_result",
                    params={"id": request_id}
                )
                result_response.raise_for_status()
                result_data = result_response.json()
                
                status = result_data["status"]
                logger.debug(f"BFL generation status: {status} (attempt {attempt})")
                
                if status == "Ready":
                    # Download image from signed URL
                    image_url = result_data["result"]["sample"]
                    
                    async with httpx.AsyncClient() as dl_client:
                        img_response = await dl_client.get(image_url)
                        img_response.raise_for_status()
                        
                        # Save image if output path provided
                        if output_path:
                            output_path.parent.mkdir(parents=True, exist_ok=True)
                            with open(output_path, "wb") as f:
                                f.write(img_response.content)
                            logger.info(f"Image saved to: {output_path}")
                        
                        # Return generation result
                        return {
                            "success": True,
                            "provider": "bfl",
                            "model": model,
                            "image_size": len(img_response.content),
                            "parameters": {
                                "prompt": prompt,
                                "model": model,
                                "width": width,
                                "height": height,
                                "aspect_ratio": aspect_ratio,
                                "output_format": "png"
                            },
                            "request_id": request_id
                        }
                
                elif status == "Failed":
                    error_msg = result_data.get('error', 'Unknown error')
                    raise RuntimeError(f"BFL generation failed: {error_msg}")
            
            # Timeout after max attempts
            raise RuntimeError(f"BFL generation timed out after {max_attempts} seconds")
            
        except httpx.TimeoutException:
            raise RuntimeError("Request timed out - BFL API took too long to respond")
        except httpx.HTTPError as e:
            raise RuntimeError(f"HTTP error: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to generate image: {str(e)}")
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()