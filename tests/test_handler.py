"""Unit tests for handler functions."""

import pytest
from unittest.mock import patch, MagicMock
from handler import handler, execute_workflow_async, safe_handler


class TestHandler:
    """Test handler functions."""
    
    @pytest.fixture
    def sample_job(self):
        """Create a sample job for testing."""
        return {
            "id": "test-job-123",
            "input": {
                "prompt": "a beautiful sunset"
            }
        }
    
    @pytest.fixture
    def sample_workflow(self):
        """Create a sample workflow for testing."""
        from utils.validators import load_default_workflow
        return load_default_workflow()
    
    def test_handler_with_valid_input(self, sample_job):
        """Test handler with valid workflow input."""
        # This test would require mocking the ComfyUI executor
        # For now, we'll test the validation path
        with patch('handler.load_default_workflow') as mock_load, \
             patch('handler.validate_workflow_structure') as mock_validate, \
             patch('handler.execute_workflow_async') as mock_execute:
            
            mock_load.return_value = {"10": {"class_type": "UNETLoader", "inputs": {}}}
            mock_execute.return_value = [
                {
                    "data": "iVBORw0KGgoAAAANSUhEUgAA...",
                    "format": "png",
                    "width": 1024,
                    "height": 1024
                }
            ]
            
            result = handler(sample_job)
            
            assert "output" in result
            assert "images" in result["output"]
            assert "metadata" in result["output"]
            assert result["status"] == "success"
    
    def test_handler_with_prompt_override(self, sample_job):
        """Test handler with prompt parameter override."""
        with patch('handler.load_default_workflow') as mock_load, \
             patch('handler.validate_workflow_structure') as mock_validate, \
             patch('handler.apply_overrides') as mock_apply, \
             patch('handler.execute_workflow_async') as mock_execute:
            
            mock_load.return_value = {"10": {"class_type": "UNETLoader", "inputs": {}}}
            mock_apply.return_value = {"10": {"class_type": "UNETLoader", "inputs": {}}}
            mock_execute.return_value = []
            
            handler(sample_job)
            
            # Verify apply_overrides was called
            mock_apply.assert_called_once()
    
    def test_handler_missing_required_fields(self):
        """Test handler returns error for missing fields."""
        job = {
            "id": "test-job-123",
            "input": {}
        }
        
        result = handler(job)
        
        assert "error" in result
        assert "Either 'workflow' or 'prompt'" in result["error"]
        assert result["error_type"] == "ValueError"
    
    def test_handler_invalid_parameter_types(self):
        """Test handler validates parameter types."""
        job = {
            "id": "test-job-123",
            "input": {
                "prompt": "test",
                "steps": "not a number"  # Invalid type
            }
        }
        
        result = handler(job)
        
        assert "error" in result
        assert "Validation errors" in result["error"]
    
    def test_handler_out_of_range_parameters(self):
        """Test handler validates parameter ranges."""
        job = {
            "id": "test-job-123",
            "input": {
                "prompt": "test",
                "steps": 150  # Out of range (1-100)
            }
        }
        
        result = handler(job)
        
        assert "error" in result
        assert "Validation errors" in result["error"]
    
    def test_safe_handler_exception_handling(self):
        """Test safe_handler catches and formats exceptions."""
        job = {
            "id": "test-job-123",
            "input": {}
        }
        
        result = safe_handler(job)
        
        # Should return error since input is missing
        assert "error" in result
    
    def test_safe_handler_value_error(self):
        """Test safe_handler handles ValueError with user message."""
        job = {
            "id": "test-job-123",
            "input": {}
        }
        
        result = safe_handler(job)
        
        assert "error" in result
        assert result["error_type"] == "ValueError"
    
    def test_handler_with_workflow_input(self):
        """Test handler with full workflow input."""
        from utils.validators import load_default_workflow
        
        job = {
            "id": "test-job-123",
            "input": {
                "workflow": load_default_workflow()
            }
        }
        
        with patch('handler.validate_workflow_structure') as mock_validate, \
             patch('handler.execute_workflow_async') as mock_execute:
            
            mock_execute.return_value = []
            
            result = handler(job)
            
            assert "output" in result
            assert result["status"] == "success"
    
    def test_handler_with_custom_parameters(self):
        """Test handler with custom generation parameters."""
        job = {
            "id": "test-job-123",
            "input": {
                "prompt": "test prompt",
                "negative_prompt": "ugly, bad",
                "seed": 42,
                "steps": 30,
                "cfg": 5.0,
                "width": 768,
                "height": 1024
            }
        }
        
        with patch('handler.load_default_workflow') as mock_load, \
             patch('handler.validate_workflow_structure') as mock_validate, \
             patch('handler.apply_overrides') as mock_apply, \
             patch('handler.execute_workflow_async') as mock_execute:
            
            mock_load.return_value = {"10": {"class_type": "UNETLoader", "inputs": {}}}
            mock_apply.return_value = {"10": {"class_type": "UNETLoader", "inputs": {}}}
            mock_execute.return_value = []
            
            result = handler(job)
            
            # Verify apply_overrides was called with correct parameters
            call_args = mock_apply.call_args
            overrides = call_args[0][1]
            
            assert overrides["seed"] == 42
            assert overrides["steps"] == 30
            assert overrides["cfg"] == 5.0
            assert overrides["width"] == 768
            assert overrides["height"] == 1024