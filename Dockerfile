# Build argument for base image selection
ARG BASE_IMAGE=nvidia/cuda:12.6.3-cudnn-runtime-ubuntu24.04

# Stage 1: Base image with common dependencies
FROM ${BASE_IMAGE} AS base

# Build arguments for this stage with sensible defaults for standalone builds
ARG COMFYUI_VERSION=latest
ARG CUDA_VERSION_FOR_COMFY
ARG ENABLE_PYTORCH_UPGRADE=false
ARG PYTORCH_INDEX_URL

# Prevents prompts from packages asking for user input during installation
ENV DEBIAN_FRONTEND=noninteractive
# Prefer binary wheels over source distributions for faster pip installations
ENV PIP_PREFER_BINARY=1
# Ensures output from python is printed immediately to the terminal without buffering
ENV PYTHONUNBUFFERED=1
# Speed up some cmake builds
ENV CMAKE_BUILD_PARALLEL_LEVEL=8

# Install Python, git and other necessary tools
RUN apt-get update && apt-get install -y \
    python3.12 \
    python3.12-venv \
    git \
    wget \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && ln -sf /usr/bin/python3.12 /usr/bin/python \
    && ln -sf /usr/bin/pip3 /usr/bin/pip

# Clean up to reduce image size
RUN apt-get autoremove -y && apt-get clean -y && rm -rf /var/lib/apt/lists/*

# Install uv (latest) using official installer and create isolated venv
RUN wget -qO- https://astral.sh/uv/install.sh | sh \
    && ln -s /root/.local/bin/uv /usr/local/bin/uv \
    && ln -s /root/.local/bin/uvx /usr/local/bin/uvx \
    && uv venv /opt/venv

# Use the virtual environment for all subsequent commands
ENV PATH="/opt/venv/bin:${PATH}"

# Install comfy-cli + dependencies needed by it to install ComfyUI
RUN uv pip install comfy-cli pip setuptools wheel

# Install ComfyUI
RUN if [ -n "${CUDA_VERSION_FOR_COMFY}" ]; then \
      /usr/bin/yes | comfy --workspace /comfyui install --version "${COMFYUI_VERSION}" --cuda-version "${CUDA_VERSION_FOR_COMFY}" --nvidia; \
    else \
      /usr/bin/yes | comfy --workspace /comfyui install --version "${COMFYUI_VERSION}" --nvidia; \
    fi

# Upgrade PyTorch if needed (for newer CUDA versions)
RUN if [ "$ENABLE_PYTORCH_UPGRADE" = "true" ]; then \
      uv pip install --force-reinstall torch torchvision torchaudio --index-url ${PYTORCH_INDEX_URL}; \
    fi

# Change working directory to ComfyUI
WORKDIR /comfyui

# Install custom nodes needed for z-image workflow
RUN git clone https://github.com/ltdrdata/ComfyUI-Manager.git custom_nodes/ComfyUI-Manager && \
    git clone https://github.com/kijai/ComfyUI-KJNodes custom_nodes/ComfyUI-KJNodes && \
    git clone https://github.com/MoonGoblinDev/Civicomfy custom_nodes/Civicomfy

# Install custom node dependencies
RUN for node_dir in custom_nodes/*/; do \
        if [ -f "$node_dir/requirements.txt" ]; then \
            echo "Installing requirements for $node_dir"; \
            uv pip install -r "$node_dir/requirements.txt" || true; \
        fi; \
    done

# Go back to the root
WORKDIR /

# Install Python runtime dependencies for the handler
RUN uv pip install runpod requests websocket-client

# Copy handler.py
COPY handler.py /comfyui/handler.py

# Create start.sh script that starts ComfyUI in background then runs handler
RUN echo '#!/bin/bash\n\
set -e\n\
\n\
# Start ComfyUI server in background\n\
echo "Starting ComfyUI server..."\n\
cd /comfyui\n\
python main.py --listen 127.0.0.1 --port 8188 &\n\
\n\
# Wait for ComfyUI to be ready\n\
echo "Waiting for ComfyUI to start..."\n\
timeout 60 bash -c "until curl -s http://127.0.0.1:8188/system_stats > /dev/null; do sleep 1; done" || {\n\
    echo "ComfyUI failed to start within 60 seconds"\n\
    exit 1\n\
}\n\
\n\
echo "ComfyUI is ready. Starting serverless handler..."\n\
\n\
# Run the serverless handler\n\
exec python -u /comfyui/handler.py\n\
' > /start.sh && chmod +x /start.sh

# Prevent pip from asking for confirmation during uninstall steps in custom nodes
ENV PIP_NO_INPUT=1

# Set the default command to run when starting the container
CMD ["/start.sh"]

# Stage 2: Download models
FROM base AS downloader

ARG HUGGINGFACE_ACCESS_TOKEN

# Change working directory to ComfyUI
WORKDIR /comfyui

# Create necessary directories upfront
RUN mkdir -p models/checkpoints models/vae models/unet models/clip models/text_encoders models/diffusion_models models/model_patches

# Download z-image models
# Download z_image_bf16.safetensors to models/diffusion_models/
RUN comfy model download \
    --url https://huggingface.co/Comfy-Org/z_image/resolve/main/split_files/diffusion_models/z_image_bf16.safetensors \
    --relative-path models/diffusion_models \
    --filename z_image_bf16.safetensors

# Download qwen_3_4b.safetensors to models/text_encoders/
RUN comfy model download \
    --url https://huggingface.co/Comfy-Org/z_image/resolve/main/split_files/text_encoders/qwen_3_4b.safetensors \
    --relative-path models/text_encoders \
    --filename qwen_3_4b.safetensors

# Download ae.safetensors to models/vae/
RUN comfy model download \
    --url https://huggingface.co/black-forest-labs/FLUX.1-schnell/resolve/main/ae.safetensors \
    --relative-path models/vae \
    --filename ae.safetensors

# Stage 3: Final image
FROM base AS final

# Copy models from stage 2 to the final image
COPY --from=downloader /comfyui/models /comfyui/models
