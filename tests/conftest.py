from collections.abc import Callable
import os

from dotenv import load_dotenv
import pytest

# Load .env file early so all fixtures and tests have access to env vars
load_dotenv()

from tau2.data_model.tasks import Task
from tau2.environment.environment import Environment
from tau2.registry import registry
from tau2.run import get_tasks


@pytest.fixture
def domain_name():
    return "mock"


@pytest.fixture
def get_environment() -> Callable[[], Environment]:
    return registry.get_env_constructor("mock")


@pytest.fixture
def base_task() -> Task:
    return get_tasks("mock", task_ids=["create_task_1"])[0]


@pytest.fixture
def task_with_env_assertions() -> Task:
    return get_tasks("mock", task_ids=["create_task_1_with_env_assertions"])[0]


@pytest.fixture
def task_with_message_history() -> Task:
    return get_tasks("mock", task_ids=["update_task_with_message_history"])[0]


@pytest.fixture
def task_with_initialization_data() -> Task:
    return get_tasks("mock", task_ids=["update_task_with_initialization_data"])[0]


@pytest.fixture
def task_with_initialization_actions() -> Task:
    return get_tasks("mock", task_ids=["update_task_with_initialization_actions"])[0]


@pytest.fixture
def task_with_history_and_env_assertions() -> Task:
    return get_tasks("mock", task_ids=["update_task_with_history_and_env_assertions"])[
        0
    ]


@pytest.fixture
def task_with_action_checks() -> Task:
    return get_tasks("mock", task_ids=["impossible_task_1"])[0]


# LLM Configuration for Real Integration Tests
# These fixtures provide default configurations for tests that make actual LLM calls

@pytest.fixture
def nebius_llm_config():
    """Nebius Llama configuration for testing (requires NEBIUS_API_KEY and NEBIUS_API_BASE env vars)"""
    api_key = os.getenv("NEBIUS_API_KEY")
    api_base = os.getenv("NEBIUS_API_BASE", "https://api.tokenfactory.nebius.com/v1/")

    if not api_key:
        pytest.skip("NEBIUS_API_KEY not set - skipping test requiring real LLM calls")

    return {
        "model": "openai/meta-llama/Meta-Llama-3.1-8B-Instruct",
        "api_key": api_key,
        "api_base": api_base,
    }


@pytest.fixture
def test_llm_agent_config(nebius_llm_config):
    """Default LLM agent configuration for tests"""
    return {
        "llm": nebius_llm_config["model"],
        "llm_args": {
            "api_key": nebius_llm_config["api_key"],
            "api_base": nebius_llm_config["api_base"],
            "temperature": 0.0,
        }
    }


@pytest.fixture
def test_user_llm_config(nebius_llm_config):
    """Default user simulator LLM configuration for tests"""
    return {
        "llm": nebius_llm_config["model"],
        "llm_args": {
            "api_key": nebius_llm_config["api_key"],
            "api_base": nebius_llm_config["api_base"],
            "temperature": 0.0,
        }
    }


@pytest.fixture
def anthropic_api_configured():
    """Skip test if ANTHROPIC_API_KEY is not configured."""
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set - skipping test requiring Anthropic API")
    return api_key


@pytest.fixture
def anthropic_llm_config(anthropic_api_configured):
    """Anthropic Claude configuration for user simulator (requires ANTHROPIC_API_KEY)"""
    return {
        "model": "claude-3-haiku-20240307",
        "api_key": anthropic_api_configured,
    }


@pytest.fixture
def anthropic_user_llm_config(anthropic_llm_config):
    """Anthropic-based user simulator LLM configuration"""
    return {
        "llm": anthropic_llm_config["model"],
        "llm_args": {
            "api_key": anthropic_llm_config["api_key"],
            "temperature": 0.0,
        }
    }
