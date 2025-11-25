# ADK Agent Quickstart: Building and Deploying A2A Agents

A practical guide for creating Google ADK agents and exposing them via A2A protocol.

## Prerequisites

```bash
pip install google-adk[a2a]
```

**Requirements**:
- Python 3.10+
- API keys for your LLM provider

## Project Structure

```
your_agent/
├── __init__.py          # Must import agent module
├── agent.py             # Agent definition with root_agent variable
└── agent.json           # AgentCard for A2A protocol
```

## Step 1: Create Agent Definition

**File**: `your_agent/agent.py`

### Option A: Using Gemini (Built-in)

```python
from google.adk.agents import LlmAgent

# ADK expects variable named 'root_agent'
root_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="my_agent",
    description="A helpful assistant",
    instruction="You are a helpful assistant. Be concise.",
)
```

### Option B: Using Custom API (OpenAI-compatible)

```python
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm
import os

# Create LiteLlm wrapper for custom API
llm_model = LiteLlm(
    model="openai/meta-llama/Meta-Llama-3.1-8B-Instruct",  # LiteLLM format
    api_base=os.getenv("NEBIUS_API_BASE", "https://api.tokenfactory.nebius.com/v1/"),
    api_key=os.getenv("NEBIUS_API_KEY"),
)

# Create agent
root_agent = LlmAgent(
    model=llm_model,
    name="my_agent",
    description="Agent using Nebius Llama",
    instruction="You are a helpful assistant.",
)
```

### Adding Tools

```python
from google.adk.agents import LlmAgent
from google.adk.tools import BaseTool

class CalculatorTool(BaseTool):
    """Simple calculator tool."""

    def __init__(self):
        super().__init__(
            name="calculator",
            description="Performs basic math operations"
        )

    def run(self, expression: str) -> str:
        """Evaluate a math expression."""
        try:
            result = eval(expression)
            return f"Result: {result}"
        except Exception as e:
            return f"Error: {str(e)}"

root_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="calculator_agent",
    description="Agent with calculator capability",
    instruction="Help users with calculations.",
    tools=[CalculatorTool()],
)
```

## Step 2: Create Package Init File

**File**: `your_agent/__init__.py`

```python
"""Your agent package."""

from . import agent

__all__ = ["agent"]
```

**Critical**: ADK requires `from . import agent` for agent discovery.

## Step 3: Create AgentCard Configuration

**File**: `your_agent/agent.json`

```json
{
  "name": "my_agent",
  "url": "http://localhost:8000/a2a/my_agent",
  "description": "A helpful assistant",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false
  },
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [
    {
      "id": "general-conversation",
      "name": "General Conversation",
      "description": "Can engage in conversation and answer questions",
      "tags": ["conversation", "qa"]
    }
  ]
}
```

**Required Fields**:
- `name`: Agent identifier
- `url`: Full A2A endpoint URL (must include `/a2a/{agent_name}`)
- `description`: Brief summary
- `version`: Semantic version
- `capabilities`: Agent capabilities object
- `defaultInputModes`: Array of supported input types
- `defaultOutputModes`: Array of supported output types
- `skills`: Array of skill objects with `id`, `name`, `description`, `tags`

## Step 4: Start A2A Server

```bash
# From parent directory of your_agent/
adk api_server --a2a . --port 8000
```

**Important**:
- Pass parent directory (`.`), not agent directory
- Use `adk api_server` (not `adk web`)
- Agent must be in subdirectory with `agent.json`

## Step 5: Verify Agent is Running

### Check Agent Card

```bash
curl http://localhost:8000/a2a/my_agent/.well-known/agent-card.json | jq
```

### Send Test Message

```bash
curl -X POST http://localhost:8000/a2a/my_agent/message/send \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "messageId": "test-123",
      "role": "user",
      "parts": [{"text": "Hello!"}]
    }
  }'
```

## Common Patterns

### Environment Variables

```python
import os

api_key = os.getenv("LLM_API_KEY")
if not api_key:
    raise ValueError("LLM_API_KEY environment variable required")
```

### Custom LLM Providers

ADK uses LiteLLM for multi-provider support. Format: `"openai/{model_name}"` for OpenAI-compatible APIs.

**Examples**:
- Nebius: `"openai/meta-llama/Meta-Llama-3.1-8B-Instruct"`
- Azure: `"azure/gpt-4"`
- Anthropic: `"anthropic/claude-3-sonnet"`

### Multiple Agents

```
project/
├── agent_one/
│   ├── __init__.py
│   ├── agent.py
│   └── agent.json
├── agent_two/
│   ├── __init__.py
│   ├── agent.py
│   └── agent.json
```

Start server from `project/`:
```bash
adk api_server --a2a . --port 8000
```

Agents available at:
- `http://localhost:8000/a2a/agent_one/`
- `http://localhost:8000/a2a/agent_two/`

## A2A Protocol Details

### Endpoint Structure

- **Agent Card**: `/{a2a_prefix}/{agent_name}/.well-known/agent-card.json`
- **Message Send**: `/{a2a_prefix}/{agent_name}/message/send`

Where `{a2a_prefix}` is typically `a2a`.

### Message Format

A2A uses JSON-RPC 2.0 with camelCase fields:

```json
{
  "message": {
    "messageId": "uuid-string",
    "role": "user",
    "parts": [
      {"text": "Hello, agent!"}
    ],
    "contextId": "optional-session-id"
  }
}
```

### Context Management

- **contextId**: Optional session identifier for multi-turn conversations
- Server maintains session state between messages
- New contextId creates new session

## Testing with tau2-bench

```bash
python -m tau2.run \
  --agent-type a2a \
  --agent-endpoint http://localhost:8000/a2a/my_agent \
  --domain mock \
  --num-trials 1
```

## Troubleshooting

### Agent Card Returns 404

**Causes**:
1. Missing `agent.json` file
2. Incomplete AgentCard schema (missing required fields)
3. Wrong directory passed to `adk api_server`
4. Using wrong command (`adk web` instead of `adk api_server`)

**Solution**:
```bash
# Check agent.json exists
ls your_agent/agent.json

# Validate JSON
cat your_agent/agent.json | jq .

# Start from parent directory
cd parent_of_your_agent/
adk api_server --a2a . --port 8000
```

### Agent Not Discovered

**Causes**:
1. Missing `__init__.py` file
2. `__init__.py` doesn't import agent module
3. Variable not named `root_agent` in agent.py

**Solution**:
```bash
# Check __init__.py exists
ls your_agent/__init__.py

# Verify import
grep "from . import agent" your_agent/__init__.py

# Check variable name in agent.py
grep "root_agent = " your_agent/agent.py
```

### Import Errors

**Error**: `ModuleNotFoundError: No module named 'google.adk'`

**Solution**:
```bash
pip install google-adk[a2a]
```

**Error**: `ImportError: A2A requires Python 3.10+`

**Solution**: Upgrade Python to 3.10 or higher.

### LiteLLM Configuration Issues

**Error**: Authentication failed for custom API

**Solution**:
```python
# Verify API key is set
import os
print(os.getenv("YOUR_API_KEY"))  # Should not be None

# Test API directly
import httpx
response = httpx.get(
    "https://your-api.com/v1/models",
    headers={"Authorization": f"Bearer {os.getenv('YOUR_API_KEY')}"}
)
print(response.status_code)  # Should be 200
```

## Production Deployment

### Docker Example

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY your_agent/ ./your_agent/
ENV PORT=8000
EXPOSE 8000

CMD ["adk", "api_server", "--a2a", ".", "--port", "8000", "--host", "0.0.0.0"]
```

### Environment Variables

```bash
# Required
export LLM_API_KEY="your-api-key"

# Optional
export LLM_API_BASE="https://custom-api.com/v1/"
export PORT=8000
```

### Health Checks

```bash
#!/bin/bash
# health_check.sh
curl -f http://localhost:8000/a2a/my_agent/.well-known/agent-card.json > /dev/null 2>&1
exit $?
```

## Reference

### ADK Core Classes

- `google.adk.agents.LlmAgent` - Main agent class
- `google.adk.models.lite_llm.LiteLlm` - Multi-provider LLM wrapper
- `google.adk.tools.BaseTool` - Base class for custom tools

### LiteLLM Model Formats

- OpenAI-compatible: `"openai/{model_name}"`
- Azure: `"azure/{deployment_name}"`
- Anthropic: `"anthropic/{model_name}"`
- [Full list](https://docs.litellm.ai/docs/providers)

### A2A Protocol

- [Specification](https://a2a-protocol.org/latest/specification/)
- [Agent Discovery](https://a2a-protocol.org/latest/topics/agent-discovery/)
- [Message Protocol](https://a2a-protocol.org/latest/topics/message-protocol/)

## Example: Complete Minimal Agent

```
simple_agent/
├── __init__.py
├── agent.py
└── agent.json
```

**__init__.py**:
```python
from . import agent
__all__ = ["agent"]
```

**agent.py**:
```python
from google.adk.agents import LlmAgent
root_agent = LlmAgent(
    model="gemini-2.0-flash-exp",
    name="simple_agent",
    description="A minimal agent",
    instruction="Be helpful and concise.",
)
```

**agent.json**:
```json
{
  "name": "simple_agent",
  "url": "http://localhost:8000/a2a/simple_agent",
  "description": "A minimal agent",
  "version": "1.0.0",
  "capabilities": {"streaming": false},
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [{"id": "chat", "name": "Chat", "description": "Conversation", "tags": ["chat"]}]
}
```

**Start**:
```bash
adk api_server --a2a . --port 8000
```

**Test**:
```bash
curl http://localhost:8000/a2a/simple_agent/.well-known/agent-card.json
```
