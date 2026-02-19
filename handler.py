"""Main RunPod serverless handler for ComfyUI image generation."""

import asyncio
import time
import traceback
import os
from typing import Dict, Any

import runpod

from utils.comfyui_executor import ComfyUIExecutor, ComfyUIError, ComfyUIConnectionError, ComfyUIExecutionError
from utils.validators import validate_input, validate_workflow_structure, apply_overrides, load_default_workflow
from utils.logger import setup_logger, set_job_context

# Initialize logger
logger = setup_logger(__name__)

# Environment configuration
COMFYUI_URL = os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
DEFAULT_TIMEOUT = int(os.getenv("DEFAULT_TIMEOUT", "300"))


def handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main handler for RunPod serverless jobs.
    
    Args:
        job: RunPod job object with structure:
            {
                "input": {
                    "workflow": {...},  # ComfyUI workflow JSON
                    "prompt": str,      # Optional: override positive prompt
                    "negative_prompt": str,  # Optional: override negative prompt
                    "seed": int,        # Optional: override seed
                    "steps": int,       # Optional: override steps
                    "cfg": float,       # Optional: override cfg
                    "width": int,       # Optional: override width
                    "height": int,      # Optional: override height
                    "return_format": str  # Optional: "base64" or "url" (default: base64)
                },
                "id": str
            }
    
    Returns:
        Dict with structure:
            {
                "output": {
                    "images": [
                        {
                            "data": "base64_encoded_image_data",
                            "format": "png",
                            "width": 1024,
                            "height": 1024
                        }
                    ],
                    "metadata": {
                        "seed": 123456,
                        "steps": 26,
                        "cfg": 4.0,
                        "generation_time": 15.23
                    }
                },
                "status": "success"
            }
            OR
            {
                "error": "Error message",
                "error_type": "ExceptionType",
                "traceback": "Full traceback"
            }
    """
    job_id = job.get("id", "unknown")
    set_job_context(job_id)
    
    logger.info(f"Received job {job_id}")
    
    try:
        # Validate input
        validated_input = validate_input(job["input"])
        
        # Get or load workflow
        if "workflow" in validated_input:
            workflow = validated_input["workflow"]
            logger.info("Using provided workflow")
        else:
            workflow = load_default_workflow()
            logger.info("Using default workflow")
        
        # Validate workflow structure
        validate_workflow_structure(workflow)
        
        # Apply parameter overrides
        override_params = {
            k: v for k, v in validated_input.items()
            if k in ["prompt", "negative_prompt", "seed", "steps", "cfg", "width", "height"]
        }
        
        if override_params:
            workflow = apply_overrides(workflow, override_params)
            logger.info(f"Applied overrides: {list(override_params.keys())}")
        
        # Execute workflow
        start_time = time.time()
        
        # Run async executor in event loop
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(
                execute_workflow_async(workflow, DEFAULT_TIMEOUT)
            )
        finally:
            loop.close()
        
        generation_time = time.time() - start_time
        
        # Extract metadata
        metadata = {
            "generation_time": round(generation_time, 2),
            "steps": validated_input.get("steps", 26),
            "cfg": validated_input.get("cfg", 4.0),
        }
        
        # Add seed from result if available
        if result and len(result) > 0:
            # Try to extract seed from workflow
            for node_id, node_data in workflow.items():
                if node_data.get("class_type") == "KSampler":
                    metadata["seed"] = node_data.get("inputs", {}).get("seed", -1)
                    break
        
        logger.info(f"Job {job_id} completed successfully", extra={
            "generation_time": generation_time,
            "num_images": len(result)
        })
        
        return {
            "output": {
                "images": result,
                "metadata": metadata
            },
            "status": "success"
        }
        
    except ValueError as e:
        # Validation errors
        logger.warning(f"Validation error for job {job_id}: {e}")
        return {
            "error": str(e),
            "error_type": "ValueError"
        }
    except TimeoutError as e:
        # Timeout errors
        logger.error(f"Timeout error for job {job_id}: {e}")
        return {
            "error": str(e),
            "error_type": "TimeoutError"
        }
    except ComfyUIError as e:
        # ComfyUI-specific errors
        logger.error(f"ComfyUI error for job {job_id}: {e}")
        return {
            "error": f"ComfyUI error: {str(e)}",
            "error_type": type(e).__name__
        }
    except Exception as e:
        # Unexpected errors
        error_trace = traceback.format_exc()
        logger.error(f"Unexpected error for job {job_id}: {e}", extra={
            "traceback": error_trace
        })
        return {
            "error": str(e),
            "error_type": type(e).__name__,
            "traceback": error_trace
        }


async def execute_workflow_async(
    workflow: Dict[str, Any],
    timeout: int
) -> list:
    """
    Execute ComfyUI workflow asynchronously.
    
    Args:
        workflow: ComfyUI workflow JSON
        timeout: Maximum execution time in seconds
        
    Returns:
        List of image dictionaries
        
    Raises:
        ComfyUIError: If execution fails
        TimeoutError: If execution times out
    """
    async with ComfyUIExecutor(COMFYUI_URL) as executor:
        # Execute workflow
        history = await executor.execute_workflow(workflow, timeout)
        
        # Extract images
        images = await executor.extract_images_from_history(history)
        
        return images


def safe_handler(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Wrapper handler with comprehensive error handling.
    
    This function provides an additional layer of error handling
    and is the main entry point for RunPod serverless.
    
    Args:
        job: RunPod job object
        
    Returns:
        Response dict with output or error
    """
    return handler(job)


# Start the serverless worker
if __name__ == "__main__":
    logger.info("Starting RunPod serverless handler")
    logger.info(f"ComfyUI URL: {COMFYUI_URL}")
    logger.info(f"Default timeout: {DEFAULT_TIMEOUT}s")
    
    runpod.serverless.start({"handler": safe_handler})
