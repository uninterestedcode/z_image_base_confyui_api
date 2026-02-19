"""Input validation schemas and functions for RunPod serverless handler."""

import json
import copy
from typing import Dict, Any, Optional
from runpod.serverless.utils.rp_validator import validate
from utils.logger import setup_logger

logger = setup_logger(__name__)

# Input schema definition
INPUT_SCHEMA = {
    "workflow": {
        "type": dict,
        "required": False,  # Optional if prompt is provided
    },
    "prompt": {
        "type": str,
        "required": False,  # Optional if workflow is provided
        "constraints": lambda x: len(x.strip()) > 0,
    },
    "negative_prompt": {
        "type": str,
        "required": False,
        "default": "low quality, blurry, distorted",
    },
    "seed": {
        "type": int,
        "required": False,
        "default": -1,  # -1 means random
        "constraints": lambda x: x >= -1,
    },
    "steps": {
        "type": int,
        "required": False,
        "default": 26,
        "constraints": lambda x: 1 <= x <= 100,
    },
    "cfg": {
        "type": (int, float),
        "required": False,
        "default": 4.0,
        "constraints": lambda x: 1.0 <= x <= 20.0,
    },
    "width": {
        "type": int,
        "required": False,
        "default": 1024,
        "constraints": lambda x: x in [512, 768, 1024, 1280, 1536],
    },
    "height": {
        "type": int,
        "required": False,
        "default": 1024,
        "constraints": lambda x: x in [512, 768, 1024, 1280, 1536],
    },
    "return_format": {
        "type": str,
        "required": False,
        "default": "base64",
        "constraints": lambda x: x in ["base64", "url"],
    },
}

# Required node types for a valid workflow
REQUIRED_NODE_TYPES = [
    "UNETLoader",
    "CLIPLoader",
    "VAELoader",
    "KSampler",
]

# Output node types (at least one required)
OUTPUT_NODE_TYPES = [
    "SaveImage",
    "PreviewImage",
]


def validate_input(raw_input: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate input against schema.
    
    Args:
        raw_input: Raw input dictionary from job
        
    Returns:
        Dict with either 'validated_input' or 'errors'
        
    Raises:
        ValueError: If validation fails
    """
    # Check if either workflow or prompt is provided
    has_workflow = "workflow" in raw_input and raw_input["workflow"]
    has_prompt = "prompt" in raw_input and raw_input["prompt"]
    
    if not has_workflow and not has_prompt:
        raise ValueError(
            "Missing required field: Either 'workflow' or 'prompt' must be provided"
        )
    
    # Validate against schema
    result = validate(raw_input, INPUT_SCHEMA)
    
    if "errors" in result:
        error_messages = [f"{k}: {v}" for k, v in result["errors"].items()]
        raise ValueError(f"Validation errors: {', '.join(error_messages)}")
    
    logger.info("Input validation successful", extra={
        "validated_input": result["validated_input"]
    })
    
    return result["validated_input"]


def validate_workflow_structure(workflow: Dict[str, Any]) -> bool:
    """
    Validate that workflow has required structure.
    
    Args:
        workflow: ComfyUI workflow dictionary
        
    Returns:
        True if valid
        
    Raises:
        ValueError: If workflow structure is invalid
    """
    if not isinstance(workflow, dict):
        raise ValueError("Workflow must be a dictionary")
    
    if not workflow:
        raise ValueError("Workflow cannot be empty")
    
    # Check for required node types
    found_node_types = set()
    has_output_node = False
    
    for node_id, node_data in workflow.items():
        if not isinstance(node_data, dict):
            continue
        
        class_type = node_data.get("class_type", "")
        found_node_types.add(class_type)
        
        if class_type in OUTPUT_NODE_TYPES:
            has_output_node = True
    
    # Check for required nodes
    missing_nodes = []
    for node_type in REQUIRED_NODE_TYPES:
        if node_type not in found_node_types:
            missing_nodes.append(node_type)
    
    if missing_nodes:
        raise ValueError(
            f"Workflow is missing required node types: {', '.join(missing_nodes)}"
        )
    
    if not has_output_node:
        raise ValueError(
            f"Workflow must contain at least one output node type: {', '.join(OUTPUT_NODE_TYPES)}"
        )
    
    logger.info("Workflow structure validation successful", extra={
        "node_types": list(found_node_types)
    })
    
    return True


def apply_overrides(
    workflow: Dict[str, Any],
    overrides: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Apply parameter overrides to workflow.
    
    Args:
        workflow: Base ComfyUI workflow
        overrides: Parameters to override (prompt, seed, steps, etc.)
        
    Returns:
        Modified workflow
    """
    # Create a deep copy to avoid modifying the original
    modified_workflow = copy.deepcopy(workflow)
    
    # Find and apply overrides
    for node_id, node_data in modified_workflow.items():
        if not isinstance(node_data, dict):
            continue
        
        class_type = node_data.get("class_type", "")
        inputs = node_data.get("inputs", {})
        
        # Override prompt in CLIPTextEncode nodes
        if class_type == "CLIPTextEncode" and "prompt" in overrides:
            # Check if this is the positive prompt node (node 6 in our workflow)
            # We can identify it by checking if it's connected to KSampler
            if "text" in inputs:
                # For now, we'll override all CLIPTextEncode nodes
                # In a more sophisticated implementation, we'd check connections
                inputs["text"] = overrides["prompt"]
        
        # Override negative prompt
        if class_type == "CLIPTextEncode" and "negative_prompt" in overrides:
            if "text" in inputs:
                # Check if this looks like a negative prompt
                current_text = inputs.get("text", "")
                if "low quality" in current_text or "blurry" in current_text:
                    inputs["text"] = overrides["negative_prompt"]
        
        # Override KSampler parameters
        if class_type == "KSampler":
            if "seed" in overrides:
                inputs["seed"] = overrides["seed"]
            if "steps" in overrides:
                inputs["steps"] = overrides["steps"]
            if "cfg" in overrides:
                inputs["cfg"] = overrides["cfg"]
        
        # Override dimensions in EmptySD3LatentImage
        if class_type == "EmptySD3LatentImage":
            if "width" in overrides:
                inputs["width"] = overrides["width"]
            if "height" in overrides:
                inputs["height"] = overrides["height"]
    
    logger.info("Applied parameter overrides", extra={
        "overrides": overrides
    })
    
    return modified_workflow


def load_default_workflow() -> Dict[str, Any]:
    """
    Load the default workflow from workflow.json.
    
    Returns:
        Default workflow dictionary
        
    Raises:
        FileNotFoundError: If workflow.json doesn't exist
        json.JSONDecodeError: If workflow.json is invalid JSON
    """
    try:
        with open("workflow.json", "r") as f:
            workflow = json.load(f)
        logger.info("Loaded default workflow from workflow.json")
        return workflow
    except FileNotFoundError:
        logger.error("workflow.json not found")
        raise FileNotFoundError("Default workflow file (workflow.json) not found")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in workflow.json: {e}")
        raise
