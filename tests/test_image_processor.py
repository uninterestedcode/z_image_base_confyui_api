"""Unit tests for image processing functions."""

import pytest
import io
import base64
from PIL import Image
from utils.image_processor import ImageProcessor


class TestImageProcessor:
    """Test ImageProcessor class methods."""
    
    @pytest.fixture
    def sample_image(self):
        """Create a sample PIL Image for testing."""
        # Create a simple 100x100 red image
        img = Image.new("RGB", (100, 100), color="red")
        return img
    
    @pytest.fixture
    def sample_image_bytes(self, sample_image):
        """Convert sample image to bytes."""
        buffer = io.BytesIO()
        sample_image.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer.read()
    
    def test_encode_to_base64_png(self, sample_image_bytes):
        """Test PNG encoding to base64."""
        result = ImageProcessor.encode_to_base64(sample_image_bytes, format="png")
        
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Verify it's valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0
    
    def test_encode_to_base64_jpeg(self, sample_image_bytes):
        """Test JPEG encoding to base64."""
        result = ImageProcessor.encode_to_base64(sample_image_bytes, format="jpeg", quality=90)
        
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Verify it's valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0
        
        # Verify it's actually JPEG
        img = Image.open(io.BytesIO(decoded))
        assert img.format == "JPEG"
    
    def test_encode_to_base64_webp(self, sample_image_bytes):
        """Test WebP encoding to base64."""
        result = ImageProcessor.encode_to_base64(sample_image_bytes, format="webp", quality=80)
        
        assert isinstance(result, str)
        assert len(result) > 0
        
        # Verify it's valid base64
        decoded = base64.b64decode(result)
        assert len(decoded) > 0
    
    def test_decode_from_base64(self, sample_image_bytes):
        """Test base64 decoding."""
        # First encode
        encoded = base64.b64encode(sample_image_bytes).decode("utf-8")
        
        # Then decode
        result = ImageProcessor.decode_from_base64(encoded)
        
        assert isinstance(result, bytes)
        assert result == sample_image_bytes
    
    def test_get_image_info(self, sample_image):
        """Test image metadata extraction."""
        info = ImageProcessor.get_image_info(sample_image)
        
        assert info["width"] == 100
        assert info["height"] == 100
        assert info["mode"] == "RGB"
        assert info["format"] is None  # Image.new() doesn't set format
    
    def test_optimize_image_resize(self, sample_image):
        """Test image resizing."""
        max_size = (50, 50)
        optimized = ImageProcessor.optimize_image(sample_image, max_size=max_size)
        
        # Should be resized to fit within max_size
        assert optimized.width <= 50
        assert optimized.height <= 50
    
    def test_optimize_image_no_resize(self, sample_image):
        """Test image optimization without resize."""
        max_size = (200, 200)
        optimized = ImageProcessor.optimize_image(sample_image, max_size=max_size)
        
        # Should not be resized
        assert optimized.width == 100
        assert optimized.height == 100
    
    def test_optimize_image_format_conversion(self):
        """Test format conversion for JPEG."""
        # Create RGBA image
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 128))
        
        optimized = ImageProcessor.optimize_image(img, format="jpeg")
        
        # Should be converted to RGB
        assert optimized.mode == "RGB"
    
    def test_process_comfyui_output_with_images(self):
        """Test processing ComfyUI output with images."""
        # Create mock output data with images
        image_bytes = io.BytesIO()
        img = Image.new("RGB", (64, 64), color="blue")
        img.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        
        output_data = {
            "images": [
                {
                    "data": base64.b64encode(image_bytes.read()).decode("utf-8"),
                    "filename": "test.png"
                }
            ]
        }
        
        result = ImageProcessor.process_comfyui_output(output_data, return_format="base64")
        
        assert len(result) == 1
        assert result[0]["format"] == "png"
        assert result[0]["width"] == 64
        assert result[0]["height"] == 64
        assert "data" in result[0]
    
    def test_process_comfyui_output_empty(self):
        """Test processing empty ComfyUI output."""
        output_data = {}
        
        result = ImageProcessor.process_comfyui_output(output_data)
        
        assert len(result) == 0
    
    def test_process_comfyui_output_with_outputs(self):
        """Test processing ComfyUI output with outputs section."""
        # Create mock output data
        image_bytes = io.BytesIO()
        img = Image.new("RGB", (64, 64), color="green")
        img.save(image_bytes, format="PNG")
        image_bytes.seek(0)
        
        output_data = {
            "outputs": {
                "9": {
                    "images": [
                        {
                            "data": base64.b64encode(image_bytes.read()).decode("utf-8"),
                            "filename": "output.png"
                        }
                    ]
                }
            }
        }
        
        result = ImageProcessor.process_comfyui_output(output_data, return_format="base64")
        
        assert len(result) == 1
        assert result[0]["format"] == "png"
    
    def test_supported_formats(self):
        """Test supported formats list."""
        assert "png" in ImageProcessor.SUPPORTED_FORMATS
        assert "jpeg" in ImageProcessor.SUPPORTED_FORMATS
        assert "webp" in ImageProcessor.SUPPORTED_FORMATS