"""Tests for tau2.llm_config module."""

import importlib
import json
import os
from unittest.mock import MagicMock, patch

import pytest


class TestLoadModelsFromEnv:
    """Tests for load_models_from_env function."""

    def test_load_models_from_env_valid_json(self):
        """Test loading valid model config from environment variable."""
        model_json = json.dumps(
            {"test/model-1": {"max_tokens": 8192, "litellm_provider": "openai"}}
        )
        with patch.dict(os.environ, {"TAU2_LLM_MODELS": model_json}):
            from tau2.llm_config import load_models_from_env

            models = load_models_from_env()
            assert models is not None
            assert "test/model-1" in models
            assert models["test/model-1"]["max_tokens"] == 8192
            assert models["test/model-1"]["litellm_provider"] == "openai"

    def test_load_models_from_env_not_set(self):
        """Test graceful handling when env var is not set."""
        with patch.dict(os.environ, {}, clear=True):
            os.environ.pop("TAU2_LLM_MODELS", None)

            from tau2.llm_config import load_models_from_env

            models = load_models_from_env()
            assert models is None

    def test_load_models_from_env_invalid_json(self):
        """Test handling of invalid JSON in environment variable."""
        with patch.dict(os.environ, {"TAU2_LLM_MODELS": "not valid json {"}):
            from tau2.llm_config import load_models_from_env

            models = load_models_from_env()
            assert models is None

    def test_load_models_from_env_invalid_schema(self):
        """Test handling of JSON that doesn't match expected schema (not a dict)."""
        with patch.dict(os.environ, {"TAU2_LLM_MODELS": '"just a string"'}):
            from tau2.llm_config import load_models_from_env

            models = load_models_from_env()
            assert models is None


class TestValidateModelConfig:
    """Tests for validate_model_config function."""

    def test_validate_model_config_valid(self):
        """Test validation of a fully valid config."""
        from tau2.llm_config import validate_model_config

        config = {
            "max_tokens": 8192,
            "max_input_tokens": 8192,
            "max_output_tokens": 4096,
            "input_cost_per_token": 0.00001,
            "output_cost_per_token": 0.00002,
            "litellm_provider": "openai",
        }
        errors = validate_model_config("test/model", config)
        assert errors == []

    def test_validate_model_config_missing_provider(self):
        """Test validation fails when litellm_provider is missing."""
        from tau2.llm_config import validate_model_config

        config = {"max_tokens": 8192}
        errors = validate_model_config("test/model", config)
        assert len(errors) == 1
        assert "missing required field 'litellm_provider'" in errors[0]

    def test_validate_model_config_invalid_provider_type(self):
        """Test validation fails when litellm_provider is not a string."""
        from tau2.llm_config import validate_model_config

        config = {"litellm_provider": 123}
        errors = validate_model_config("test/model", config)
        assert len(errors) == 1
        assert "'litellm_provider' must be a string" in errors[0]

    def test_validate_model_config_invalid_token_types(self):
        """Test validation fails when token fields are not integers."""
        from tau2.llm_config import validate_model_config

        config = {
            "litellm_provider": "openai",
            "max_tokens": "8192",  # should be int
        }
        errors = validate_model_config("test/model", config)
        assert len(errors) == 1
        assert "'max_tokens' must be an integer" in errors[0]

    def test_validate_model_config_negative_costs(self):
        """Test validation fails when cost fields are negative."""
        from tau2.llm_config import validate_model_config

        config = {
            "litellm_provider": "openai",
            "input_cost_per_token": -0.001,
        }
        errors = validate_model_config("test/model", config)
        assert len(errors) == 1
        assert "'input_cost_per_token' must be non-negative" in errors[0]


class TestRegisterModels:
    """Tests for register_models function."""

    def test_register_models_calls_litellm(self):
        """Test that valid models are registered with LiteLLM."""
        with patch("litellm.register_model") as mock_register:
            from tau2.llm_config import register_models

            models = {"test/model": {"max_tokens": 4096, "litellm_provider": "openai"}}

            valid = register_models(models)

            mock_register.assert_called_once_with(models)
            assert valid == models

    def test_register_models_skips_invalid(self):
        """Test that invalid entries are skipped while valid ones are registered."""
        with patch("litellm.register_model") as mock_register:
            from tau2.llm_config import register_models

            models = {
                "valid/model": {"litellm_provider": "openai"},
                "invalid/model": {"max_tokens": 8192},  # missing provider
            }

            valid = register_models(models)

            mock_register.assert_called_once_with({"valid/model": {"litellm_provider": "openai"}})
            assert "valid/model" in valid
            assert "invalid/model" not in valid


class TestRegisterCustomModels:
    """Tests for register_custom_models function."""

    def test_register_custom_models_idempotent(self):
        """Test that registration only happens once by default."""
        env_models = {"custom/model": {"litellm_provider": "openai"}}

        with patch("litellm.register_model") as mock_register:
            with patch.dict(os.environ, {"TAU2_LLM_MODELS": json.dumps(env_models)}):
                import tau2.llm_config as llm_config

                importlib.reload(llm_config)

                result1 = llm_config.register_custom_models()
                assert result1 is True
                assert mock_register.call_count == 1

                result2 = llm_config.register_custom_models()
                assert result2 is False
                assert mock_register.call_count == 1

    def test_register_custom_models_force(self):
        """Test force re-registration."""
        env_models = {"custom/model": {"litellm_provider": "openai"}}

        with patch("litellm.register_model") as mock_register:
            with patch.dict(os.environ, {"TAU2_LLM_MODELS": json.dumps(env_models)}):
                import tau2.llm_config as llm_config

                importlib.reload(llm_config)

                llm_config.register_custom_models()
                assert mock_register.call_count == 1

                result = llm_config.register_custom_models(force=True)
                assert result is True
                assert mock_register.call_count == 2

    def test_no_models_when_env_not_set(self):
        """Test that no models are registered when env var is not set."""
        with patch("litellm.register_model") as mock_register:
            with patch.dict(os.environ, {}, clear=True):
                os.environ.pop("TAU2_LLM_MODELS", None)

                import tau2.llm_config as llm_config

                importlib.reload(llm_config)

                result = llm_config.register_custom_models()

                assert result is False
                mock_register.assert_not_called()

    def test_register_custom_models_from_env(self):
        """Test that env var models are registered."""
        with patch("litellm.register_model") as mock_register:
            env_models = {"custom/env-model": {"litellm_provider": "openai"}}

            with patch.dict(os.environ, {"TAU2_LLM_MODELS": json.dumps(env_models)}):
                import tau2.llm_config as llm_config

                importlib.reload(llm_config)

                result = llm_config.register_custom_models()

                assert result is True
                call_args = mock_register.call_args[0][0]
                assert "custom/env-model" in call_args
