# Research: Hybrid Agent with Gym Evaluation

**Feature**: 004-gym-evaluation
**Date**: 2025-12-22
**Status**: Complete

## Scope

This research covers routing logic, GymOrchestrator design, and integration patterns. SSE streaming utilities are covered in 003-async-evaluation.

## Research Tasks

### 1. ADK BaseAgent Pattern

**Question**: How should we implement the Tau2RouterAgent using ADK's BaseAgent?

**Decision**: Extend `google.adk.agents.BaseAgent` and implement `_run_async_impl`.

**Rationale**: ADK's `BaseAgent` provides:

1. **Lifecycle management** - Constructor, initialization
2. **Event emission** - `_run_async_impl` yields `Event` objects
3. **A2A integration** - `A2aAgentExecutor` wraps BaseAgent for A2A protocol

**Implementation Pattern**:
```python
from collections.abc import AsyncIterator
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events.event import Event

class Tau2RouterAgent(BaseAgent):
    """Hybrid agent that routes structured vs NL requests."""

    def __init__(self):
        super().__init__(
            name="tau2_router_agent",
            description="Evaluation service with routing capabilities",
        )
        # Initialize sub-components

    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncIterator[Event]:
        """Main entry point - route based on input type."""
        content = self._extract_content(ctx)

        if is_structured_request(content):
            async for event in self._handle_structured(content, ctx):
                yield event
        else:
            async for event in self.llm_agent.run_async(ctx):
                yield event
```

**Key Insight**: The `_run_async_impl` method is the hook point. We yield `Event` objects which ADK converts to A2A events.

---

### 2. Input Detection Strategy

**Question**: How should we detect structured vs natural language input?

**Decision**: Use JSON schema validation with specific AgentBeats field checks.

**Rationale**: AgentBeats format is well-defined:

```json
{
  "participants": {
    "agent": {
      "url": "http://agent:8000/a2a"
    }
  },
  "config": {
    "domain": "airline",
    "num_tasks": 5
  }
}
```

Detection logic:
1. Attempt JSON parse
2. Check for `participants.agent.url` (required)
3. Check for `config.domain` (required)

**Alternatives Considered**:

| Approach | Pros | Cons |
|----------|------|------|
| JSON schema validation | Strict, catches malformed | Heavy dependency |
| Field checks (chosen) | Simple, no deps | Manual maintenance |
| Regex detection | Fast | Fragile, false positives |
| ML classification | Flexible | Overkill, latency |

**Implementation**:
```python
def is_structured_request(content: str) -> bool:
    """Detect AgentBeats-format structured request."""
    try:
        data = json.loads(content)
        return (
            isinstance(data.get("participants"), dict)
            and isinstance(data.get("participants", {}).get("agent"), dict)
            and "url" in data["participants"]["agent"]
            and isinstance(data.get("config"), dict)
            and "domain" in data["config"]
        )
    except (json.JSONDecodeError, TypeError):
        return False
```

---

### 3. GymOrchestrator Design

**Question**: How should GymOrchestrator interact with tau2-bench's gym environment?

**Decision**: Pure async orchestrator that runs AgentGymEnv in a background thread.

**Rationale**: tau2-bench's `AgentGymEnv` uses synchronous gymnasium interface. We need:
1. Async wrapper for non-blocking operation
2. Progress event emission during execution
3. Clean error handling

**Architecture**:
```
GymOrchestrator
    │
    ├── run_evaluation() [async generator]
    │       │
    │       ├── yield submitted event
    │       │
    │       └── for each task:
    │               │
    │               ├── yield working event
    │               ├── _evaluate_task() [async]
    │               │       │
    │               │       └── run_in_executor(gym.make, env.step, ...)
    │               │
    │               └── yield progress update
    │
    └── yield completed/failed event
```

**Thread Pool Pattern**:
```python
async def _evaluate_task(self, task_id: str) -> TaskResult:
    """Run gym evaluation in background thread."""
    loop = asyncio.get_event_loop()

    def _run_sync():
        env = gym.make(TAU_BENCH_ENV_ID, domain=self.domain, task_id=task_id)
        observation, info = env.reset()
        # ... gym loop ...
        env.close()
        return result

    return await loop.run_in_executor(self.executor, _run_sync)
```

**Alternatives Considered**:
- **Direct sync calls** - Rejected: Blocks event loop
- **Full async gym** - Rejected: Would require rewriting tau2-bench
- **Subprocess** - Rejected: Overhead, complexity

---

### 4. LlmAgent Sub-Agent Integration

**Question**: How should the NL path integrate LlmAgent?

**Decision**: Create LlmAgent as a sub-component, delegate NL requests to it.

**Rationale**: LlmAgent provides:
1. LLM reasoning for natural language
2. Tool calling with function schemas
3. Streaming token output

**Integration Pattern**:
```python
class Tau2RouterAgent(BaseAgent):
    def __init__(self):
        super().__init__(...)

        self.llm_agent = LlmAgent(
            name="tau2_llm_agent",
            model=create_model(),
            instruction=NL_INSTRUCTION,
            tools=[
                RunTau2Evaluation(...),
                ListDomains(...),
                GetEvaluationResults(...),
            ],
        )

    async def _run_async_impl(self, ctx) -> AsyncIterator[Event]:
        if is_structured_request(content):
            # Bypass LLM
            async for event in self._handle_structured(...):
                yield event
        else:
            # Use LLM
            async for event in self.llm_agent.run_async(ctx):
                yield event
```

**Key Insight**: `LlmAgent.run_async()` returns an async iterator of `Event` objects, so we can directly yield them.

---

### 5. Concurrent Request Handling

**Question**: How do we handle multiple concurrent evaluation requests?

**Decision**: Each request gets its own GymOrchestrator instance with unique evaluation_id.

**Rationale**:
1. No shared state between requests
2. Evaluation ID enables session tracking (via 002-evaluation-store)
3. Thread pool shared for efficiency, but work is isolated

**Pattern**:
```python
async def _handle_structured(self, content: str, ctx: InvocationContext):
    data = json.loads(content)

    # Each request gets fresh orchestrator
    orchestrator = GymOrchestrator(
        invocation_id=ctx.invocation_id,
        evaluation_id=self._generate_eval_id(),  # Unique per request
        ...
    )

    async for event in orchestrator.run_evaluation():
        yield event
```

**Concurrency Model**:
```
Request A ─────► Tau2RouterAgent ─────► GymOrchestrator(eval_id=A) ─────► Events
Request B ─────► Tau2RouterAgent ─────► GymOrchestrator(eval_id=B) ─────► Events
                                              │
                                              └─── SharedThreadPoolExecutor
```

---

### 6. Error Handling Strategy

**Question**: How should errors be handled and reported?

**Decision**: Use 003's `create_adk_error_event` for SSE error emission.

**Rationale**:
1. Consistent error format across structured and NL paths
2. ADK handles conversion to A2A `failed` state
3. Error details preserved in tau2.* metadata

**Error Categories**:

| Category | Handling | Error Code |
|----------|----------|------------|
| Invalid JSON input | Return error event | `INVALID_INPUT` |
| Agent unreachable | Return error event | `AGENT_CONNECTION_FAILED` |
| Task evaluation failed | Return error event | `TASK_EVALUATION_FAILED` |
| Internal error | Return error event | `INTERNAL_ERROR` |

**Pattern**:
```python
async def run_evaluation(self) -> AsyncIterator[Event]:
    try:
        for task_id in task_ids:
            try:
                result = await self._evaluate_task(task_id)
            except AgentConnectionError as e:
                yield create_adk_error_event(
                    invocation_id=self.invocation_id,
                    error_message=f"Failed to connect to agent: {e}",
                    error_code="AGENT_CONNECTION_FAILED",
                )
                return
    except Exception as e:
        yield create_adk_error_event(
            invocation_id=self.invocation_id,
            error_message=str(e),
            error_code="INTERNAL_ERROR",
        )
```

---

### 7. Integration with 002-evaluation-store

**Question**: How should evaluation sessions be persisted?

**Decision**: GymOrchestrator creates/updates sessions via 002's SessionStore.

**Rationale**:
1. Session persistence enables result retrieval
2. Progress tracking for long-running evaluations
3. Consistent with 002 design

**Integration Points**:
```python
from tau2_agent.storage import SessionStore, EvaluationSession

async def run_evaluation(self):
    # Create session
    session = EvaluationSession(
        evaluation_id=self.evaluation_id,
        domain=self.domain,
        status="running",
    )
    await self.session_store.create(session)

    # ... run tasks ...

    # Update session
    session.status = "completed"
    session.results = aggregated_results
    await self.session_store.update(session)
```

---

## Dependencies

| Dependency | Version | Purpose |
|------------|---------|---------|
| google-adk | >=1.18.0 | BaseAgent, LlmAgent, Event |
| a2a-sdk | >=0.3.12 | A2A types (reference) |
| gymnasium | * | AgentGymEnv |
| httpx | >=0.28.0 | Async HTTP for A2A calls |
| pydantic | >=2.0 | Data validation |

---

## Summary

| Area | Decision | Confidence |
|------|----------|------------|
| Router pattern | BaseAgent with _run_async_impl | High |
| Input detection | JSON field checks | High |
| GymOrchestrator | Thread pool for sync gym | High |
| LlmAgent integration | Sub-component delegation | High |
| Concurrent handling | Per-request orchestrator instances | High |
| Error handling | 003 error event utilities | High |
| Session persistence | 002 SessionStore integration | High |

## Relationship to Other Specs

| Spec | Relationship |
|------|--------------|
| 002-evaluation-store | Session persistence for evaluation results |
| 003-async-evaluation | Streaming utilities for progress events |
| 006-otel-integration | Shares tau2.* namespace for tracing |
