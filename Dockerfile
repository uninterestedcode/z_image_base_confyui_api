# clean base image containing only comfyui, comfy-cli and comfyui-manager
FROM runpod/worker-comfyui:5.5.1-base

# Set working directory
WORKDIR /workspace

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY handler.py .
COPY workflow.json .
COPY utils/ ./utils/

# install custom nodes into comfyui (first node with --mode remote to fetch updated cache)
# No custom nodes detected in the provided workflow

# download models into comfyui
RUN comfy model download --url https://huggingface.co/Comfy-Org/z_image/blob/main/split_files/diffusion_models/z_image_bf16.safetensors --relative-path models/diffusion_models --filename z_image_bf16.safetensors
RUN comfy model download --url https://huggingface.co/Comfy-Org/z_image_turbo/blob/main/split_files/text_encoders/qwen_3_4b.safetensors --relative-path models/text_encoders --filename qwen_3_4b.safetensors
RUN comfy model download --url https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors --relative-path models/vae --filename ae.safetensors

# copy all input data (like images or videos) into comfyui (uncomment and adjust if needed)
# COPY input/ /comfyui/input/

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV LOG_LEVEL=INFO
ENV LOG_FORMAT=json

# Expose port for local testing (not used in production serverless)
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; requests.get('http://127.0.0.1:8188/system_stats')" || exit 1

# Start ComfyUI in background and run handler
CMD ["sh", "-c", "comfyui start --listen 0.0.0.0 --port 8188 & sleep 10 && python handler.py --rp_serve_api --rp_api_port 8000"]
