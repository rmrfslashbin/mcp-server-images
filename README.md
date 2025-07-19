# MCP Server - Images

A Model Context Protocol (MCP) server for AI-powered image generation using Stability AI and Black Forest Labs APIs.

## Features

- **Multi-provider support**: Stability AI (Stable Diffusion) and Black Forest Labs (Flux models)
- **Direct generation**: Accepts optimized prompts directly from calling LLM (no dual pipes)
- **Flexible filename templates**: Customizable output filenames with timestamp, provider, model, and content-based variables
- **Comprehensive metadata**: Full tracking of generation parameters, checksums, and provenance
- **Professional error handling**: Detailed error reporting and retry mechanisms
- **MCP standard compliance**: Works with any MCP-compatible client

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/rmrfslashbin/mcp-server-images.git
cd mcp-server-images

# Install dependencies
uv sync
```

### Configuration

Configure via environment variables:

```bash
STABILITY_API_KEY=sk-...     # Required for Stability AI
BFL_API_KEY=...              # Required for Black Forest Labs
```

### Usage with MCP Client

```bash
# Run the server
uv run mcp-server-images

# Or via Python
python -m mcp_server_images
```

## MCP Tools

### `generate_image`

Generate images from text prompts with AI-optimized prompting.

**Parameters:**
- `prompt` (required): Detailed, optimized text description of the image to generate
- `negative_prompt` (optional): Things to avoid in the image (Stability AI only)
- `provider` (optional): "stability" or "bfl" (default: "stability")
- `model` (optional): Specific model to use (e.g., "sd3.5-large", "flux-pro-1.1")
- `aspect_ratio` (optional): Image aspect ratio (default: "1:1")
- `cfg_scale` (optional): Classifier free guidance scale 1.0-10.0 (Stability AI only)
- `seed` (optional): Seed for reproducible generation
- `output_dir` (optional): Output directory (default: "./images")
- `filename_template` (optional): Template for generated filenames

**Example:**
```json
{
  "name": "generate_image",
  "arguments": {
    "prompt": "A majestic mountain landscape at golden hour, with a pristine lake reflecting the warm sunset colors, ancient pine trees framing the composition, volumetric lighting through misty atmosphere, highly detailed digital painting style",
    "negative_prompt": "blurry, low quality, oversaturated, distorted, artificial",
    "provider": "stability",
    "model": "sd3.5-large",
    "aspect_ratio": "16:9",
    "cfg_scale": 7.5,
    "filename_template": "{{.Timestamp}}-{{.Provider}}-{{.Subject}}"
  }
}
```

## Filename Templates

Customize output filenames using template variables:

- `{{.Timestamp}}`: mmddyy.hhmmss format
- `{{.Date}}`: mmddyy format  
- `{{.Time}}`: hhmmss format
- `{{.Provider}}`: "stability" or "bfl"
- `{{.Model}}`: Model name (e.g., "sd3.5-large")
- `{{.Subject}}`: Cleaned main subject from prompt
- `{{.Hash}}`: Short hash of the prompt
- `{{.Counter}}`: Auto-incrementing counter

**Example templates:**
- `"{{.Timestamp}}-{{.Subject}}"` → `071825.143022-mountain_landscape.png`
- `"{{.Date}}.{{.Time}}-{{.Provider}}-{{.Model}}"` → `071825.143022-stability-sd35-large.png`
- `"img_{{.Counter}}_{{.Hash}}"` → `img_001_a7b2c9d8.png`

## Supported Providers

### Stability AI
- **Models**: sd3-large, sd3-large-turbo, sd3-medium, sd3.5-large, sd3.5-large-turbo, sd3.5-medium
- **Features**: Negative prompts, CFG scale control, multiple aspect ratios
- **API**: Stability AI REST API v2

### Black Forest Labs  
- **Models**: flux-pro-1.1, flux-pro-1.1-ultra, flux-pro, flux-dev
- **Features**: High-quality generation, fast turnaround
- **API**: BFL REST API v1

## Integration

### With Chatterbox

Add to your `config.yaml`:

```yaml
mcp:
  servers:
    images:
      command: "uv"
      args: ["run", "mcp-server-images"]
      env:
        STABILITY_API_KEY: "sk-..."
        BFL_API_KEY: "..."
      config:
        output_dir: "./images"
        filename_template: "{{.Timestamp}}-{{.Provider}}-{{.Subject}}"
```

### With Other MCP Clients

This server works with any MCP-compatible client including:
- Claude Desktop
- Cline (VS Code extension)
- Continue (VS Code extension)
- Custom MCP clients

## Development

```bash
# Install development dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run ruff format .

# Lint code  
uv run ruff check .
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## Related Projects

- [chatterbox](https://github.com/rmrfslashbin/chatterbox) - AI chat interface with MCP support
- [mkimg](https://github.com/rmrfslashbin/mkimg) - Original Python image generation pipeline
- [MCP Servers](https://github.com/modelcontextprotocol/servers) - Official MCP server implementations