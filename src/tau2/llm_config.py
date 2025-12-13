"""
Dynamic LLM model registration for LiteLLM.

This module provides functionality to register custom LLM models with LiteLLM
from the TAU2_LLM_MODELS environment variable.

Usage:
    # Import early in application startup to ensure models are registered
    from tau2.llm_config import register_custom_models
    register_custom_models()
"""

import json
import os
from typing import Any, TypedDict

import litellm
from loguru import logger

# Environment variable name
ENV_LLM_MODELS = "TAU2_LLM_MODELS"


class ModelConfig(TypedDict, total=False):
    """Configuration for a single LLM model."""

    max_tokens: int
    max_input_tokens: int
    max_output_tokens: int
    input_cost_per_token: float
    output_cost_per_token: float
    litellm_provider: str


# Module-level state to track registration
_models_registered: bool = False


def load_models_from_env() -> dict[str, ModelConfig] | None:
    """
    Load model configurations from TAU2_LLM_MODELS environment variable.

    Returns:
        Dictionary of model configurations, or None if not set or invalid.
    """
    env_value = os.environ.get(ENV_LLM_MODELS)
    if not env_value:
        return None

    try:
        models = json.loads(env_value)
        if not isinstance(models, dict):
            logger.warning(
                f"{ENV_LLM_MODELS} must be a JSON object, got {type(models).__name__}"
            )
            return None
        return models
    except json.JSONDecodeError as e:
        logger.warning(f"Invalid JSON in {ENV_LLM_MODELS}: {e}")
        return None


def validate_model_config(name: str, config: Any) -> list[str]:
    """
    Validate a model configuration.

    Args:
        name: The model name (for error messages).
        config: The configuration to validate.

    Returns:
        List of validation error messages (empty if valid).
    """
    errors: list[str] = []

    if not isinstance(config, dict):
        errors.append(f"Model '{name}': config must be a dict, got {type(config).__name__}")
        return errors

    # Required: litellm_provider
    if "litellm_provider" not in config:
        errors.append(f"Model '{name}': missing required field 'litellm_provider'")
    elif not isinstance(config["litellm_provider"], str):
        errors.append(
            f"Model '{name}': 'litellm_provider' must be a string, "
            f"got {type(config['litellm_provider']).__name__}"
        )
    elif not config["litellm_provider"].strip():
        errors.append(f"Model '{name}': 'litellm_provider' cannot be empty")

    # Optional: token limits (must be positive integers)
    token_fields = ["max_tokens", "max_input_tokens", "max_output_tokens"]
    for field in token_fields:
        if field in config:
            value = config[field]
            if not isinstance(value, int):
                errors.append(
                    f"Model '{name}': '{field}' must be an integer, "
                    f"got {type(value).__name__}"
                )
            elif value <= 0:
                errors.append(f"Model '{name}': '{field}' must be positive, got {value}")

    # Optional: costs (must be non-negative floats)
    cost_fields = ["input_cost_per_token", "output_cost_per_token"]
    for field in cost_fields:
        if field in config:
            value = config[field]
            if not isinstance(value, (int, float)):
                errors.append(
                    f"Model '{name}': '{field}' must be a number, "
                    f"got {type(value).__name__}"
                )
            elif value < 0:
                errors.append(
                    f"Model '{name}': '{field}' must be non-negative, got {value}"
                )

    return errors


def register_models(models: dict[str, ModelConfig]) -> dict[str, ModelConfig]:
    """
    Validate and register models with LiteLLM.

    Args:
        models: Dictionary mapping model names to their configurations.

    Returns:
        Dictionary of valid models that were registered.
    """
    if not models:
        return {}

    valid_models: dict[str, ModelConfig] = {}

    for name, config in models.items():
        errors = validate_model_config(name, config)
        if errors:
            for error in errors:
                logger.warning(error)
        else:
            valid_models[name] = config

    if valid_models:
        litellm.register_model(valid_models)
        logger.debug(
            f"Registered {len(valid_models)} custom LLM model(s): {list(valid_models.keys())}"
        )

    return valid_models


def register_custom_models(force: bool = False) -> bool:
    """
    Register custom LLM models from TAU2_LLM_MODELS environment variable.

    Args:
        force: If True, re-register even if already registered.

    Returns:
        True if models were registered, False if skipped (already registered or no models).
    """
    global _models_registered

    if _models_registered and not force:
        logger.debug("Custom LLM models already registered, skipping")
        return False

    # Load from environment variable
    env_models = load_models_from_env()
    if not env_models:
        logger.debug(f"No custom models configured in {ENV_LLM_MODELS}")
        _models_registered = True
        return False

    logger.debug(f"Loaded {len(env_models)} model(s) from {ENV_LLM_MODELS}")

    # Validate and register models
    valid_models = register_models(env_models)

    _models_registered = True
    if valid_models:
        logger.info(f"Registered {len(valid_models)} custom LLM model(s) with LiteLLM")

    return len(valid_models) > 0
