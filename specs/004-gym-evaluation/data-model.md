# Data Model: Hybrid Agent with Gym Evaluation

**Feature**: 004-gym-evaluation
**Date**: 2025-12-22
**Status**: Complete

## Scope

This document defines the data types for the hybrid routing agent and GymOrchestrator. Streaming event types are defined in 003-async-evaluation.

## Entities

### 1. StructuredRequest

Parsed AgentBeats format request.

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class AgentParticipant:
    """Agent participant configuration."""
    url: str
    auth_token: str | None = None
    timeout: int = 300

@dataclass
class EvaluationConfig:
    """Evaluation configuration from structured request."""
    domain: str
    num_tasks: int | None = None
    num_trials: int = 1
    task_ids: list[str] | None = None
    user_llm: str = "gpt-4o"
    user_llm_args: dict[str, Any] | None = None
    max_steps: int = 100

@dataclass
class StructuredRequest:
    """Parsed AgentBeats-format structured request."""
    agent: AgentParticipant
    config: EvaluationConfig

    @classmethod
    def from_json(cls, data: dict) -> "StructuredRequest":
        """Parse from JSON dict."""
        participants = data.get("participants", {})
        agent_data = participants.get("agent", {})
        config_data = data.get("config", {})

        return cls(
            agent=AgentParticipant(
                url=agent_data["url"],
                auth_token=agent_data.get("auth_token"),
                timeout=agent_data.get("timeout", 300),
            ),
            config=EvaluationConfig(
                domain=config_data["domain"],
                num_tasks=config_data.get("num_tasks"),
                num_trials=config_data.get("num_trials", 1),
                task_ids=config_data.get("task_ids"),
                user_llm=config_data.get("user_llm", "gpt-4o"),
                user_llm_args=config_data.get("user_llm_args"),
                max_steps=config_data.get("max_steps", 100),
            ),
        )
```

**Validation Rules**:
- `agent.url`: Required, must be valid HTTP(S) URL
- `config.domain`: Required, must be known domain (airline, retail, telecom, mock)
- `config.num_trials`: >= 1
- `config.max_steps`: >= 1

---

### 2. TaskResult

Result from evaluating a single task.

```python
from dataclasses import dataclass
from typing import Any

@dataclass
class TaskResult:
    """Result from a single task evaluation."""
    task_id: str
    trial: int
    reward: float
    success: bool
    steps: int
    purpose: str | None = None
    simulation_run: dict[str, Any] | None = None
    error: str | None = None

    @property
    def is_error(self) -> bool:
        """Check if task ended with error."""
        return self.error is not None
```

**Validation Rules**:
- `task_id`: Non-empty string
- `trial`: >= 1
- `reward`: Float value
- `steps`: >= 0

---

### 3. EvaluationSummary

Aggregated results from a complete evaluation.

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class EvaluationSummary:
    """Aggregated evaluation results."""
    evaluation_id: str
    domain: str
    agent_endpoint: str
    status: str  # completed, failed

    # Counts
    total_tasks: int
    total_trials: int
    successful_simulations: int
    failed_simulations: int

    # Metrics
    success_rate: float
    avg_reward: float
    avg_steps: float

    # Pass@k metrics
    pass_hat_k: dict[int, float] = field(default_factory=dict)

    # Cost (if available)
    total_tokens: int | None = None
    estimated_cost_usd: float | None = None

    # Timing
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    duration_seconds: float | None = None

    # Individual results
    task_results: list[TaskResult] = field(default_factory=list)

    # Error (if failed)
    error: str | None = None

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "evaluation_id": self.evaluation_id,
            "domain": self.domain,
            "agent_endpoint": self.agent_endpoint,
            "status": self.status,
            "summary": {
                "total_simulations": self.total_tasks * self.total_trials,
                "total_tasks": self.total_tasks,
                "successful_simulations": self.successful_simulations,
                "success_rate": self.success_rate,
                "avg_reward": self.avg_reward,
                "pass_hat_k": self.pass_hat_k,
            },
            "timing": {
                "started_at": self.started_at.isoformat(),
                "completed_at": self.completed_at.isoformat() if self.completed_at else None,
                "duration_seconds": self.duration_seconds,
            },
            "tasks": [
                {
                    "task_id": r.task_id,
                    "trial": r.trial,
                    "reward": r.reward,
                    "success": r.success,
                    "purpose": r.purpose,
                }
                for r in self.task_results
            ],
            "error": self.error,
        }
```

---

### 4. GymOrchestratorConfig

Configuration for the GymOrchestrator.

```python
from dataclasses import dataclass, field
from typing import Any
from concurrent.futures import ThreadPoolExecutor

@dataclass
class GymOrchestratorConfig:
    """Configuration for GymOrchestrator."""
    # Required
    invocation_id: str
    a2a_endpoint: str
    domain: str

    # Optional evaluation config
    num_tasks: int | None = None
    num_trials: int = 1
    task_ids: list[str] | None = None
    user_llm: str = "gpt-4o"
    user_llm_args: dict[str, Any] | None = None
    max_steps: int = 100

    # Execution config
    executor: ThreadPoolExecutor | None = None
    max_workers: int = 4

    # Session persistence
    persist_session: bool = True

    @classmethod
    def from_structured_request(
        cls,
        request: StructuredRequest,
        invocation_id: str,
    ) -> "GymOrchestratorConfig":
        """Create config from parsed structured request."""
        return cls(
            invocation_id=invocation_id,
            a2a_endpoint=request.agent.url,
            domain=request.config.domain,
            num_tasks=request.config.num_tasks,
            num_trials=request.config.num_trials,
            task_ids=request.config.task_ids,
            user_llm=request.config.user_llm,
            user_llm_args=request.config.user_llm_args,
            max_steps=request.config.max_steps,
        )
```

---

### 5. Routing Utilities

Input detection and routing helpers.

```python
import json
from typing import Literal

InputType = Literal["structured", "natural_language"]

def detect_input_type(content: str) -> InputType:
    """Detect whether input is structured or natural language.

    Args:
        content: Raw input content string

    Returns:
        "structured" for AgentBeats format, "natural_language" otherwise
    """
    if is_structured_request(content):
        return "structured"
    return "natural_language"

def is_structured_request(content: str) -> bool:
    """Check if content matches AgentBeats structured format.

    Criteria:
    - Valid JSON
    - Has participants.agent.url
    - Has config.domain
    """
    try:
        data = json.loads(content)
        return (
            isinstance(data.get("participants"), dict)
            and isinstance(data.get("participants", {}).get("agent"), dict)
            and "url" in data["participants"]["agent"]
            and isinstance(data.get("config"), dict)
            and "domain" in data["config"]
        )
    except (json.JSONDecodeError, TypeError, KeyError):
        return False

def parse_structured_request(content: str) -> StructuredRequest:
    """Parse structured request content.

    Args:
        content: JSON string in AgentBeats format

    Returns:
        Parsed StructuredRequest

    Raises:
        ValueError: If content is not valid structured format
    """
    if not is_structured_request(content):
        raise ValueError("Content is not a valid structured request")

    data = json.loads(content)
    return StructuredRequest.from_json(data)
```

---

## Type Summary

| Type | Purpose | Location |
|------|---------|----------|
| `StructuredRequest` | Parsed AgentBeats input | `tau2_agent/models/request.py` |
| `TaskResult` | Single task evaluation result | `tau2_agent/models/result.py` |
| `EvaluationSummary` | Aggregated evaluation results | `tau2_agent/models/result.py` |
| `GymOrchestratorConfig` | Orchestrator configuration | `tau2_agent/orchestrator/config.py` |
| `InputType` | Routing type literal | `tau2_agent/detection.py` |

---

## Shared Types from 003

These types from 003-async-evaluation are used in 004:

| Type | Purpose | Import |
|------|---------|--------|
| `EvaluationProgress` | Progress tracking | `from tau2_agent.streaming import EvaluationProgress` |
| `Tau2EventMetadata` | Event metadata | `from tau2_agent.streaming import Tau2EventMetadata` |

---

## Schema: AgentBeats Request Format

```yaml
AgentBeatsRequest:
  type: object
  required:
    - participants
    - config
  properties:
    participants:
      type: object
      required:
        - agent
      properties:
        agent:
          type: object
          required:
            - url
          properties:
            url:
              type: string
              format: uri
              description: A2A endpoint URL of agent to evaluate
            auth_token:
              type: string
              description: Optional auth token for agent
            timeout:
              type: integer
              default: 300
              description: Request timeout in seconds
    config:
      type: object
      required:
        - domain
      properties:
        domain:
          type: string
          enum: [airline, retail, telecom, mock]
          description: Evaluation domain
        num_tasks:
          type: integer
          minimum: 1
          description: Number of tasks to evaluate (null = all)
        num_trials:
          type: integer
          default: 1
          minimum: 1
          description: Trials per task
        task_ids:
          type: array
          items:
            type: string
          description: Specific task IDs to evaluate
        user_llm:
          type: string
          default: "gpt-4o"
          description: LLM for user simulator
        user_llm_args:
          type: object
          description: Additional LLM arguments
        max_steps:
          type: integer
          default: 100
          minimum: 1
          description: Max steps per task
```

---

## Relationship to Other Specs

| Spec | Shared Types |
|------|--------------|
| 002-evaluation-store | `EvaluationSession` uses `EvaluationSummary` |
| 003-async-evaluation | Uses `EvaluationProgress` for progress tracking |
| 006-otel-integration | Uses `evaluation_id` for trace correlation |
