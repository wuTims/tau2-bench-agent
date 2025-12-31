# Implementation Plan: Hybrid Agent with Gym Evaluation

**Branch**: `004-gym-evaluation` | **Date**: 2025-12-22 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/004-gym-evaluation/spec.md`
**Depends On**: `003-async-evaluation` (streaming utilities), `002-evaluation-store` (session persistence)
**Depended On By**: None

## Summary

Implement a hybrid `Tau2RouterAgent` (BaseAgent) that:

1. **Routes structured JSON** (AgentBeats format) → GymOrchestrator (no LLM, direct execution)
2. **Routes natural language** → LlmAgent sub-agent (LLM chooses tools)
3. **Streams progress** via SSE using 003-async-evaluation utilities
4. **Persists sessions** using 002-evaluation-store

**Key Insight**: The router is the single entry point. Both paths yield ADK Events which ADK's A2aAgentExecutor converts to A2A SSE events.

## Technical Context

**Language/Version**: Python 3.10+ (per tau2-bench pyproject.toml `requires-python = ">=3.10"`)
**Primary Dependencies**:
- `google-adk>=1.18.0` - ADK `BaseAgent`, `LlmAgent`, `Event` types
- `a2a-sdk>=0.3.12` - A2A protocol types (for reference, ADK handles conversion)
- `gymnasium` - AgentGymEnv for task execution
- `httpx>=0.28.0` - Async HTTP client for A2A communication
- `pydantic>=2.0` - Data validation

**Internal Dependencies**:
- `tau2_agent.streaming` (003) - `EvaluationProgress`, `create_adk_progress_event`, etc.
- `tau2_agent.storage` (002) - Session persistence

**Storage**: Evaluation sessions persisted via 002-evaluation-store
**Testing**: pytest + pytest-asyncio
**Target Platform**: Linux container (Docker)
**Project Type**: Main agent module within tau2_agent

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: A2A/ADK/tau2 Compliance

| Requirement | Status | Notes |
|-------------|--------|-------|
| A2A Protocol Compliance | Planned | ADK handles A2A event conversion |
| ADK Integration | Planned | Tau2RouterAgent extends BaseAgent |
| tau2-bench Extension | Planned | GymOrchestrator uses existing gym/env patterns |
| Message Fidelity | Planned | Structured path preserves exact input |
| Tool Execution Locality | Planned | GymOrchestrator runs tools locally |

### Principle II: Backward Compatibility

| Requirement | Status | Notes |
|-------------|--------|-------|
| Zero Breaking Changes | Planned | New Tau2RouterAgent, doesn't modify existing code |
| Agent Registry | Planned | Registers as new agent type |
| CLI Compatibility | Planned | No CLI changes, A2A protocol access |

### Principle III: Metrics & Observability

| Requirement | Status | Notes |
|-------------|--------|-------|
| Progress Metrics | Planned | Uses 003 streaming utilities |
| Execution Time | Planned | EvaluationProgress.elapsed_seconds |
| Token Tracking | Planned | For NL path via LlmAgent |

### Principle IV: Testing Philosophy

| Requirement | Status | Notes |
|-------------|--------|-------|
| Integration Tests | Planned | Test routing logic, GymOrchestrator flow |
| Test Isolation | Planned | Mock A2A servers for testing |

### Principle V: Code Quality Guidelines

| Requirement | Status | Notes |
|-------------|--------|-------|
| Type Hints | Planned | All public functions fully typed |
| Async Patterns | Planned | GymOrchestrator is fully async |

**Gate Status: PASS**

## Project Structure

### Documentation (this feature)

```text
specs/004-gym-evaluation/
├── plan.md              # This file
├── research.md          # Routing patterns, orchestrator design research
├── data-model.md        # Tau2RouterAgent, GymOrchestrator models
├── quickstart.md        # How to use the hybrid agent
├── contracts/           # AgentBeats schema, routing schemas
└── tasks.md             # Implementation tasks
```

### Source Code (repository root)

```text
tau2_agent/
├── router.py                    # NEW: Tau2RouterAgent (BaseAgent)
├── detection.py                 # NEW: Input type detection
├── orchestrator/                # NEW: Orchestration layer
│   ├── __init__.py
│   └── gym_orchestrator.py      # GymOrchestrator class
├── streaming/                   # FROM 003: SSE utilities
│   ├── __init__.py
│   ├── events.py
│   ├── progress.py
│   └── metadata.py
├── agent.py                     # MODIFY: Export Tau2RouterAgent
└── ...

tests/
├── test_router.py               # NEW: Routing logic tests
├── test_detection.py            # NEW: Input detection tests
├── test_gym_orchestrator.py     # NEW: GymOrchestrator tests
└── ...
```

**Structure Decision**: New `router.py` and `orchestrator/` submodule within `tau2_agent/`. The router is the main entry point; orchestrator encapsulates gym evaluation logic.

## Complexity Tracking

> **No violations identified** - Focused implementation

| Aspect | Decision | Rationale |
|--------|----------|-----------|
| Router pattern | Single router class | Simple routing, no complex middleware |
| Input detection | Function, not class | Stateless JSON validation |
| GymOrchestrator | Standalone class | Encapsulates gym logic cleanly |
| Event emission | Uses 003 utilities | No duplication of SSE logic |

## Implementation Approach

### Key Design Principles

1. **Single entry point**: Tau2RouterAgent handles all requests
2. **Clean separation**: Routing logic vs execution logic
3. **Async-first**: GymOrchestrator is pure async
4. **Reuse 003 utilities**: Don't duplicate SSE event building

### Event Flow Architecture

```
                     Incoming A2A Request
                            │
                            ▼
┌───────────────────────────────────────────────────────────────┐
│  Tau2RouterAgent._run_async_impl()                            │
│                                                                │
│  1. Extract content from InvocationContext                    │
│  2. Detect input type: is_structured_request(content)         │
└───────────────────────────────────────────────────────────────┘
                            │
           ┌────────────────┴────────────────┐
           │                                 │
           ▼                                 ▼
┌─────────────────────────┐    ┌─────────────────────────────────┐
│ Structured Path         │    │ Natural Language Path           │
│                         │    │                                 │
│ parse AgentBeats JSON   │    │ delegate to self.llm_agent      │
│ create GymOrchestrator  │    │ LlmAgent processes with LLM     │
│ run_evaluation()        │    │ may call run_tau2_evaluation    │
│                         │    │ tool which uses GymOrchestrator │
│ yields ADK Event        │    │                                 │
└─────────────────────────┘    └─────────────────────────────────┘
           │                                 │
           │                                 │
           └────────────────┬────────────────┘
                            │
                            ▼
┌───────────────────────────────────────────────────────────────┐
│  ADK A2aAgentExecutor                                         │
│                                                                │
│  convert_event_to_a2a_events(event)                           │
│  → TaskStatusUpdateEvent                                       │
│  → event_queue.enqueue_event()                                │
│  → SSE stream to client                                       │
└───────────────────────────────────────────────────────────────┘
```

### Core Components

#### 1. Input Detection

```python
# tau2_agent/detection.py

def is_structured_request(content: str) -> bool:
    """Detect AgentBeats-format structured request.

    Returns True if content is valid JSON with:
    - participants.agent.url (agent endpoint)
    - config.domain (evaluation domain)
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
    except (json.JSONDecodeError, TypeError):
        return False
```

#### 2. Tau2RouterAgent

```python
# tau2_agent/router.py

class Tau2RouterAgent(BaseAgent):
    """Hybrid agent routing structured vs NL requests."""

    def __init__(self):
        super().__init__(
            name="tau2_router_agent",
            description="Evaluation service routing to appropriate handler",
        )

        # LlmAgent for natural language path
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

    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncIterator[Event]:
        """Route based on input type."""
        content = self._extract_content(ctx)

        if is_structured_request(content):
            # Direct to GymOrchestrator, no LLM
            async for event in self._handle_structured(content, ctx):
                yield event
        else:
            # Delegate to LlmAgent
            async for event in self.llm_agent.run_async(ctx):
                yield event

    async def _handle_structured(
        self,
        content: str,
        ctx: InvocationContext,
    ) -> AsyncIterator[Event]:
        """Handle structured AgentBeats request."""
        data = json.loads(content)

        orchestrator = GymOrchestrator(
            invocation_id=ctx.invocation_id,
            a2a_endpoint=data["participants"]["agent"]["url"],
            domain=data["config"]["domain"],
            num_tasks=data["config"].get("num_tasks"),
            num_trials=data["config"].get("num_trials", 1),
            user_llm=data["config"].get("user_llm", "gpt-4o"),
        )

        async for event in orchestrator.run_evaluation():
            yield event
```

#### 3. GymOrchestrator

```python
# tau2_agent/orchestrator/gym_orchestrator.py

class GymOrchestrator:
    """Async orchestrator for tau2-bench evaluations using AgentGymEnv."""

    def __init__(
        self,
        invocation_id: str,
        a2a_endpoint: str,
        domain: str,
        num_tasks: int | None = None,
        num_trials: int = 1,
        user_llm: str = "gpt-4o",
        user_llm_args: dict | None = None,
        max_steps: int = 100,
    ):
        self.invocation_id = invocation_id
        self.a2a_endpoint = a2a_endpoint
        self.domain = domain
        self.num_tasks = num_tasks
        self.num_trials = num_trials
        self.user_llm = user_llm
        self.user_llm_args = user_llm_args or {}
        self.max_steps = max_steps

        self.evaluation_id = self._generate_evaluation_id()

    async def run_evaluation(self) -> AsyncIterator[Event]:
        """Run full evaluation, yielding progress events."""
        task_ids = self._get_task_ids()
        progress = EvaluationProgress(total_tasks=len(task_ids) * self.num_trials)

        # Emit submitted
        yield create_adk_progress_event(
            invocation_id=self.invocation_id,
            state="submitted",
            message=f"Starting {self.domain} evaluation",
            **{
                "tau2.evaluation_id": self.evaluation_id,
                "tau2.domain": self.domain,
                "tau2.total_tasks": progress.total_tasks,
            },
        )

        results = []
        for trial in range(self.num_trials):
            for task_id in task_ids:
                progress.current_task_id = task_id
                progress.current_trial = trial + 1

                # Emit working
                yield create_adk_progress_event(
                    invocation_id=self.invocation_id,
                    state="working",
                    message=f"Evaluating {task_id} (trial {trial + 1})",
                    progress=progress,
                )

                try:
                    result = await self._evaluate_task(task_id)
                    results.append(result)
                except Exception as e:
                    yield create_adk_error_event(
                        invocation_id=self.invocation_id,
                        error_message=str(e),
                        error_code="TASK_EVALUATION_FAILED",
                    )
                    return

                progress.increment()

        # Emit completed with results
        yield create_adk_result_event(
            invocation_id=self.invocation_id,
            results=self._aggregate_results(results),
            message="Evaluation complete",
            **{"tau2.evaluation_id": self.evaluation_id},
        )
```

## Integration with 003-async-evaluation

The GymOrchestrator uses streaming utilities from 003:

```python
from tau2_agent.streaming import (
    EvaluationProgress,
    create_adk_progress_event,
    create_adk_error_event,
    create_adk_result_event,
)

# Progress tracking
progress = EvaluationProgress(total_tasks=10)
progress.current_task_id = "airline_001"
progress.increment()

# Event creation
event = create_adk_progress_event(
    invocation_id=ctx.invocation_id,
    state="working",
    message="Evaluating task",
    progress=progress,  # Includes tau2.* metadata
)
```

## Constitution Check (Post-Design Re-evaluation)

All principles remain satisfied. The design:
- Uses ADK BaseAgent (Principle I)
- Doesn't modify existing code (Principle II)
- Tracks progress via 003 utilities (Principle III)
- Enables integration testing (Principle IV)
- Uses async patterns with type hints (Principle V)

**Post-Design Gate Status: PASS**

---

## Generated Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Plan | `specs/004-gym-evaluation/plan.md` | Complete |
| Research | `specs/004-gym-evaluation/research.md` | Pending |
| Data Model | `specs/004-gym-evaluation/data-model.md` | Pending |
| Quickstart | `specs/004-gym-evaluation/quickstart.md` | Pending |
| Contracts | `specs/004-gym-evaluation/contracts/` | Pending |

## Next Steps

Run `/speckit.tasks` to generate implementation tasks based on this plan.
