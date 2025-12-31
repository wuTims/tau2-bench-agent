# Feature Specification: OpenTelemetry Integration for A2A Trace Visibility

**Feature Branch**: `006-otel-integration`
**Created**: 2025-12-11
**Status**: Draft

**Input**: "Add OpenTelemetry instrumentation to tau2 A2A communication so that per-task A2A message traces appear in the ADK web viewer in real-time, especially when running concurrent evaluations"

## Problem Statement

When running tau2 evaluations via the ADK web UI, users can only see top-level tool calls (e.g., `run_tau2_evaluation`). The detailed A2A message exchanges between tau2_agent and the agent being evaluated are invisible because:

1. ADK uses OpenTelemetry for tracing, but tau2 doesn't emit OTel spans
2. Evaluations run in a thread pool (`run_in_executor`), so trace context doesn't propagate
3. With concurrent tasks (e.g., `max_concurrency=3`), console logs become interleaved and unusable

## Architecture Overview

```
ADK Web UI (Trace Viewer)
        ↑
        │ OpenTelemetry Spans
        │
┌───────┴────────────────────────────────────────────┐
│ tau2_agent                                          │
│   └── execute_tool (run_tau2_evaluation)            │
│         └── [OTel context propagation]              │
│               ├── tau2.task (task_001)              │
│               │     ├── tau2.a2a.message (→agent)   │
│               │     ├── tau2.a2a.message (←agent)   │
│               │     └── ...                         │
│               ├── tau2.task (task_002)              │
│               └── tau2.task (task_003)              │
└─────────────────────────────────────────────────────┘
```

## User Scenarios & Testing

### User Story 1 - View Per-Task A2A Traces in ADK Web UI (Priority: P1)

A developer running evaluations via ADK web mode wants to see the detailed A2A message exchanges for each task in real-time, with clear task separation even when tasks run concurrently.

**Why this priority**: Core value proposition - enables debugging and understanding of agent behavior during evaluation without parsing interleaved console logs.

**Acceptance Scenarios**:

1. **Given** an evaluation running 3 tasks concurrently, **When** viewing the ADK web UI trace view, **Then** each task appears as a separate child span under `execute_tool` with clear task ID labels
2. **Given** a task with multiple A2A message exchanges, **When** expanding the task span, **Then** each message appears as a child span showing direction (request/response), latency, and token counts
3. **Given** a completed evaluation, **When** viewing the trace, **Then** the span hierarchy shows: `execute_tool` → `tau2.task.{id}` → `tau2.a2a.message`

---

### User Story 2 - Trace Context Propagation Across Threads (Priority: P1)

A developer wants trace context to properly propagate when evaluations run in thread pools, ensuring all child spans appear under the correct parent.

**Why this priority**: Without proper context propagation, spans would be orphaned and not visible in the ADK trace hierarchy.

**Acceptance Scenarios**:

1. **Given** an evaluation executed via `run_in_executor`, **When** tau2 emits spans, **Then** all spans appear as children of the `execute_tool` span in the trace view
2. **Given** multiple concurrent evaluations from different ADK sessions, **When** viewing traces, **Then** each evaluation's spans are correctly associated with their respective session traces
3. **Given** the OTel tracer provider from ADK, **When** tau2 creates spans, **Then** spans use the same tracer provider and appear in ADK's span exporters

---

### User Story 3 - Span Attributes for Debugging (Priority: P2)

A developer debugging a failed task wants to see detailed attributes on each span including request/response content, token counts, latency, and error information.

**Why this priority**: Attributes enable effective debugging without needing to check separate log files.

**Acceptance Scenarios**:

1. **Given** an A2A message span, **When** viewing span attributes, **Then** the span includes: `tau2.task_id`, `tau2.endpoint`, `tau2.request_id`, `tau2.latency_ms`, `tau2.input_tokens`, `tau2.output_tokens`
2. **Given** a task span, **When** viewing attributes, **Then** the span includes: `tau2.task_id`, `tau2.domain`, `tau2.trial`, `tau2.reward` (on completion)
3. **Given** a failed A2A request, **When** viewing the span, **Then** the span status is ERROR with `tau2.error` attribute containing the error message

---

### User Story 4 - Backward Compatibility (Priority: P1)

An existing tau2 CLI user wants evaluations to work identically whether OTel is configured or not.

**Why this priority**: Must not break existing workflows or require OTel setup for CLI usage.

**Acceptance Scenarios**:

1. **Given** tau2 CLI without OTel configured, **When** running evaluations, **Then** behavior is identical to before (no errors, no performance impact)
2. **Given** tau2 running under ADK with OTel configured, **When** running evaluations, **Then** spans are automatically emitted without additional configuration
3. **Given** the `--a2a-debug` flag, **When** OTel is also active, **Then** both console logging and OTel spans work simultaneously

## Functional Requirements

### FR-001: OpenTelemetry Tracer Integration (P0)
- tau2 SHALL obtain a tracer via `opentelemetry.trace.get_tracer("tau2")`
- tau2 SHALL use the globally configured TracerProvider (set by ADK or user)
- tau2 SHALL gracefully handle missing OTel configuration (no-op tracer)

### FR-001a: Evaluation Span Creation (P0)
- tau2 SHALL create a span named `tau2.evaluation` for each evaluation run
- Evaluation spans SHALL include attributes: `tau2.domain`, `tau2.agent_endpoint`, `tau2.num_tasks`
- This span is sufficient for trace_id extraction and store correlation

### FR-002: Task Span Creation (P1 - Enhancement)
- tau2 SHALL create a span named `tau2.task` for each task evaluation
- Task spans SHALL include attributes: `tau2.task_id`, `tau2.domain`, `tau2.trial`, `tau2.seed`
- Task spans SHALL be children of the evaluation span

### FR-003: A2A Message Span Creation (P2 - Detailed Debugging)
- tau2 SHALL create a span named `tau2.a2a.message` for each A2A request/response
- Message spans SHALL be children of their corresponding task span
- Message spans SHALL include attributes: `tau2.request_id`, `tau2.endpoint`, `tau2.latency_ms`, `tau2.input_tokens`, `tau2.output_tokens`, `tau2.context_id`

### FR-004: Trace Context Propagation (P0)
- tau2 SHALL propagate trace context into thread pool executors (Path A)
- tau2 SHALL use `opentelemetry.context.attach()` to set context in worker threads
- tau2 SHALL properly detach context after task completion
- Pure async paths (Path B) do not require explicit propagation

### FR-005: Error Recording (P1)
- Failed A2A requests SHALL set span status to ERROR
- Error spans SHALL include `tau2.error` attribute with error message
- Timeout errors SHALL include `tau2.timeout_ms` attribute

### FR-006: Content Capture (P2 - Optional)
- Message content capture SHALL be controlled by environment variable `TAU2_CAPTURE_MESSAGE_CONTENT`
- When enabled, spans SHALL include `tau2.request_content` and `tau2.response_content` attributes
- Content SHALL be truncated to 10KB to avoid span size limits

## Non-Functional Requirements

### NFR-001: Performance
- OTel instrumentation SHALL add less than 5ms overhead per span
- Span creation SHALL not block A2A request processing

### NFR-002: Memory
- Span data SHALL not accumulate in memory (relies on OTel exporters)
- Large content attributes SHALL be truncated

### NFR-003: Compatibility
- SHALL work with OpenTelemetry Python SDK 1.20+
- SHALL work with ADK's built-in span processors
- SHALL not require additional OTel dependencies beyond `opentelemetry-api`

## Technical Constraints

- **Thread Safety**: Spans must be created in the correct thread context
- **Async/Sync Bridge**: tau2 uses sync code in thread pools; must handle context correctly
- **No Breaking Changes**: Existing tau2 modules must work unchanged when OTel not configured

---

## Execution Path Considerations

tau2 has two execution paths with different OTel context propagation requirements:

### Path A: Thread-Pool Execution (Current)

The current `run_tau2_evaluation.py` uses `run_in_executor` which creates a worker thread:

```
ADK Tool (async context with OTel span)
    └── run_in_executor()  ← Context lost here!
        └── run_domain() (sync in thread - no parent span)
```

**Challenge**: OTel context does NOT auto-propagate across thread boundaries.

**Solution**: Explicit context propagation
```python
ctx = get_current_context()  # Capture in async context

def run_with_context():
    token = attach_context(ctx)  # Attach in worker thread
    try:
        return run_domain(config)
    finally:
        detach_context(token)

results = await loop.run_in_executor(None, run_with_context)
```

### Path B: Pure Async Execution (Future - 004-gym-evaluation)

The future GymOrchestrator (004-gym-evaluation) is pure async:

```
Tau2RouterAgent (async)
    └── GymOrchestrator.run_evaluation() (async)
        └── await _evaluate_task() (async)
```

**No special handling required** - OTel context automatically propagates in async context. Use `create_span()` directly.

---

## Store Integration (Dependency: 002-evaluation-store)

OTel trace_id enables correlation between:
- Trace spans in ADK web UI / Datadog / Jaeger
- Stored evaluation records in `data/evaluations/`

This allows developers to click a trace in Datadog/Jaeger and find the corresponding evaluation record, or vice versa.

### FR-007: Trace ID Extraction
- tau2 SHALL extract trace_id from the current span context
- trace_id SHALL be W3C Trace Context format (32 hex characters)
- Missing trace_id SHALL result in null (no error)

### FR-008: Store Correlation
- EvaluationContext SHALL pass trace_id to store.create_session()
- Stored evaluation records SHALL include trace_id for later correlation
- Query by trace_id SHALL be supported via store.get_evaluation_by_trace_id()

---

## Dependencies

- **002-evaluation-store**: Provides `trace_id` field in evaluation records
- **004-gym-evaluation**: Future pure async path (no context propagation needed)
