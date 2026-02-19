"""ComfyUI workflow execution utilities for RunPod serverless handler."""

import os
import asyncio
import aiohttp
from typing import Dict, Any, List, Optional
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ComfyUIError(Exception):
    """Base exception for ComfyUI errors."""
    pass


class ComfyUIConnectionError(ComfyUIError):
    """Exception for ComfyUI connection errors."""
    pass


class ComfyUIExecutionError(ComfyUIError):
    """Exception for ComfyUI execution errors."""
    pass


class ComfyUIExecutor:
    """
    Executes ComfyUI workflows via the ComfyUI API.
    
    The base image includes ComfyUI running on port 8188.
    """
    
    def __init__(self, comfyui_url: str = "http://127.0.0.1:8188"):
        """
        Initialize ComfyUI executor.
        
        Args:
            comfyui_url: URL of the ComfyUI API
        """
        self.comfyui_url = comfyui_url.rstrip("/")
        self.session: Optional[aiohttp.ClientSession] = None
        
    async def __aenter__(self):
        """Async context manager entry."""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        if self.session:
            await self.session.close()
    
    async def execute_workflow(
        self,
        workflow: Dict[str, Any],
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Execute a ComfyUI workflow and return the results.
        
        Args:
            workflow: ComfyUI workflow JSON
            timeout: Maximum execution time in seconds
            
        Returns:
            Dict containing execution results including images
            
        Raises:
            TimeoutError: If workflow execution exceeds timeout
            ComfyUIError: If ComfyUI returns an error
        """
        if not self.session:
            raise RuntimeError("Executor not initialized. Use async context manager.")
        
        logger.info("Starting workflow execution", extra={"timeout": timeout})
        
        try:
            # Queue the workflow
            prompt_id = await self._queue_prompt(workflow)
            logger.info(f"Workflow queued with prompt_id: {prompt_id}")
            
            # Wait for completion
            history = await self._wait_for_completion(prompt_id, timeout)
            logger.info(f"Workflow completed for prompt_id: {prompt_id}")
            
            return history
            
        except asyncio.TimeoutError:
            logger.error(f"Workflow execution timed out after {timeout}s")
            raise TimeoutError(f"Workflow execution timed out after {timeout}s")
        except ComfyUIError:
            raise
        except Exception as e:
            logger.error(f"Unexpected error during workflow execution: {e}")
            raise ComfyUIError(f"Unexpected error: {str(e)}")
    
    async def _queue_prompt(self, workflow: Dict[str, Any]) -> str:
        """
        Queue a workflow for execution and return prompt ID.
        
        Args:
            workflow: ComfyUI workflow JSON
            
        Returns:
            Prompt ID for tracking
            
        Raises:
            ComfyUIConnectionError: If connection to ComfyUI fails
            ComfyUIExecutionError: If ComfyUI returns an error
        """
        url = f"{self.comfyui_url}/prompt"
        payload = {"prompt": workflow}
        
        try:
            async with self.session.post(url, json=payload) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"ComfyUI returned error: {error_text}")
                    raise ComfyUIExecutionError(
                        f"ComfyUI returned status {response.status}: {error_text}"
                    )
                
                data = await response.json()
                prompt_id = data.get("prompt_id")
                
                if not prompt_id:
                    raise ComfyUIExecutionError("No prompt_id in ComfyUI response")
                
                return prompt_id
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to ComfyUI: {e}")
            raise ComfyUIConnectionError(f"Failed to connect to ComfyUI: {str(e)}")
    
    async def _wait_for_completion(
        self,
        prompt_id: str,
        timeout: int
    ) -> Dict[str, Any]:
        """
        Wait for workflow completion and return results.
        
        Args:
            prompt_id: Prompt ID to wait for
            timeout: Maximum time to wait in seconds
            
        Returns:
            Execution history from ComfyUI
            
        Raises:
            TimeoutError: If workflow doesn't complete within timeout
            ComfyUIExecutionError: If workflow execution fails
        """
        start_time = asyncio.get_event_loop().time()
        poll_interval = 0.1  # Start with 100ms
        max_poll_interval = 2.0  # Max 2 seconds between polls
        
        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                raise TimeoutError(f"Workflow execution timed out after {timeout}s")
            
            # Get history
            history = await self._get_history(prompt_id)
            
            # Check if complete
            if prompt_id in history:
                # Check for errors in the execution
                node_errors = self._check_for_errors(history[prompt_id])
                if node_errors:
                    error_msg = "; ".join(node_errors)
                    logger.error(f"Workflow execution failed: {error_msg}")
                    raise ComfyUIExecutionError(f"Workflow execution failed: {error_msg}")
                
                return history[prompt_id]
            
            # Wait before next poll (with exponential backoff)
            await asyncio.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.5, max_poll_interval)
    
    async def _get_history(self, prompt_id: str) -> Dict[str, Any]:
        """
        Retrieve execution history for a prompt.
        
        Args:
            prompt_id: Prompt ID to get history for
            
        Returns:
            Execution history from ComfyUI
            
        Raises:
            ComfyUIConnectionError: If connection to ComfyUI fails
        """
        url = f"{self.comfyui_url}/history/{prompt_id}"
        
        try:
            async with self.session.get(url) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to get history: {error_text}")
                    raise ComfyUIExecutionError(
                        f"Failed to get history: status {response.status}"
                    )
                
                return await response.json()
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to ComfyUI: {e}")
            raise ComfyUIConnectionError(f"Failed to connect to ComfyUI: {str(e)}")
    
    def _check_for_errors(self, history_entry: Dict[str, Any]) -> List[str]:
        """
        Check for errors in workflow execution history.
        
        Args:
            history_entry: Single history entry from ComfyUI
            
        Returns:
            List of error messages (empty if no errors)
        """
        errors = []
        
        # Check for node errors
        for node_id, node_output in history_entry.get("outputs", {}).items():
            if "errors" in node_output:
                for error in node_output["errors"]:
                    errors.append(f"Node {node_id}: {error}")
        
        return errors
    
    async def get_image_data(
        self,
        filename: str,
        subfolder: str = "",
        image_type: str = "output"
    ) -> bytes:
        """
        Retrieve image data from ComfyUI.
        
        Args:
            filename: Image filename
            subfolder: Subfolder path
            image_type: Image type (output, input, temp)
            
        Returns:
            Raw image bytes
            
        Raises:
            ComfyUIConnectionError: If connection to ComfyUI fails
        """
        params = {
            "filename": filename,
            "subfolder": subfolder,
            "type": image_type
        }
        
        url = f"{self.comfyui_url}/view"
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    logger.error(f"Failed to get image: {error_text}")
                    raise ComfyUIExecutionError(
                        f"Failed to get image: status {response.status}"
                    )
                
                return await response.read()
                
        except aiohttp.ClientError as e:
            logger.error(f"Failed to connect to ComfyUI: {e}")
            raise ComfyUIConnectionError(f"Failed to connect to ComfyUI: {str(e)}")
    
    async def extract_images_from_history(
        self,
        history: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Extract images from execution history.
        
        Args:
            history: Execution history from ComfyUI
            
        Returns:
            List of image dictionaries with base64 data
        """
        import base64
        from utils.image_processor import ImageProcessor
        
        images = []
        
        try:
            # Iterate through outputs in history
            for node_id, node_output in history.get("outputs", {}).items():
                if "images" in node_output:
                    for img_info in node_output["images"]:
                        filename = img_info.get("filename", "")
                        subfolder = img_info.get("subfolder", "")
                        image_type = img_info.get("type", "output")
                        
                        # Get image data
                        image_bytes = await self.get_image_data(filename, subfolder, image_type)
                        
                        # Encode to base64
                        base64_data = base64.b64encode(image_bytes).decode("utf-8")
                        
                        # Get image info
                        from PIL import Image
                        import io
                        image = Image.open(io.BytesIO(image_bytes))
                        
                        images.append({
                            "data": base64_data,
                            "format": image.format.lower() if image.format else "png",
                            "width": image.width,
                            "height": image.height,
                            "filename": filename
                        })
            
            logger.info(f"Extracted {len(images)} images from history")
            
            return images
            
        except Exception as e:
            logger.error(f"Failed to extract images from history: {e}")
            raise ComfyUIError(f"Failed to extract images: {str(e)}")


async def check_comfyui_health(comfyui_url: str = "http://127.0.0.1:8188") -> bool:
    """
    Check if ComfyUI is healthy and ready.
    
    Args:
        comfyui_url: URL of the ComfyUI API
        
    Returns:
        True if ComfyUI is healthy
    """
    try:
        async with aiohttp.ClientSession() as session:
            url = f"{comfyui_url.rstrip('/')}/system_stats"
            async with session.get(url, timeout=aiohttp.ClientTimeout(total=5)) as response:
                return response.status == 200
    except Exception:
        return False
