"""Unit tests for input validation functions."""

import pytest
import json
from utils.validators import (
    validate_input,
    validate_workflow_structure,
    apply_overrides,
    load_default_workflow,
    INPUT_SCHEMA,
    REQUIRED_NODE_TYPES,
    OUTPUT_NODE_TYPES
)


class TestValidateInput:
    """Test input validation function."""
    
    def test_validate_input_with_workflow(self):
        """Test validation with workflow provided."""
        # Load default workflow
        workflow = load_default_workflow()
        
        input_data = {
            "workflow": workflow
        }
        
        result = validate_input(input_data)
        
        assert "workflow" in result
        assert result["workflow"] == workflow
    
    def test_validate_input_with_prompt(self):
        """Test validation with prompt provided."""
        input_data = {
            "prompt": "a beautiful sunset"
        }
        
        result = validate_input(input_data)
        
        assert "prompt" in result
        assert result["prompt"] == "a beautiful sunset"
        assert result["negative_prompt"] == "low quality, blurry, distorted"  # default
        assert result["seed"] == -1  # default
        assert result["steps"] == 26  # default
    
    def test_validate_input_missing_both(self):
        """Test validation fails when both workflow and prompt missing."""
        input_data = {}
        
        with pytest.raises(ValueError) as exc_info:
            validate_input(input_data)
        
        assert "Either 'workflow' or 'prompt'" in str(exc_info.value)
    
    def test_validate_input_defaults_applied(self):
        """Test default values are applied."""
        input_data = {
            "prompt": "test"
        }
        
        result = validate_input(input_data)
        
        assert result["negative_prompt"] == "low quality, blurry, distorted"
        assert result["seed"] == -1
        assert result["steps"] == 26
        assert result["cfg"] == 4.0
        assert result["width"] == 1024
        assert result["height"] == 1024
        assert result["return_format"] == "base64"
    
    def test_validate_input_custom_values(self):
        """Test custom values are preserved."""
        input_data = {
            "prompt": "test",
            "negative_prompt": "ugly, bad",
            "seed": 123,
            "steps": 30,
            "cfg": 5.0,
            "width": 768,
            "height": 1024
        }
        
        result = validate_input(input_data)
        
        assert result["negative_prompt"] == "ugly, bad"
        assert result["seed"] == 123
        assert result["steps"] == 30
        assert result["cfg"] == 5.0
        assert result["width"] == 768
        assert result["height"] == 1024
    
    def test_validate_input_invalid_seed(self):
        """Test validation fails for invalid seed."""
        input_data = {
            "prompt": "test",
            "seed": -2  # Must be >= -1
        }
        
        with pytest.raises(ValueError) as exc_info:
            validate_input(input_data)
        
        assert "Validation errors" in str(exc_info.value)
    
    def test_validate_input_invalid_steps(self):
        """Test validation fails for invalid steps."""
        input_data = {
            "prompt": "test",
            "steps": 150  # Must be 1-100
        }
        
        with pytest.raises(ValueError) as exc_info:
            validate_input(input_data)
        
        assert "Validation errors" in str(exc_info.value)
    
    def test_validate_input_invalid_cfg(self):
        """Test validation fails for invalid cfg."""
        input_data = {
            "prompt": "test",
            "cfg": 25.0  # Must be 1.0-20.0
        }
        
        with pytest.raises(ValueError) as exc_info:
            validate_input(input_data)
        
        assert "Validation errors" in str(exc_info.value)
    
    def test_validate_input_invalid_width(self):
        """Test validation fails for invalid width."""
        input_data = {
            "prompt": "test",
            "width": 600  # Must be in [512, 768, 1024, 1280, 1536]
        }
        
        with pytest.raises(ValueError) as exc_info:
            validate_input(input_data)
        
        assert "Validation errors" in str(exc_info.value)
    
    def test_validate_input_invalid_return_format(self):
        """Test validation fails for invalid return_format."""
        input_data = {
            "prompt": "test",
            "return_format": "binary"  # Must be "base64" or "url"
        }
        
        with pytest.raises(ValueError) as exc_info:
            validate_input(input_data)
        
        assert "Validation errors" in str(exc_info.value)


class TestValidateWorkflowStructure:
    """Test workflow structure validation."""
    
    def test_validate_workflow_structure_valid(self):
        """Test workflow structure validation passes."""
        workflow = load_default_workflow()
        
        result = validate_workflow_structure(workflow)
        
        assert result is True
    
    def test_validate_workflow_structure_empty(self):
        """Test workflow validation fails for empty workflow."""
        with pytest.raises(ValueError) as exc_info:
            validate_workflow_structure({})
        
        assert "cannot be empty" in str(exc_info.value).lower()
    
    def test_validate_workflow_structure_not_dict(self):
        """Test workflow validation fails for non-dict."""
        with pytest.raises(ValueError) as exc_info:
            validate_workflow_structure("not a dict")
        
        assert "must be a dictionary" in str(exc_info.value)
    
    def test_validate_workflow_structure_missing_unet(self):
        """Test workflow validation fails without UNETLoader."""
        workflow = load_default_workflow()
        # Remove UNETLoader node
        workflow = {k: v for k, v in workflow.items() if v.get("class_type") != "UNETLoader"}
        
        with pytest.raises(ValueError) as exc_info:
            validate_workflow_structure(workflow)
        
        assert "UNETLoader" in str(exc_info.value)
    
    def test_validate_workflow_structure_missing_clip(self):
        """Test workflow validation fails without CLIPLoader."""
        workflow = load_default_workflow()
        # Remove CLIPLoader node
        workflow = {k: v for k, v in workflow.items() if v.get("class_type") != "CLIPLoader"}
        
        with pytest.raises(ValueError) as exc_info:
            validate_workflow_structure(workflow)
        
        assert "CLIPLoader" in str(exc_info.value)
    
    def test_validate_workflow_structure_missing_vae(self):
        """Test workflow validation fails without VAELoader."""
        workflow = load_default_workflow()
        # Remove VAELoader node
        workflow = {k: v for k, v in workflow.items() if v.get("class_type") != "VAELoader"}
        
        with pytest.raises(ValueError) as exc_info:
            validate_workflow_structure(workflow)
        
        assert "VAELoader" in str(exc_info.value)
    
    def test_validate_workflow_structure_missing_ksampler(self):
        """Test workflow validation fails without KSampler."""
        workflow = load_default_workflow()
        # Remove KSampler node
        workflow = {k: v for k, v in workflow.items() if v.get("class_type") != "KSampler"}
        
        with pytest.raises(ValueError) as exc_info:
            validate_workflow_structure(workflow)
        
        assert "KSampler" in str(exc_info.value)
    
    def test_validate_workflow_structure_missing_output(self):
        """Test workflow validation fails without output node."""
        workflow = load_default_workflow()
        # Remove SaveImage and PreviewImage nodes
        workflow = {
            k: v for k, v in workflow.items()
            if v.get("class_type") not in OUTPUT_NODE_TYPES
        }
        
        with pytest.raises(ValueError) as exc_info:
            validate_workflow_structure(workflow)
        
        assert "output node" in str(exc_info.value).lower()


class TestApplyOverrides:
    """Test parameter override application."""
    
    def test_apply_overrides_prompt(self):
        """Test prompt override application."""
        workflow = load_default_workflow()
        overrides = {"prompt": "new prompt"}
        
        result = apply_overrides(workflow, overrides)
        
        # Check that CLIPTextEncode nodes were updated
        found_prompt = False
        for node_data in result.values():
            if node_data.get("class_type") == "CLIPTextEncode":
                text = node_data.get("inputs", {}).get("text", "")
                if "new prompt" in text:
                    found_prompt = True
        
        assert found_prompt
    
    def test_apply_overrides_negative_prompt(self):
        """Test negative prompt override application."""
        workflow = load_default_workflow()
        overrides = {"negative_prompt": "ugly, bad quality"}
        
        result = apply_overrides(workflow, overrides)
        
        # Check that negative prompt CLIPTextEncode node was updated
        found_negative = False
        for node_data in result.values():
            if node_data.get("class_type") == "CLIPTextEncode":
                text = node_data.get("inputs", {}).get("text", "")
                if "ugly, bad quality" in text:
                    found_negative = True
        
        assert found_negative
    
    def test_apply_overrides_seed(self):
        """Test seed override application."""
        workflow = load_default_workflow()
        overrides = {"seed": 999}
        
        result = apply_overrides(workflow, overrides)
        
        # Check that KSampler seed was updated
        found_seed = False
        for node_data in result.values():
            if node_data.get("class_type") == "KSampler":
                seed = node_data.get("inputs", {}).get("seed")
                if seed == 999:
                    found_seed = True
        
        assert found_seed
    
    def test_apply_overrides_steps(self):
        """Test steps override application."""
        workflow = load_default_workflow()
        overrides = {"steps": 40}
        
        result = apply_overrides(workflow, overrides)
        
        # Check that KSampler steps was updated
        found_steps = False
        for node_data in result.values():
            if node_data.get("class_type") == "KSampler":
                steps = node_data.get("inputs", {}).get("steps")
                if steps == 40:
                    found_steps = True
        
        assert found_steps
    
    def test_apply_overrides_cfg(self):
        """Test cfg override application."""
        workflow = load_default_workflow()
        overrides = {"cfg": 6.0}
        
        result = apply_overrides(workflow, overrides)
        
        # Check that KSampler cfg was updated
        found_cfg = False
        for node_data in result.values():
            if node_data.get("class_type") == "KSampler":
                cfg = node_data.get("inputs", {}).get("cfg")
                if cfg == 6.0:
                    found_cfg = True
        
        assert found_cfg
    
    def test_apply_overrides_dimensions(self):
        """Test width/height override application."""
        workflow = load_default_workflow()
        overrides = {"width": 768, "height": 1024}
        
        result = apply_overrides(workflow, overrides)
        
        # Check that EmptySD3LatentImage dimensions were updated
        found_dimensions = False
        for node_data in result.values():
            if node_data.get("class_type") == "EmptySD3LatentImage":
                width = node_data.get("inputs", {}).get("width")
                height = node_data.get("inputs", {}).get("height")
                if width == 768 and height == 1024:
                    found_dimensions = True
        
        assert found_dimensions
    
    def test_apply_overrides_does_not_modify_original(self):
        """Test that apply_overrides doesn't modify the original workflow."""
        workflow = load_default_workflow()
        original_seed = None
        
        # Find original seed
        for node_data in workflow.values():
            if node_data.get("class_type") == "KSampler":
                original_seed = node_data.get("inputs", {}).get("seed")
                break
        
        overrides = {"seed": 999}
        result = apply_overrides(workflow, overrides)
        
        # Check original is unchanged
        for node_data in workflow.values():
            if node_data.get("class_type") == "KSampler":
                assert node_data.get("inputs", {}).get("seed") == original_seed
                break


class TestLoadDefaultWorkflow:
    """Test default workflow loading."""
    
    def test_load_default_workflow(self):
        """Test loading default workflow."""
        workflow = load_default_workflow()
        
        assert isinstance(workflow, dict)
        assert len(workflow) > 0
    
    def test_load_default_workflow_has_required_nodes(self):
        """Test default workflow has all required nodes."""
        workflow = load_default_workflow()
        
        found_types = set()
        for node_data in workflow.values():
            found_types.add(node_data.get("class_type", ""))
        
        for node_type in REQUIRED_NODE_TYPES:
            assert node_type in found_types, f"Missing required node: {node_type}"
        
        has_output = any(t in OUTPUT_NODE_TYPES for t in found_types)
        assert has_output, "Missing output node"
