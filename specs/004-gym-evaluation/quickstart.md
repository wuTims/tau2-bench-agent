# Quickstart: Hybrid Agent with Gym Evaluation

**Feature**: 004-gym-evaluation
**Date**: 2025-12-22

## Overview

The `Tau2RouterAgent` is a hybrid agent that intelligently routes requests:

1. **Structured JSON** (AgentBeats format) → Direct GymOrchestrator execution (no LLM)
2. **Natural Language** → LlmAgent sub-agent (LLM reasoning)

Both paths stream progress via SSE using the utilities from 003-async-evaluation.

## Installation

The agent is part of the `tau2_agent` package:

```bash
pip install tau2-bench-agent
```

## Starting the Agent

```bash
# Start with ADK
adk api_server --agent tau2_agent.agent:root_agent --a2a

# Or with environment variables
export TAU2_DATA_DIR=./data
adk api_server --agent tau2_agent.agent:root_agent --a2a --port 8080
```

## Usage

### Path 1: Structured Request (AgentBeats Format)

Send a JSON request matching the AgentBeats schema:

```bash
curl -X POST http://localhost:8080/message/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "parts": [{
        "text": "{\"participants\": {\"agent\": {\"url\": \"http://my-agent:8001/a2a\"}}, \"config\": {\"domain\": \"airline\", \"num_tasks\": 5}}"
      }]
    }
  }'
```

This bypasses the LLM and directly runs GymOrchestrator:

```
SSE Response Stream:
data: {"statusUpdate": {"status": {"state": "submitted"}, "metadata": {"tau2.domain": "airline"}}}
data: {"statusUpdate": {"status": {"state": "working"}, "metadata": {"tau2.progress": 20}}}
data: {"statusUpdate": {"status": {"state": "working"}, "metadata": {"tau2.progress": 40}}}
...
data: {"artifactUpdate": {"artifact": {"parts": [{"data": {"success_rate": 0.8}}]}}}
data: {"statusUpdate": {"status": {"state": "completed"}, "final": true}}
```

### Path 2: Natural Language Request

Send a natural language prompt:

```bash
curl -X POST http://localhost:8080/message/stream \
  -H "Content-Type: application/json" \
  -d '{
    "message": {
      "parts": [{
        "text": "Evaluate my agent at http://my-agent:8001/a2a on the airline domain with 5 tasks"
      }]
    }
  }'
```

This uses LlmAgent to interpret the request and call appropriate tools:

```
SSE Response Stream:
data: {"statusUpdate": {"message": {"text": "I'll evaluate your agent..."}}}
data: {"statusUpdate": {"status": {"state": "working"}, "metadata": {"tau2.progress": 20}}}
...
data: {"statusUpdate": {"message": {"text": "Evaluation complete! Success rate: 80%"}}}
```

## AgentBeats Request Schema

```json
{
  "participants": {
    "agent": {
      "url": "http://agent-under-test:8000/a2a",
      "auth_token": "optional-token",
      "timeout": 300
    }
  },
  "config": {
    "domain": "airline",
    "num_tasks": 5,
    "num_trials": 1,
    "user_llm": "gpt-4o",
    "max_steps": 100
  }
}
```

| Field | Required | Default | Description |
|-------|----------|---------|-------------|
| `participants.agent.url` | Yes | - | A2A endpoint of agent |
| `config.domain` | Yes | - | airline, retail, telecom, mock |
| `config.num_tasks` | No | all | Number of tasks to run |
| `config.num_trials` | No | 1 | Trials per task |
| `config.user_llm` | No | gpt-4o | User simulator LLM |

## Routing Detection

The router detects structured vs NL based on:

```python
def is_structured_request(content: str) -> bool:
    """Returns True if content is AgentBeats JSON."""
    try:
        data = json.loads(content)
        return (
            "participants" in data
            and "agent" in data["participants"]
            and "url" in data["participants"]["agent"]
            and "config" in data
            and "domain" in data["config"]
        )
    except:
        return False
```

## SSE Progress Events

Both paths emit consistent progress events:

```json
{
  "statusUpdate": {
    "taskId": "eval-1234567890-abc123",
    "status": {"state": "working"},
    "metadata": {
      "tau2.state": "working",
      "tau2.progress": 40,
      "tau2.completed_tasks": 2,
      "tau2.total_tasks": 5,
      "tau2.current_task_id": "airline_003",
      "tau2.elapsed_seconds": 45.2
    }
  }
}
```

## Python Client Example

```python
import httpx
import json

async def evaluate_agent(agent_url: str, domain: str, num_tasks: int = 5):
    """Run evaluation via structured request."""
    request = {
        "message": {
            "parts": [{
                "text": json.dumps({
                    "participants": {"agent": {"url": agent_url}},
                    "config": {"domain": domain, "num_tasks": num_tasks}
                })
            }]
        }
    }

    async with httpx.AsyncClient() as client:
        async with client.stream(
            "POST",
            "http://localhost:8080/message/stream",
            json=request,
        ) as response:
            async for line in response.aiter_lines():
                if line.startswith("data: "):
                    event = json.loads(line[6:])
                    if "statusUpdate" in event:
                        progress = event["statusUpdate"].get("metadata", {})
                        print(f"Progress: {progress.get('tau2.progress', 0)}%")
                    elif "artifactUpdate" in event:
                        results = event["artifactUpdate"]["artifact"]["parts"][0]["data"]
                        print(f"Results: {results}")
```

## GymOrchestrator Direct Usage

For programmatic use within an agent:

```python
from tau2_agent.orchestrator import GymOrchestrator
from tau2_agent.streaming import EvaluationProgress

async def run_evaluation():
    orchestrator = GymOrchestrator(
        invocation_id="my-invocation",
        a2a_endpoint="http://agent:8001/a2a",
        domain="airline",
        num_tasks=5,
        num_trials=1,
    )

    async for event in orchestrator.run_evaluation():
        # Process events
        if hasattr(event, 'custom_metadata'):
            progress = event.custom_metadata.get('tau2.progress', 0)
            print(f"Progress: {progress}%")
```

## Integration with 002-evaluation-store

Evaluation sessions are automatically persisted:

```python
from tau2_agent.storage import SessionStore

# Query past evaluations
store = SessionStore()
session = await store.get("eval-1234567890-abc123")
print(f"Status: {session.status}")
print(f"Success rate: {session.results.get('success_rate')}")
```

## Troubleshooting

### Structured Request Not Detected

Ensure your JSON includes the required fields:
```json
{
  "participants": {"agent": {"url": "..."}},
  "config": {"domain": "..."}
}
```

### Agent Connection Failed

Verify the agent endpoint is accessible:
```bash
curl http://my-agent:8001/a2a/.well-known/agent.json
```

### Progress Not Streaming

1. Ensure client connects to `/message/stream` (not `/message/send`)
2. Check `Accept: text/event-stream` header

## See Also

- [003-async-evaluation](../003-async-evaluation/quickstart.md) - SSE streaming utilities
- [002-evaluation-store](../002-evaluation-store/quickstart.md) - Session persistence
- [006-otel-integration](../006-otel-integration/spec.md) - OpenTelemetry tracing
