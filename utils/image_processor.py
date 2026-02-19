"""Image processing and encoding utilities for RunPod serverless handler."""

import base64
import io
from typing import Dict, Any, List, Optional
from PIL import Image
import numpy as np
from utils.logger import setup_logger

logger = setup_logger(__name__)


class ImageProcessor:
    """Process and encode images from ComfyUI output."""
    
    SUPPORTED_FORMATS = ["png", "jpeg", "webp"]
    
    @staticmethod
    def encode_to_base64(
        image_data: bytes,
        format: str = "png",
        quality: int = 95
    ) -> str:
        """
        Encode image data to base64 string.
        
        Args:
            image_data: Raw image bytes
            format: Output format (png, jpeg, webp)
            quality: Quality for lossy formats (1-100)
            
        Returns:
            Base64 encoded string
        """
        try:
            # Open image with PIL
            image = Image.open(io.BytesIO(image_data))
            
            # Convert to RGB if necessary (for JPEG)
            if format.lower() in ["jpeg", "jpg"] and image.mode in ["RGBA", "P"]:
                image = image.convert("RGB")
            
            # Encode to bytes
            buffer = io.BytesIO()
            save_kwargs = {}
            if format.lower() in ["jpeg", "jpg", "webp"]:
                save_kwargs["quality"] = quality
                save_kwargs["optimize"] = True
            
            image.save(buffer, format=format.upper(), **save_kwargs)
            buffer.seek(0)
            
            # Encode to base64
            base64_string = base64.b64encode(buffer.read()).decode("utf-8")
            
            logger.debug(f"Encoded image to base64 (format: {format}, size: {len(base64_string)} chars)")
            
            return base64_string
            
        except Exception as e:
            logger.error(f"Failed to encode image to base64: {e}")
            raise
    
    @staticmethod
    def decode_from_base64(base64_string: str) -> bytes:
        """
        Decode base64 string to bytes.
        
        Args:
            base64_string: Base64 encoded string
            
        Returns:
            Decoded bytes
        """
        try:
            return base64.b64decode(base64_string)
        except Exception as e:
            logger.error(f"Failed to decode base64 string: {e}")
            raise
    
    @staticmethod
    def process_comfyui_output(
        output_data: Dict[str, Any],
        return_format: str = "base64"
    ) -> List[Dict[str, Any]]:
        """
        Process ComfyUI output into API response format.
        
        Args:
            output_data: Raw output from ComfyUI
            return_format: "base64" or "url"
            
        Returns:
            List of processed image dictionaries
        """
        images = []
        
        try:
            # Extract images from output data
            # ComfyUI output structure varies based on node types
            if "images" in output_data:
                for img_data in output_data["images"]:
                    image_info = ImageProcessor._process_single_image(
                        img_data, return_format
                    )
                    if image_info:
                        images.append(image_info)
            
            # Check for output nodes in history
            if "outputs" in output_data:
                for node_id, node_output in output_data["outputs"].items():
                    if "images" in node_output:
                        for img_data in node_output["images"]:
                            image_info = ImageProcessor._process_single_image(
                                img_data, return_format
                            )
                            if image_info:
                                images.append(image_info)
            
            logger.info(f"Processed {len(images)} images from ComfyUI output")
            
            return images
            
        except Exception as e:
            logger.error(f"Failed to process ComfyUI output: {e}")
            raise
    
    @staticmethod
    def _process_single_image(
        img_data: Dict[str, Any],
        return_format: str
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single image from ComfyUI output.
        
        Args:
            img_data: Single image data from ComfyUI
            return_format: "base64" or "url"
            
        Returns:
            Processed image dictionary or None
        """
        try:
            # Extract image data
            if "data" in img_data:
                # Image data is already provided
                image_bytes = base64.b64decode(img_data["data"])
            else:
                # Image data needs to be fetched from ComfyUI
                # This would require additional API calls
                logger.warning("Image data not provided in output")
                return None
            
            # Get image info
            image = Image.open(io.BytesIO(image_bytes))
            width, height = image.size
            format_name = image.format.lower() if image.format else "png"
            
            # Encode to base64
            base64_data = ImageProcessor.encode_to_base64(image_bytes, format=format_name)
            
            return {
                "data": base64_data,
                "format": format_name,
                "width": width,
                "height": height
            }
            
        except Exception as e:
            logger.error(f"Failed to process single image: {e}")
            return None
    
    @staticmethod
    def get_image_info(image: Image.Image) -> Dict[str, Any]:
        """
        Extract metadata from PIL Image.
        
        Args:
            image: PIL Image
            
        Returns:
            Dictionary with image metadata
        """
        return {
            "width": image.width,
            "height": image.height,
            "mode": image.mode,
            "format": image.format,
        }
    
    @staticmethod
    def optimize_image(
        image: Image.Image,
        max_size: Optional[tuple] = None,
        format: str = "png"
    ) -> Image.Image:
        """
        Optimize image for API response.
        
        Args:
            image: PIL Image
            max_size: Maximum (width, height) tuple
            format: Output format
            
        Returns:
            Optimized PIL Image
        """
        # Resize if max_size is specified
        if max_size and (image.width > max_size[0] or image.height > max_size[1]):
            image.thumbnail(max_size, Image.Resampling.LANCZOS)
            logger.debug(f"Resized image to {image.width}x{image.height}")
        
        # Convert format if needed
        if format.lower() in ["jpeg", "jpg"] and image.mode in ["RGBA", "P"]:
            image = image.convert("RGB")
            logger.debug("Converted image to RGB for JPEG format")
        
        return image
    
    @staticmethod
    def extract_images_from_history(
        history: Dict[str, Any],
        comfyui_url: str = "http://127.0.0.1:8188"
    ) -> List[Dict[str, Any]]:
        """
        Extract images from ComfyUI execution history.
        
        Args:
            history: ComfyUI execution history
            comfyui_url: URL to ComfyUI API
            
        Returns:
            List of image dictionaries with base64 data
        """
        images = []
        
        try:
            # Iterate through outputs in history
            for node_id, node_output in history.get("outputs", {}).items():
                if "images" in node_output:
                    for img_info in node_output["images"]:
                        # Construct image URL
                        filename = img_info.get("filename", "")
                        subfolder = img_info.get("subfolder", "")
                        image_type = img_info.get("type", "output")
                        
                        # For now, we'll return the image info
                        # In a full implementation, we'd fetch the actual image data
                        images.append({
                            "filename": filename,
                            "subfolder": subfolder,
                            "type": image_type,
                            "url": f"{comfyui_url}/view?filename={filename}&subfolder={subfolder}&type={image_type}"
                        })
            
            logger.info(f"Extracted {len(images)} images from history")
            
            return images
            
        except Exception as e:
            logger.error(f"Failed to extract images from history: {e}")
            raise
