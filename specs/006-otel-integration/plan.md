# Implementation Plan: OpenTelemetry Integration for A2A Trace Visibility

**Branch**: `006-otel-integration` | **Date**: 2025-12-11 | **Spec**: [spec.md](spec.md)

## Summary

Add OpenTelemetry instrumentation to tau2's A2A communication layer so that per-task evaluation traces appear in the ADK web viewer in real-time. This enables developers to see the full A2A message flow during evaluations, even when running multiple tasks concurrently.

**Core Value**: Transform opaque `run_tau2_evaluation` tool calls into transparent, debuggable trace hierarchies showing every A2A interaction per task.

## Technical Context

**Language/Version**: Python 3.10+
**Primary Dependencies**:
- `opentelemetry-api` (>=1.20.0) - Tracing API (no SDK required, uses ADK's provider)
- Existing: httpx, loguru, pydantic

**Key Integration Points**:
- ADK sets up `TracerProvider` and span exporters
- tau2 obtains tracer via `trace.get_tracer("tau2")`
- Spans automatically flow to ADK's web UI via configured exporters

**Constraints**:
- Zero breaking changes to existing tau2 CLI workflows
- Must handle missing OTel gracefully (no-op when not configured)
- Thread pool execution requires explicit context propagation

## Span Hierarchy Design

```
invoke_agent (tau2_agent)                    [ADK creates]
└── execute_tool (run_tau2_evaluation)       [ADK creates]
    └── tau2.evaluation                      [NEW: tau2 creates]
        ├── tau2.task                        [NEW: per task]
        │   ├── tau2.a2a.message             [NEW: per A2A request]
        │   ├── tau2.a2a.message
        │   └── tau2.task.evaluate           [NEW: reward calculation]
        ├── tau2.task
        │   └── ...
        └── tau2.task
            └── ...
```

## Project Structure

### New Files

```text
src/tau2/
├── telemetry/                    # NEW: OTel instrumentation module
│   ├── __init__.py
│   ├── tracing.py               # Tracer setup, span helpers
│   └── context.py               # Thread context propagation utilities
```

### Modified Files

```text
src/tau2/
├── a2a/
│   └── client.py                # Add spans around send_message()
├── run.py                       # Add evaluation span, propagate context to threads
├── agent/
│   └── a2a_agent.py             # Add task-level spans
└── evaluator/
    └── evaluator.py             # Add evaluation span for reward calculation

tau2_agent/
└── tools/
    └── run_tau2_evaluation.py   # Pass trace context to thread executor
```

## Implementation Phases

### Phase 1: Core Telemetry Module

Create the telemetry foundation with graceful fallback when OTel isn't configured.

**File: `src/tau2/telemetry/__init__.py`**
```python
from .tracing import get_tracer, create_span, get_trace_id, SpanKind
from .context import propagate_context, attach_context, get_current_context, detach_context

__all__ = [
    "get_tracer",
    "create_span",
    "get_trace_id",  # For store correlation
    "SpanKind",
    "propagate_context",
    "attach_context",
    "get_current_context",
    "detach_context",
]
```

**File: `src/tau2/telemetry/tracing.py`**
```python
"""OpenTelemetry tracing utilities for tau2.

Provides graceful fallback when OTel is not configured.
"""
import os
from contextlib import contextmanager
from typing import Any, Generator

# Lazy import to avoid hard dependency
_tracer = None
_TRACER_NAME = "tau2"
_CAPTURE_CONTENT = os.getenv("TAU2_CAPTURE_MESSAGE_CONTENT", "false").lower() == "true"

def get_tracer():
    """Get or create the tau2 tracer.

    Returns a no-op tracer if OpenTelemetry is not configured.
    """
    global _tracer
    if _tracer is None:
        try:
            from opentelemetry import trace
            _tracer = trace.get_tracer(_TRACER_NAME)
        except ImportError:
            _tracer = _NoOpTracer()
    return _tracer


class _NoOpSpan:
    """No-op span for when OTel is not available."""

    def set_attribute(self, key: str, value: Any) -> None:
        pass

    def set_status(self, status: Any) -> None:
        pass

    def record_exception(self, exception: Exception) -> None:
        pass

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass


class _NoOpTracer:
    """No-op tracer for when OTel is not available."""

    @contextmanager
    def start_as_current_span(self, name: str, **kwargs) -> Generator[_NoOpSpan, None, None]:
        yield _NoOpSpan()


@contextmanager
def create_span(
    name: str,
    attributes: dict[str, Any] | None = None,
    kind: str = "internal",
) -> Generator[Any, None, None]:
    """Create a span with the given name and attributes.

    Args:
        name: Span name (e.g., "tau2.task", "tau2.a2a.message")
        attributes: Initial span attributes
        kind: Span kind ("internal", "client", "server")

    Yields:
        The span object (or no-op span if OTel not configured)
    """
    tracer = get_tracer()

    # Map kind string to OTel SpanKind if available
    span_kind = None
    try:
        from opentelemetry.trace import SpanKind
        kind_map = {
            "internal": SpanKind.INTERNAL,
            "client": SpanKind.CLIENT,
            "server": SpanKind.SERVER,
        }
        span_kind = kind_map.get(kind, SpanKind.INTERNAL)
    except ImportError:
        pass

    with tracer.start_as_current_span(name, kind=span_kind) as span:
        if attributes:
            for key, value in attributes.items():
                if value is not None:
                    span.set_attribute(key, value)
        yield span


def should_capture_content() -> bool:
    """Check if message content should be captured in spans."""
    return _CAPTURE_CONTENT


def get_trace_id() -> str | None:
    """Extract W3C trace_id from current span for store correlation.

    Returns:
        32-character hex string or None if not available

    Used by EvaluationContext to capture trace_id for store records,
    enabling correlation between traces and stored evaluations.
    """
    try:
        from opentelemetry import trace
        span = trace.get_current_span()
        ctx = span.get_span_context()
        if ctx.is_valid:
            return format(ctx.trace_id, '032x')
        return None
    except (ImportError, AttributeError):
        return None
```

**File: `src/tau2/telemetry/context.py`**
```python
"""OpenTelemetry context propagation utilities.

Handles trace context propagation across thread boundaries.
"""
from typing import Any, Callable
from functools import wraps

def get_current_context() -> Any:
    """Get the current trace context for propagation.

    Returns:
        Context object or None if OTel not configured
    """
    try:
        from opentelemetry import context
        return context.get_current()
    except ImportError:
        return None


def attach_context(ctx: Any) -> Any:
    """Attach a trace context in the current thread.

    Args:
        ctx: Context object from get_current_context()

    Returns:
        Token for detaching, or None if OTel not configured
    """
    if ctx is None:
        return None
    try:
        from opentelemetry import context
        return context.attach(ctx)
    except ImportError:
        return None


def detach_context(token: Any) -> None:
    """Detach a previously attached trace context.

    Args:
        token: Token returned from attach_context()
    """
    if token is None:
        return
    try:
        from opentelemetry import context
        context.detach(token)
    except ImportError:
        pass


def propagate_context(func: Callable) -> Callable:
    """Decorator to propagate trace context into a function.

    Use this to wrap functions that will be executed in thread pools.
    The context is captured at decoration time and attached when called.

    Usage:
        ctx = get_current_context()

        @propagate_context
        def worker():
            # Spans created here will be children of the captured context
            pass

        # Pass ctx to the worker somehow, or capture in closure
    """
    # Capture context at decoration time
    ctx = get_current_context()

    @wraps(func)
    def wrapper(*args, **kwargs):
        token = attach_context(ctx)
        try:
            return func(*args, **kwargs)
        finally:
            detach_context(token)

    return wrapper


def with_context(ctx: Any):
    """Decorator factory to propagate a specific context.

    Usage:
        ctx = get_current_context()

        @with_context(ctx)
        def worker():
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            token = attach_context(ctx)
            try:
                return func(*args, **kwargs)
            finally:
                detach_context(token)
        return wrapper
    return decorator
```

---

### Phase 2: Instrument A2A Client

Add spans around A2A message exchanges.

**Modify: `src/tau2/a2a/client.py`**

```python
# Add import at top
from tau2.telemetry import create_span, should_capture_content

# In send_message() method, wrap the HTTP request:
async def send_message(self, ...):
    request_id = str(uuid.uuid4())

    with create_span(
        "tau2.a2a.message",
        attributes={
            "tau2.request_id": request_id,
            "tau2.endpoint": self.config.endpoint,
            "tau2.context_id": context_id,
        },
        kind="client",
    ) as span:
        start_time = time.perf_counter()

        try:
            # ... existing HTTP request code ...

            latency_ms = (time.perf_counter() - start_time) * 1000

            # Add completion attributes
            span.set_attribute("tau2.latency_ms", round(latency_ms, 2))
            span.set_attribute("tau2.status_code", status_code)
            span.set_attribute("tau2.input_tokens", input_tokens)
            span.set_attribute("tau2.output_tokens", output_tokens)

            if should_capture_content():
                # Truncate to avoid huge spans
                span.set_attribute("tau2.request_content", str(message_content)[:10000])
                span.set_attribute("tau2.response_content", str(response_content)[:10000])

            return response_content, response_context_id

        except Exception as e:
            span.set_attribute("tau2.error", str(e))
            try:
                from opentelemetry.trace import Status, StatusCode
                span.set_status(Status(StatusCode.ERROR, str(e)))
            except ImportError:
                pass
            span.record_exception(e)
            raise
```

---

### Phase 3: Instrument Task Execution

Add spans around each task evaluation and propagate context to thread pool.

**Modify: `src/tau2/run.py`**

```python
# Add imports
from tau2.telemetry import create_span, get_current_context, attach_context, detach_context

# In run_tasks(), wrap the thread pool execution:
def run_tasks(...):
    # ... existing setup code ...

    # Capture current context before entering thread pool
    parent_context = get_current_context()

    def _run_with_context(task: Task, trial: int, seed: int, progress_str: str) -> SimulationRun:
        """Run task with propagated trace context."""
        # Attach parent context in this worker thread
        token = attach_context(parent_context)
        try:
            return _run(task, trial, seed, progress_str)
        finally:
            detach_context(token)

    def _run(task: Task, trial: int, seed: int, progress_str: str) -> SimulationRun:
        # Create task span
        with create_span(
            "tau2.task",
            attributes={
                "tau2.task_id": task.id,
                "tau2.domain": domain,
                "tau2.trial": trial,
                "tau2.seed": seed,
            },
        ) as span:
            console_text = Text(...)
            ConsoleDisplay.console.print(console_text)

            try:
                simulation = run_task(...)

                # Add result attributes
                if simulation.reward_info:
                    span.set_attribute("tau2.reward", simulation.reward_info.reward)
                span.set_attribute("tau2.duration_ms", simulation.duration * 1000)
                span.set_attribute("tau2.termination_reason", simulation.termination_reason.value)

                simulation.trial = trial
                if console_display:
                    ConsoleDisplay.display_simulation(simulation, show_details=False)
                _save(simulation)

            except Exception as e:
                span.set_attribute("tau2.error", str(e))
                try:
                    from opentelemetry.trace import Status, StatusCode
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                except ImportError:
                    pass
                logger.error(f"Error running task {task.id}, trial {trial}: {e}")
                raise

            return simulation

    # Use context-propagating wrapper
    with ThreadPoolExecutor(max_workers=max_concurrency) as executor:
        res = list(executor.map(_run_with_context, *zip(*args)))
        simulation_results.simulations.extend(res)
```

---

### Phase 4: Instrument Path A (Thread-Pool Execution)

Path A is the current execution model using `run_in_executor`. This requires explicit OTel context propagation because thread boundaries break automatic context inheritance.

**Modify: `tau2_agent/tools/run_tau2_evaluation.py`**

```python
# Add imports
from tau2.telemetry import create_span, get_trace_id
from tau2.telemetry.context import get_current_context, attach_context, detach_context
from tau2.evaluation import EvaluationContext  # Store integration helper

async def _execute(self, ...):
    """Run evaluation with OTel tracing and store integration."""

    with create_span(
        "tau2.evaluation",
        attributes={
            "tau2.domain": domain,
            "tau2.agent_endpoint": agent_endpoint,
            "tau2.num_tasks": num_tasks,
            "tau2.num_trials": num_trials,
            "tau2.max_concurrency": 3,
        },
    ) as span:
        # Create evaluation context - captures trace_id for store correlation
        eval_ctx = EvaluationContext.create(
            domain=domain,
            request={"num_tasks": num_tasks, "num_trials": num_trials},
            agent_endpoint=agent_endpoint,
        )

        # Capture OTel context INSIDE the span for thread propagation
        otel_ctx = get_current_context()

        def run_with_context():
            """Wrapper to run_domain with propagated context."""
            token = attach_context(otel_ctx)
            try:
                return run_domain(config)
            finally:
                detach_context(token)

        try:
            loop = asyncio.get_running_loop()
            results = await loop.run_in_executor(None, run_with_context)

            # Add result attributes to span
            span.set_attribute("tau2.total_simulations", len(results.simulations))
            span.set_attribute("tau2.avg_reward", metrics.avg_reward)
            span.set_attribute("tau2.successful_simulations", successful_sims)

            # Complete store evaluation
            eval_ctx.complete(build_results(results))

            return {...}

        except Exception as e:
            # Fail store evaluation
            eval_ctx.fail(str(e))

            span.set_attribute("tau2.error", str(e))
            try:
                from opentelemetry.trace import Status, StatusCode
                span.set_status(Status(StatusCode.ERROR, str(e)))
            except ImportError:
                pass
            raise
```

---

### Phase 5: Pure Async Path (Future - 004-gym-evaluation)

Path B is the future GymOrchestrator which is pure async. OTel context automatically propagates in async context, so no explicit attach/detach is needed.

**File: `src/tau2/gym/orchestrator.py`** (future implementation)

```python
from tau2.telemetry import create_span
from tau2.evaluation import EvaluationContext

class GymOrchestrator:
    async def run_evaluation(self) -> AsyncIterator[TaskStatusUpdateEvent]:
        """Run evaluation with automatic OTel context propagation."""

        # Context auto-propagates in async - just create span
        with create_span(
            "tau2.evaluation",
            attributes={
                "tau2.domain": self.domain,
                "tau2.agent_endpoint": self.endpoint,
            },
        ) as span:
            # Create evaluation context - trace_id captured automatically
            ctx = EvaluationContext.create(
                domain=self.domain,
                request=self._build_request(),
                agent_endpoint=self.endpoint,
            )

            try:
                for i, task_id in enumerate(task_ids):
                    ctx.update_progress(i + 1, total_tasks)

                    # No context propagation needed - async inherits context
                    result = await self._evaluate_task(task_id)
                    results.append(result)

                    yield TaskStatusUpdateEvent(
                        state=TaskState.WORKING,
                        message={"progress": (i + 1) / total_tasks * 100},
                    )

                ctx.complete(aggregate_results(results))
                yield TaskStatusUpdateEvent(state=TaskState.COMPLETED, ...)

            except Exception as e:
                ctx.fail(str(e))
                yield TaskStatusUpdateEvent(state=TaskState.FAILED, ...)
                raise
```

**Key difference from Path A**: No `get_current_context()`, `attach_context()`, or `detach_context()` calls needed.

---

## Testing Strategy

### Unit Tests

**File: `tests/test_telemetry/test_tracing.py`**
```python
def test_create_span_without_otel():
    """Verify graceful fallback when OTel not configured."""
    with create_span("test.span") as span:
        span.set_attribute("key", "value")  # Should not raise

def test_create_span_with_attributes():
    """Verify attributes are set on spans."""
    # Requires OTel test setup with InMemorySpanExporter
    pass

def test_no_op_tracer_is_safe():
    """Verify no-op tracer doesn't break anything."""
    tracer = _NoOpTracer()
    with tracer.start_as_current_span("test") as span:
        span.set_attribute("key", "value")
```

### Integration Tests

**File: `tests/test_telemetry/test_context_propagation.py`**
```python
def test_context_propagates_to_thread():
    """Verify trace context propagates to thread pool workers."""
    # Create span, capture context, run in thread, verify parent relationship
    pass

def test_concurrent_tasks_have_separate_spans():
    """Verify concurrent tasks create separate child spans."""
    pass
```

### Manual Testing

1. Start ADK web server with tau2_agent
2. Run evaluation via web UI
3. View traces in ADK trace viewer
4. Verify span hierarchy matches expected structure

---

## Dependencies

**Add to `pyproject.toml`**:
```toml
[project.optional-dependencies]
telemetry = [
    "opentelemetry-api>=1.20.0",
]
```

**Note**: Only `opentelemetry-api` is required. The SDK and exporters are provided by ADK.

---

## Store Integration: EvaluationContext Helper

To avoid duplicating store + tracing logic across Path A and Path B, introduce a shared helper:

**File: `src/tau2/evaluation/context.py`**

```python
"""Evaluation lifecycle context manager.

Wraps EvaluationStore with OTel trace_id capture for correlation.
Works with both thread-pool (Path A) and pure async (Path B) execution.
"""
from dataclasses import dataclass

from tau2.store import EvaluationStore, create_store
from tau2.telemetry import get_trace_id


@dataclass
class EvaluationContext:
    """Lifecycle manager for store + tracing."""

    store: EvaluationStore
    evaluation_id: str
    trace_id: str | None

    @classmethod
    def create(
        cls,
        domain: str,
        request: dict,
        agent_endpoint: str,
        store: EvaluationStore | None = None,
    ) -> "EvaluationContext":
        """Create context and initialize store session."""
        store = store or create_store()
        trace_id = get_trace_id()  # From OTel context

        evaluation_id = store.create_session(
            domain=domain,
            request=request,
            trace_id=trace_id,
            agent_endpoint=agent_endpoint,
        )

        return cls(store=store, evaluation_id=evaluation_id, trace_id=trace_id)

    def update_progress(self, current_task: int, total_tasks: int) -> None:
        """Update evaluation progress."""
        self.store.update_progress(self.evaluation_id, current_task, total_tasks)

    def complete(self, results: dict) -> None:
        """Mark evaluation as completed."""
        self.store.complete_evaluation(self.evaluation_id, results)

    def fail(self, error: str) -> None:
        """Mark evaluation as failed."""
        self.store.fail_evaluation(self.evaluation_id, error)
```

**Dependency**: Requires 002-evaluation-store to be implemented (it is).

---

## Rollout Plan

1. **Phase 1**: Merge telemetry module with no-op fallback (zero risk)
2. **Phase 2**: Add A2A client instrumentation (low risk, isolated)
3. **Phase 3**: Add task instrumentation with context propagation (medium risk)
4. **Phase 4-5**: Add ADK tool instrumentation (completes the feature)

Each phase can be tested independently and rolled back if issues arise.

---

## Success Criteria

1. Running `adk web` with tau2_agent shows full span hierarchy in trace view
2. Concurrent tasks (e.g., `max_concurrency=3`) appear as separate sibling spans
3. Each A2A message exchange appears as a child span with latency/token attributes
4. CLI usage without OTel configured works identically to before
5. Less than 5ms overhead per span creation

---

## Open Questions

1. **Content capture**: Should we enable `TAU2_CAPTURE_MESSAGE_CONTENT` by default in ADK mode? (Recommendation: No, opt-in for privacy)
2. **Span naming**: Use `tau2.task.{task_id}` or just `tau2.task` with task_id as attribute? (Recommendation: Attribute for cleaner traces)
3. **Metrics export**: Should we also add OTel metrics for aggregate statistics? (Recommendation: Future enhancement, not MVP)
