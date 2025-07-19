"""MCP server for AI-powered image generation."""

import asyncio
import logging
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
    """Generate an image directly from provided parameters - no prompt optimization needed."""
    
    logger.info(f"Generating image: {prompt[:50]}...")
    logger.info(f"Provider: {provider}, Model: {model}, Aspect: {aspect_ratio}")
    
    # Create output directory
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # TODO: Implement direct image generation
    # 1. Apply filename template with timestamp and subject extraction
    # 2. Call provider API directly (no Claude needed)
    # 3. Save image with generated filename
    # 4. Return metadata and file path
    
    # For now, return a placeholder that shows the simplified design
    result_text = f"""Image generation request received!

**Direct Generation (No Dual Pipes):**
- Prompt: {prompt}
- Negative: {negative_prompt or 'None'}
- Provider: {provider}
- Model: {model or f'default-{provider}'}
- Aspect: {aspect_ratio}
- CFG Scale: {cfg_scale}
- Seed: {seed or 'random'}

**Simplified Design:**
✅ LLM provides optimized prompt directly
✅ MCP server handles image generation only
✅ No secondary Claude API call needed
✅ Filename templating: {filename_template}

**Next Steps:**
1. Implement direct provider clients (Stability AI, BFL)
2. Add filename templating with timestamp patterns
3. Save images and return metadata
4. Error handling and validation

This design is much cleaner - the calling LLM does the prompt optimization!"""
    
    return [TextContent(type="text", text=result_text)]


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