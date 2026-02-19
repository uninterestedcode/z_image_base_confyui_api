# Z-Image ComfyUI Serverless API

A queue-based serverless endpoint for ComfyUI image generation on RunPod. This API provides fast, scalable image generation using the Z-Image model with automatic queue management and direct image responses.

## Features

- **Queue-based serverless endpoint** on RunPod with automatic scaling
- **Direct image responses** - images returned as base64 in API response (no persistent storage)
- **Flexible workflow** - use full ComfyUI workflow or simple prompt-based generation
- **Production-ready** - comprehensive error handling, logging, and monitoring
- **GitHub integration** - automated deployments via GitHub Actions

## Architecture

```
┌─────────────┐     ┌──────────────┐     ┌─────────────┐
│   Client    │────▶│  RunPod API  │────▶│   Handler   │
└─────────────┘     └──────────────┘     └──────┬──────┘
                                                │
                                                ▼
                                        ┌──────────────┐
                                        │  ComfyUI     │
                                        │  (port 8188) │
                                        └──────────────┘
```

## Project Structure

```
z_image_base_confyui_api/
├── Dockerfile              # Container configuration
├── handler.py              # Main RunPod serverless handler
├── workflow.json           # ComfyUI workflow definition
├── requirements.txt         # Python dependencies
├── utils/                  # Utility modules
│   ├── comfyui_executor.py # Workflow execution
│   ├── image_processor.py  # Image encoding
│   ├── validators.py       # Input validation
│   └── logger.py           # Logging configuration
└── tests/                  # Test suite
```

## Quick Start

### 1. Local Testing with Docker

```bash
# Build the Docker image
docker build -t z_image_base_confyui_api .

# Run the container locally
docker run -p 8000:8000 z_image_base_confyui_api

# Test the endpoint
curl -X POST http://localhost:8000/run \
  -H "Content-Type: application/json" \
  -d @example-request.json
```

### 2. Deploy to RunPod

#### Option A: Manual Deployment

1. **Push Docker image to registry:**
   ```bash
   docker tag z_image_base_confyui_api your-registry/z_image_base_confyui_api:latest
   docker push your-registry/z_image_base_confyui_api:latest
   ```

2. **Create serverless endpoint on RunPod:**
   - Go to RunPod Console → Serverless → New Endpoint
   - Select your Docker image
   - Configure:
     - Container Port: `8000`
     - Min Replicas: `0`
     - Max Replicas: `5`
     - Timeout: `300` seconds
     - Idle Timeout: `60` seconds
   - Deploy

#### Option B: GitHub Integration (Recommended)

1. **Configure GitHub Secrets:**
   - `RUNPOD_API_KEY`: Your RunPod API key
   - `DOCKER_USERNAME`: Docker registry username
   - `DOCKER_PASSWORD`: Docker registry password

2. **Push to main branch:**
   ```bash
   git add .
   git commit -m "Deploy to RunPod"
   git push origin main
   ```

3. **GitHub Actions will:**
   - Build and push Docker image
   - Deploy to RunPod automatically

## API Usage

### Request Format

```json
{
  "input": {
    "workflow": { ... },           // Optional: Full ComfyUI workflow
    "prompt": "your prompt here",  // Optional: Simple prompt (overrides workflow)
    "negative_prompt": "low quality, blurry, distorted",  // Optional
    "seed": -1,                    // Optional: -1 for random
    "steps": 26,                   // Optional: 1-100
    "cfg": 4.0,                    // Optional: 1.0-20.0
    "width": 1024,                 // Optional: 512, 768, 1024, 1280, 1536
    "height": 1024,                // Optional: 512, 768, 1024, 1280, 1536
    "return_format": "base64"      // Optional: "base64" or "url"
  }
}
```

### Response Format

**Success:**
```json
{
  "output": {
    "images": [
      {
        "data": "iVBORw0KGgoAAAANSUhEUgAA...",
        "format": "png",
        "width": 1024,
        "height": 1024
      }
    ],
    "metadata": {
      "seed": 123456789,
      "steps": 26,
      "cfg": 4.0,
      "generation_time": 15.23
    }
  },
  "status": "success"
}
```

**Error:**
```json
{
  "error": "Error message describing the issue",
  "error_type": "ExceptionType",
  "traceback": "Full traceback for debugging"
}
```

## API Examples

### Example 1: Simple Prompt Generation

```bash
curl -X POST https://your-endpoint.runpod.run/run \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "prompt": "a beautiful sunset over mountains",
      "width": 1024,
      "height": 1024
    }
  }'
```

### Example 2: Custom Parameters

```bash
curl -X POST https://your-endpoint.runpod.run/run \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "prompt": "anime cat with massive fluffy fennec ears",
      "negative_prompt": "low quality, blurry, distorted",
      "seed": 123456,
      "steps": 30,
      "cfg": 5.0,
      "width": 768,
      "height": 1024
    }
  }'
```

### Example 3: Full Workflow

```bash
curl -X POST https://your-endpoint.runpod.run/run \
  -H "Content-Type: application/json" \
  -d @example-request.json
```

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `LOG_LEVEL` | `INFO` | Logging level (DEBUG, INFO, WARNING, ERROR) |
| `LOG_FORMAT` | `json` | Log format (json, text) |
| `COMFYUI_URL` | `http://127.0.0.1:8188` | ComfyUI API URL |

### RunPod Endpoint Settings

| Setting | Recommended Value | Description |
|---------|-------------------|-------------|
| Container Port | `8000` | Handler API port |
| Min Replicas | `0` | Scale to zero when idle |
| Max Replicas | `5` | Maximum concurrent instances |
| Timeout | `300` | Maximum request duration (seconds) |
| Idle Timeout | `60` | Time before scaling down (seconds) |
| Workers per Replica | `1` | Concurrent workers per instance |

## Monitoring

### Logs

Logs are available in:
- **RunPod Console**: Serverless → Your Endpoint → Logs
- **Structured JSON format** includes:
  - `timestamp`: ISO 8601 timestamp
  - `level`: Log level
  - `message`: Log message
  - `job_id`: RunPod job ID
  - `execution_time`: Request duration

### Metrics

Monitor these key metrics:
- **Request latency**: Time to generate images
- **Error rate**: Failed requests percentage
- **Queue time**: Time spent in queue
- **Cold starts**: Time to spin up new instances

## Troubleshooting

### Common Issues

**Issue: Timeout errors**
- Increase endpoint timeout setting
- Check if workflow is too complex
- Verify model files are loaded

**Issue: Out of memory errors**
- Reduce image dimensions
- Decrease batch size
- Use GPU with more VRAM

**Issue: Slow cold starts**
- Use smaller base image
- Pre-load models on startup
- Increase idle timeout

## Development

### Running Tests

```bash
# Install test dependencies
pip install -r requirements.txt

# Run tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=utils --cov=handler
```

### Local Development

```bash
# Start ComfyUI
comfyui start --listen 0.0.0.0 --port 8188

# Run handler in development mode
python handler.py --rp_serve_api --rp_api_port 8000
```

## Model Information

- **Model**: Z-Image (AuraFlow-based)
- **Text Encoder**: Qwen 3 4B
- **VAE**: FLUX.1-schnell AE
- **Default Settings**:
  - Steps: 26
  - CFG: 4.0
  - Sampler: euler
  - Scheduler: simple
  - Shift: 3.1

## License

This project uses the following models:
- Z-Image: [Comfy-Org/z_image](https://huggingface.co/Comfy-Org/z_image)
- Qwen 3 4B: [Comfy-Org/z_image_turbo](https://huggingface.co/Comfy-Org/z_image_turbo)
- FLUX.1-schnell AE: [black-forest-labs/FLUX.1-schnell](https://huggingface.co/black-forest-labs/FLUX.1-schnell)

## Support

For issues and questions:
- Check RunPod documentation: https://docs.runpod.io
- Review ComfyUI documentation: https://docs.comfy.org
- Open an issue in this repository
