"""MCP server for AI-powered image generation."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, Optional

from mcp.server import Server
from mcp.types import (
    Tool,
    TextContent,
    ImageContent,
    EmbeddedResource,
)
import mcp.server.stdio

from .providers import StabilityClient, BFLClient
from .utils import generate_filename

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize the MCP server
server = Server("mcp-server-images")


@server.list_tools()
async def list_tools() -> list[Tool]:
    """List available image generation tools."""
    return [
        Tool(
            name="generate_image",
            description="Generate images from text prompts using AI image generation models",
            inputSchema={
                "type": "object",
                "properties": {
                    "prompt": {
                        "type": "string",
                        "description": "Detailed text description of the image to generate",
                    },
                    "negative_prompt": {
                        "type": "string",
                        "description": "Things to avoid in the image (not supported by BFL)",
                    },
                    "provider": {
                        "type": "string",
                        "enum": ["stability", "bfl"],
                        "description": "Image generation provider",
                        "default": "stability",
                    },
                    "model": {
                        "type": "string",
                        "description": "Specific model to use (e.g., 'sd3.5-large', 'flux-pro-1.1')",
                    },
                    "aspect_ratio": {
                        "type": "string",
                        "enum": ["16:9", "1:1", "21:9", "2:3", "3:2", "4:5", "5:4", "9:16", "9:21"],
                        "description": "Image aspect ratio",
                        "default": "1:1",
                    },
                    "cfg_scale": {
                        "type": "number",
                        "minimum": 1.0,
                        "maximum": 10.0,
                        "description": "Classifier free guidance scale (Stability AI only)",
                        "default": 7.0,
                    },
                    "seed": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 4294967294,
                        "description": "Seed for reproducible generation",
                    },
                    "output_dir": {
                        "type": "string",
                        "description": "Output directory for generated images",
                        "default": "./images",
                    },
                    "filename_template": {
                        "type": "string",
                        "description": "Template for generated filenames",
                        "default": "{{.Timestamp}}-{{.Subject}}",
                    },
                },
                "required": ["prompt"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: Dict[str, Any]) -> list[TextContent | ImageContent]:
    """Handle tool calls for image generation."""
    if name == "generate_image":
        return await generate_image_tool(**arguments)
    else:
        raise ValueError(f"Unknown tool: {name}")


async def generate_image_tool(
    prompt: str,
    negative_prompt: Optional[str] = None,
    provider: str = "stability",
    model: Optional[str] = None,
    aspect_ratio: str = "1:1",
    cfg_scale: float = 7.0,
    seed: Optional[int] = None,
    output_dir: str = "./images",
    filename_template: str = "{{.Timestamp}}-{{.Subject}}",
) -> list[TextContent]:
    """Generate an image using the specified provider and parameters."""
    
    logger.info(f"Generating image: {prompt[:50]}...")
    logger.info(f"Provider: {provider}, Model: {model}, Aspect: {aspect_ratio}")
    
    try:
        # Validate provider
        if provider not in ["stability", "bfl"]:
            raise ValueError(f"Unsupported provider: {provider}. Use 'stability' or 'bfl'")
        
        # Get API keys from environment
        if provider == "stability":
            api_key = os.getenv("STABILITY_API_KEY")
            if not api_key:
                raise ValueError("STABILITY_API_KEY environment variable not set")
            default_model = "sd3.5-large"
        else:  # bfl
            api_key = os.getenv("BFL_API_KEY")
            if not api_key:
                raise ValueError("BFL_API_KEY environment variable not set")
            default_model = "flux-pro-1.1"
        
        # Use default model if not specified
        if not model:
            model = default_model
        
        # Generate filename
        output_path = generate_filename(
            template=filename_template,
            prompt=prompt,
            provider=provider,
            model=model,
            output_dir=Path(output_dir),
            extension="png"
        )
        
        # Create output directory
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Generate image based on provider
        if provider == "stability":
            client = StabilityClient(api_key)
            try:
                result = await client.generate_image(
                    prompt=prompt,
                    negative_prompt=negative_prompt,
                    model=model,
                    aspect_ratio=aspect_ratio,
                    cfg_scale=cfg_scale,
                    seed=seed,
                    output_path=output_path
                )
            finally:
                await client.close()
                
        else:  # bfl
            client = BFLClient(api_key)
            try:
                result = await client.generate_image(
                    prompt=prompt,
                    negative_prompt=negative_prompt,  # Will be ignored by BFL
                    model=model,
                    aspect_ratio=aspect_ratio,
                    cfg_scale=cfg_scale,  # Will be ignored by BFL
                    seed=seed,  # Will be ignored by BFL
                    output_path=output_path
                )
            finally:
                await client.close()
        
        # Format success response
        file_size_mb = result["image_size"] / (1024 * 1024)
        actual_seed = result["parameters"].get("actual_seed", seed or "random")
        
        response_text = f"""✅ **Image Generated Successfully!**

**File Details:**
- **Saved to:** `{output_path.name}`
- **Full path:** `{output_path}`
- **File size:** {file_size_mb:.1f} MB

**Generation Parameters:**
- **Provider:** {provider.title()}
- **Model:** {result['model']}
- **Prompt:** {prompt}"""

        if negative_prompt and provider == "stability":
            response_text += f"\n- **Negative prompt:** {negative_prompt}"
        
        response_text += f"""
- **Aspect ratio:** {aspect_ratio}
- **Seed:** {actual_seed}"""

        if provider == "stability":
            response_text += f"\n- **CFG scale:** {cfg_scale}"

        response_text += f"""

**Template Applied:** `{filename_template}`

The image has been saved and is ready for use!

**💡 Tip:** Use `open_file(path="{output_path}")` to view the image or `reveal_file(path="{output_path}")` to show it in your file manager."""

        return [TextContent(type="text", text=response_text)]
        
    except Exception as e:
        error_msg = f"❌ **Image Generation Failed**\n\n**Error:** {str(e)}\n\n**Parameters:**\n- Provider: {provider}\n- Model: {model}\n- Prompt: {prompt[:100]}..."
        logger.error(f"Image generation failed: {str(e)}")
        return [TextContent(type="text", text=error_msg)]


async def main():
    """Run the MCP server."""
    logger.info("Starting MCP Image Generation Server...")
    
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())