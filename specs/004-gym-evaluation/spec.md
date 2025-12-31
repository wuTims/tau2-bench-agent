# Feature Specification: Hybrid Agent with Gym Evaluation

**Feature Branch**: `004-gym-evaluation`
**Created**: 2025-12-09
**Updated**: 2025-12-21
**Status**: Draft

**Input**: "Create a hybrid tau2_agent that routes structured input (AgentBeats format) directly to GymOrchestrator while routing natural language to an LlmAgent sub-agent"

## Problem Statement

The current `tau2_agent` is an `LlmAgent` that requires LLM inference for every request, even when the input is already structured JSON from platforms like AgentBeats. This creates:

1. **Unnecessary latency**: Structured requests don't need LLM interpretation
2. **Token cost overhead**: LLM processes already-valid evaluation parameters
3. **Reduced reliability**: LLM could misinterpret structured JSON

We need a hybrid agent that:
- Routes **structured input** (AgentBeats JSON) → GymOrchestrator (no LLM, direct execution)
- Routes **natural language** → LlmAgent sub-agent (LLM chooses orchestrator)

## Architecture Overview

```

  Incoming A2A Request
         │
         ▼
  ┌─────────────────────────────────────────────────────────┐
  │  Tau2RouterAgent (BaseAgent)                            │
  │                                                          │
  │  1. Detect input type (structured vs natural language)  │
  │  2. Route to appropriate handler                        │
  └─────────────────────────────────────────────────────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────────────────┐    ┌──────────────────────────────────────┐
│ Structured Path  │    │ Natural Language Path                │
│ (No LLM)         │    │ (LlmAgent sub-agent)                 │
│                  │    │                                      │
│ AgentBeats JSON  │    │ Tools:                               │
│ ↓                │    │ - run_tau2_evaluation(orchestrator)  │
│ GymOrchestrator  │    │ - list_domains                       │
│ ↓                │    │ - get_evaluation_results             │
│ SSE Stream       │    │                                      │
└──────────────────┘    └──────────────────────────────────────┘
         │                         │
         └─────────┬───────────────┘
                   ▼
           SSE TaskStatusUpdateEvent
           (Both paths stream progress)
```

## Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Agent base class | `BaseAgent` | Enables custom routing without LLM overhead |
| Input detection | JSON schema validation | AgentBeats format is well-defined |
| Structured path orchestrator | `GymOrchestrator` | Pure async, no sync/async bridging |
| NL path orchestrator selection | `orchestrator` param | Single tool with explicit choice |
| Default orchestrator | `run_domain` | Backward compatible with existing usage |
| Streaming | SSE for both paths | Per A2A spec, consistent experience |

## Input Detection

### Structured Input (AgentBeats Format)

```json
{
  "participants": {
    "agent": {
      "url": "http://agent-under-test:8000/a2a"
    }
  },
  "config": {
    "domain": "airline",
    "num_tasks": 5,
    "num_trials": 1,
    "user_llm": "gpt-4o"
  }
}
```

Detection criteria:
1. Input is valid JSON
2. Contains `participants` object with `agent.url`
3. Contains `config` object with `domain`

### Natural Language Input

Any text that doesn't match the structured format:
- "Evaluate my agent on the airline domain"
- "Run 5 tasks against http://localhost:8001/agent using the gym orchestrator"
- "What domains are available?"

## Routing Logic

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

| Input Type | Detection | Handler | LLM Used |
|------------|-----------|---------|----------|
| AgentBeats JSON | `is_structured_request()` returns `True` | GymOrchestrator | No |
| Natural language | `is_structured_request()` returns `False` | LlmAgent sub-agent | Yes |

## Structured Path: GymOrchestrator

When structured input is detected, bypass LLM entirely:

```python
async def handle_structured_request(self, data: dict) -> AsyncIterator[Event]:
    """Direct orchestration - no LLM needed."""
    participants = data["participants"]
    config = data["config"]

    orchestrator = GymOrchestrator(
        a2a_config=A2AConfig(endpoint=participants["agent"]["url"]),
        domain=config["domain"],
        num_tasks=config.get("num_tasks"),
        num_trials=config.get("num_trials", 1),
        user_llm=config.get("user_llm", DEFAULT_USER_LLM),
    )

    async for event in orchestrator.run_evaluation():
        yield event  # SSE progress events
```

### GymOrchestrator Design

```python
class GymOrchestrator:
    """
    Async orchestrator for tau2-bench evaluations using AgentGymEnv.

    Runs Orchestrator in background thread while main loop is pure async.
    Yields SSE-compatible progress events during evaluation.
    """

    def __init__(
        self,
        a2a_config: A2AConfig,
        domain: str,
        num_tasks: int | None = None,
        num_trials: int = 1,
        user_llm: str = DEFAULT_USER_LLM,
        user_llm_args: dict | None = None,
        max_steps: int = 100,
    ):
        self.client = A2AClient(config=a2a_config)
        self.domain = domain
        self.num_tasks = num_tasks
        self.num_trials = num_trials
        self.user_llm = user_llm
        self.user_llm_args = user_llm_args or {}
        self.max_steps = max_steps

    async def run_evaluation(self) -> AsyncIterator[TaskStatusUpdateEvent]:
        """
        Run full evaluation, yielding progress events.

        Yields:
            TaskStatusUpdateEvent with states: submitted, working, completed/failed
        """
        task_ids = self._get_task_ids()
        total_tasks = len(task_ids) * self.num_trials
        completed = 0
        results = []

        yield TaskStatusUpdateEvent(
            state=TaskState.SUBMITTED,
            message={"domain": self.domain, "total_tasks": total_tasks}
        )

        for trial in range(self.num_trials):
            for task_id in task_ids:
                yield TaskStatusUpdateEvent(
                    state=TaskState.WORKING,
                    message={
                        "task_id": task_id,
                        "trial": trial + 1,
                        "progress": completed / total_tasks * 100
                    }
                )

                result = await self._evaluate_task(task_id)
                results.append(result)
                completed += 1

        yield TaskStatusUpdateEvent(
            state=TaskState.COMPLETED,
            message=self._aggregate_results(results)
        )

    async def _evaluate_task(self, task_id: str) -> TaskResult:
        """Evaluate single task using AgentGymEnv with pure async A2A."""
        register_gym_agent()

        env = gym.make(
            TAU_BENCH_ENV_ID,
            domain=self.domain,
            task_id=task_id,
            max_steps=self.max_steps,
            user_llm=self.user_llm,
            user_llm_args=self.user_llm_args,
        )

        try:
            observation, info = env.reset()
            context_id = None
            terminated = False

            while not terminated:
                message = self._format_observation(observation, info, context_id is None)
                response, context_id = await self.client.send_message(message, context_id)
                action = self._parse_action(response)
                observation, reward, terminated, _, info = env.step(action)

            return TaskResult(
                task_id=task_id,
                reward=reward,
                success=reward > 0,
                simulation_run=info.get("simulation_run"),
            )
        finally:
            env.close()
```

## Natural Language Path: LlmAgent Sub-Agent

When natural language is detected, delegate to LlmAgent with tools:

```python
class Tau2RouterAgent(BaseAgent):
    """Hybrid agent that routes structured vs NL requests."""

    def __init__(self):
        super().__init__(
            name="tau2_agent",
            description="Agent evaluation service using tau2-bench",
        )

        # LlmAgent for natural language processing
        self.llm_agent = LlmAgent(
            name="tau2_llm_agent",
            model=create_model(),
            instruction=NL_INSTRUCTION,
            tools=[
                RunTau2Evaluation(...),  # With orchestrator param
                ListDomains(...),
                GetEvaluationResults(...),
            ],
        )

        # GymOrchestrator for structured requests
        self.gym_orchestrator_factory = GymOrchestrator

    async def _run_async_impl(
        self,
        ctx: InvocationContext,
    ) -> AsyncIterator[Event]:
        """Route request based on input type."""
        content = self._extract_content(ctx)

        if is_structured_request(content):
            # Structured path - direct orchestration, no LLM
            data = json.loads(content)
            async for event in self._handle_structured(data):
                yield event
        else:
            # Natural language path - delegate to LlmAgent
            async for event in self.llm_agent.run_async(ctx):
                yield event
```

### Updated run_tau2_evaluation Tool

```python
class RunTau2Evaluation(BaseTool):
    """
    Run tau2-bench evaluation with orchestrator selection.

    Parameters:
    - domain: Evaluation domain (airline, retail, telecom, mock)
    - agent_endpoint: A2A endpoint of agent to evaluate
    - orchestrator: "run_domain" (default) or "gym"
    - user_llm: LLM for user simulator (default: gpt-4o)
    - num_trials: Number of trials per task (default: 1)
    - num_tasks: Number of tasks to evaluate (optional)
    - task_ids: Optional list of specific task IDs
    """

    async def run_async(self, *, args: dict, tool_context: ToolContext) -> Any:
        domain = args["domain"]
        agent_endpoint = args["agent_endpoint"]
        orchestrator = args.get("orchestrator", "run_domain")  # Default to run_domain

        if orchestrator == "gym":
            return await self._run_gym_evaluation(args)
        else:
            return await self._run_domain_evaluation(args)

    async def _run_gym_evaluation(self, args: dict) -> dict:
        """Use GymOrchestrator for pure async evaluation."""
        orchestrator = GymOrchestrator(
            a2a_config=A2AConfig(endpoint=args["agent_endpoint"]),
            domain=args["domain"],
            num_tasks=args.get("num_tasks"),
            num_trials=args.get("num_trials", 1),
            user_llm=args.get("user_llm", DEFAULT_USER_LLM),
        )

        results = []
        async for event in orchestrator.run_evaluation():
            if event.state == TaskState.COMPLETED:
                results = event.message

        return results

    async def _run_domain_evaluation(self, args: dict) -> dict:
        """Use run_domain() in executor (existing behavior)."""
        # Current implementation using ThreadPoolExecutor
        ...
```

## SSE Streaming (Both Paths)

Per A2A spec and 003-async-evaluation, both paths stream progress via SSE:

```python
# TaskStatusUpdateEvent format (A2A compliant)
{
    "id": "task-123",
    "state": "working",  # submitted | working | completed | failed
    "message": {
        "task_id": "airline_001",
        "trial": 1,
        "progress": 40,
        "current_task": 2,
        "total_tasks": 5
    }
}
```

ADK exposes streaming via `run_async()` which yields events. The A2A server translates these to SSE.

## User Scenarios & Testing

### Scenario 1: AgentBeats Structured Request (P0)

**Given** a request with AgentBeats JSON format
**When** the router agent receives the request
**Then** it bypasses LLM and directly calls GymOrchestrator
**And** streams progress events via SSE
**And** returns evaluation results without LLM token usage

```python
# Test input
request = {
    "participants": {
        "agent": {"url": "http://localhost:8001/a2a/my_agent"}
    },
    "config": {
        "domain": "airline",
        "num_tasks": 5
    }
}

# Expected: No LLM calls, direct GymOrchestrator execution
```

### Scenario 2: Natural Language with Default Orchestrator (P0)

**Given** a natural language request: "Evaluate my agent on airline domain"
**When** the router agent receives the request
**Then** it delegates to LlmAgent sub-agent
**And** LlmAgent calls `run_tau2_evaluation` with `orchestrator="run_domain"` (default)

### Scenario 3: Natural Language with Gym Orchestrator (P1)

**Given** a natural language request: "Use the gym orchestrator to test my agent"
**When** LlmAgent interprets the request
**Then** it calls `run_tau2_evaluation` with `orchestrator="gym"`

### Scenario 4: SSE Progress Streaming (P0)

**Given** an evaluation in progress (either path)
**When** tasks complete
**Then** SSE events stream with progress updates
**And** client can track progress in real-time

## Implementation Plan

### Phase 1: Tau2RouterAgent Infrastructure

**Files to create:**
- `tau2_agent/router.py` - Tau2RouterAgent (BaseAgent)
- `tau2_agent/detection.py` - `is_structured_request()` function

**Files to modify:**
- `tau2_agent/agent.py` - Export Tau2RouterAgent as root_agent
- `tau2_agent/__init__.py` - Update exports

### Phase 2: GymOrchestrator

**Files to create:**
- `src/tau2/gym/orchestrator.py` - GymOrchestrator class

**Files to modify:**
- `src/tau2/gym/__init__.py` - Export GymOrchestrator

### Phase 3: Update RunTau2Evaluation Tool

**Files to modify:**
- `tau2_agent/tools/run_tau2_evaluation.py` - Add `orchestrator` parameter

### Phase 4: SSE Integration

**Files to modify:**
- Integrate with 003-async-evaluation SSE streaming

## File Changes Summary

| File | Action | Description |
|------|--------|-------------|
| `tau2_agent/router.py` | CREATE | Tau2RouterAgent (BaseAgent) |
| `tau2_agent/detection.py` | CREATE | Input type detection |
| `src/tau2/gym/orchestrator.py` | CREATE | GymOrchestrator class |
| `tau2_agent/agent.py` | MODIFY | Use Tau2RouterAgent as root_agent |
| `tau2_agent/tools/run_tau2_evaluation.py` | MODIFY | Add orchestrator param |
| `src/tau2/gym/__init__.py` | MODIFY | Export GymOrchestrator |
| `tau2_agent/__init__.py` | MODIFY | Update exports |

## Success Criteria

- **SC-001**: Structured AgentBeats requests bypass LLM entirely
- **SC-002**: Natural language requests route to LlmAgent sub-agent
- **SC-003**: LlmAgent can specify `orchestrator="gym"` or `orchestrator="run_domain"`
- **SC-004**: Default orchestrator is `run_domain` (backward compatible)
- **SC-005**: Both paths stream SSE progress events
- **SC-006**: GymOrchestrator runs full multi-task evaluations
- **SC-007**: No regression in existing natural language functionality

## Dependencies

- **003-async-evaluation**: SSE streaming infrastructure
- **002-evaluation-store**: Persist evaluation results
- **src/tau2/gym/gym_agent.py**: AgentGymEnv (existing)
- **src/tau2/a2a/client.py**: A2AClient (existing)

## Open Questions

1. ~~Should structured path use gym or run_domain?~~ **Resolved**: Structured path uses gym (pure async)
2. ~~How does NL path choose orchestrator?~~ **Resolved**: `orchestrator` parameter on tool, defaults to run_domain
3. Should we validate AgentBeats schema strictly or be lenient?
4. How to handle partial/invalid structured JSON (fallback to NL or error)?
