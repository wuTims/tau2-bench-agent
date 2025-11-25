# Test Configuration Guide

This document explains how LLM providers are configured for different test scenarios in tau2-bench.

## Test Types and LLM Usage

### 1. Unit Tests (No Real LLM Calls)
**Location:** `tests/test_*/` (most directories)
**LLM Strategy:** Use mocks via `unittest.mock` or `pytest-mock`
**Speed:** Fast (~seconds)
**Cost:** Free

**Example:**
```python
from unittest.mock import patch
from tau2.agent.llm_agent import LLMAgent

@patch("tau2.agent.llm_agent.generate")
def test_agent_behavior(mock_generate):
    mock_generate.return_value = AssistantMessage(...)
    # Test logic here
```

### 2. Integration Tests (Real LLM Calls)
**Location:** `tests/test_a2a_e2e/`, `tests/test_integration/`
**LLM Strategy:** Use Nebius Llama 3.1 8B via fixtures
**Speed:** Slower (~minutes)
**Cost:** Minimal (Nebius pricing)

**Example:**
```python
def test_real_llm_integration(test_llm_agent_config, test_user_llm_config):
    """Test with real Nebius LLM calls"""
    agent = LLMAgent(
        tools=mock_tools,
        domain_policy="Test policy",
        **test_llm_agent_config  # Uses Nebius Llama
    )
    # Test will skip if NEBIUS_API_KEY not set
```

### 3. Backward Compatibility Tests (Mocks Only)
**Location:** `tests/test_backward_compatibility/`
**LLM Strategy:** Always use mocks (enforced by conftest.py)
**Speed:** Fast (~seconds)
**Cost:** Free

**Why mocks only?**
- These tests verify interface compatibility, not LLM behavior
- Fast execution is critical for CI/CD
- No external dependencies required

## LLM Configuration Fixtures

### Available Fixtures

#### `nebius_llm_config`
Provides Nebius Llama configuration from environment variables.

**Usage:**
```python
def test_with_nebius(nebius_llm_config):
    model = nebius_llm_config["model"]
    # "openai/meta-llama/Meta-Llama-3.1-8B-Instruct"
```

**Requires:**
- `NEBIUS_API_KEY` environment variable
- `NEBIUS_API_BASE` environment variable (optional, has default)

**Behavior:** Automatically skips test if `NEBIUS_API_KEY` not set.

#### `test_llm_agent_config`
Complete agent LLM configuration ready to pass to `LLMAgent` constructor.

**Usage:**
```python
def test_agent(test_llm_agent_config, mock_tools):
    agent = LLMAgent(
        tools=mock_tools,
        domain_policy="Policy",
        **test_llm_agent_config  # Unpacks llm and llm_args
    )
```

**Returns:**
```python
{
    "llm": "openai/meta-llama/Meta-Llama-3.1-8B-Instruct",
    "llm_args": {
        "api_key": "...",
        "api_base": "https://api.tokenfactory.nebius.com/v1/",
        "temperature": 0.0
    }
}
```

#### `test_user_llm_config`
Complete user simulator LLM configuration.

**Usage:**
```python
def test_user_simulator(test_user_llm_config):
    user = UserSimulator(
        **test_user_llm_config  # Uses Nebius Llama
    )
```

## Environment Setup

### Required Environment Variables

Create or update `.env` file:

```bash
# Nebius Configuration (Required for integration tests)
NEBIUS_API_KEY=v1.CmQKHHN0YXRpY2tleS1lMDBj...
NEBIUS_API_BASE=https://api.tokenfactory.nebius.com/v1/

# Anthropic Configuration (Optional - for comparison tests)
ANTHROPIC_API_KEY=sk-ant-api03-...
```

### Verifying Configuration

```bash
# Check if environment variables are set
env | grep NEBIUS

# Run tests that require real LLM calls
pytest tests/test_a2a_e2e/ -v

# Run all tests (integration tests will skip if keys not set)
pytest tests/ -v
```

## Default LLM for Tests

**Primary Test LLM:** Nebius Llama 3.1 8B Instruct

**Model ID:** `openai/meta-llama/Meta-Llama-3.1-8B-Instruct`

**Why Llama 3.1 8B?**
- ✅ Cost-effective for test execution
- ✅ Fast inference (~1-2s per request)
- ✅ Sufficient capability for tau2-bench tasks
- ✅ OpenAI-compatible API (via Nebius)
- ✅ No rate limiting issues

**Alternative Models:**

| Model | Use Case | Cost | Speed |
|-------|----------|------|-------|
| Claude Haiku | High-quality baseline | Low | Fast |
| Claude Sonnet | Complex task validation | Medium | Medium |
| GPT-4 | Reference comparison | High | Slow |

To use alternatives, override fixtures:

```python
@pytest.fixture
def test_llm_agent_config():
    return {
        "llm": "claude-3-haiku-20240307",
        "llm_args": {"temperature": 0.0}
    }
```

## Test Execution Strategies

### Run Fast Tests Only (No LLM Calls)
```bash
# Exclude integration tests
pytest tests/ -v -m "not integration"

# Or run specific fast test suites
pytest tests/test_backward_compatibility/ -v
pytest tests/test_a2a_client/ -v -k "not real_llm"
```

### Run Integration Tests with Real LLMs
```bash
# Requires NEBIUS_API_KEY
pytest tests/test_a2a_e2e/ -v

# Run specific integration test
pytest tests/test_a2a_e2e/test_evaluation_flow.py::test_complete_a2a_loop -v
```

### Run Full Test Suite
```bash
# All tests (integration tests skip if no API keys)
pytest tests/ -v

# With coverage
pytest tests/ --cov=tau2 --cov-report=html -v
```

## Markers for Test Classification

Use pytest markers to classify tests:

```python
@pytest.mark.unit
def test_fast_unit_test():
    """Fast test with mocks"""
    pass

@pytest.mark.integration
def test_real_llm_integration(test_llm_agent_config):
    """Slow test with real LLM calls"""
    pass

@pytest.mark.requires_nebius
def test_nebius_specific(nebius_llm_config):
    """Test requiring Nebius API key"""
    pass
```

Register markers in `pytest.ini`:

```ini
[pytest]
markers =
    unit: Fast unit tests with mocks
    integration: Integration tests with real LLM calls
    requires_nebius: Tests requiring NEBIUS_API_KEY
    requires_anthropic: Tests requiring ANTHROPIC_API_KEY
```

## CI/CD Configuration

### GitHub Actions Example

```yaml
name: Tests

on: [push, pull_request]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run unit tests
        run: pytest tests/ -v -m "not integration"

  integration-tests:
    runs-on: ubuntu-latest
    env:
      NEBIUS_API_KEY: ${{ secrets.NEBIUS_API_KEY }}
      NEBIUS_API_BASE: ${{ secrets.NEBIUS_API_BASE }}
    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: pytest tests/test_a2a_e2e/ -v
```

## Cost Estimation

**Nebius Llama 3.1 8B Pricing:**
- Input: ~$0.10 per 1M tokens
- Output: ~$0.10 per 1M tokens

**Typical Test Run:**
- Unit tests (mocked): $0
- Single integration test: ~$0.001-0.01
- Full E2E test suite: ~$0.10-0.50

**Monthly CI/CD Estimate:**
- 100 PR runs/month × $0.05/run = ~$5/month

## Troubleshooting

### Test Skipped: "NEBIUS_API_KEY not set"

**Solution:** Set environment variable:
```bash
export NEBIUS_API_KEY="your-key-here"
# Or add to .env file
```

### LiteLLM Error: "Invalid API key"

**Solution:** Verify key format and expiration:
```bash
echo $NEBIUS_API_KEY | head -c 20
# Should start with: v1.CmQK...
```

### Slow Test Execution

**Solution:** Run unit tests only:
```bash
pytest tests/ -v -m "not integration"
```

### Tests Passing Locally but Failing in CI

**Solution:** Ensure CI has required secrets configured and test uses appropriate markers.

## Best Practices

1. **Default to Mocks:** Use mocks for unit tests, real LLMs for integration tests only
2. **Use Fixtures:** Always use `test_llm_agent_config` and `test_user_llm_config` fixtures
3. **Mark Tests:** Use `@pytest.mark.integration` for tests requiring real LLM calls
4. **Environment Fallback:** Tests requiring API keys should skip gracefully if not set
5. **Cost Awareness:** Keep integration test count low, use Nebius Llama for cost efficiency

## Summary

```
┌─────────────────────────────────────────────────────────┐
│  Test Type           │  LLM Strategy  │  Speed  │ Cost  │
├─────────────────────────────────────────────────────────┤
│  Unit Tests          │  Mocks         │  Fast   │ Free  │
│  Backward Compat     │  Mocks (only)  │  Fast   │ Free  │
│  Integration Tests   │  Nebius Llama  │  Slow   │ Low   │
│  E2E Tests          │  Nebius Llama  │  Slower │ Low   │
└─────────────────────────────────────────────────────────┘

Default Test LLM: openai/meta-llama/Meta-Llama-3.1-8B-Instruct
Provider: Nebius (OpenAI-compatible)
Requires: NEBIUS_API_KEY, NEBIUS_API_BASE
```
