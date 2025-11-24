# Implementation Plan: Bidirectional A2A Protocol Integration

**Branch**: `001-a2a-integration` | **Date**: 2025-11-23 | **Last Updated**: 2025-11-24 | **Spec**: [spec.md](spec.md)
**Input**: Feature specification from `/specs/001-a2a-integration/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Implement **bidirectional A2A protocol integration** for tau2-bench with two complementary capabilities:

### Capability 1: tau2 A2A Client (Evaluates Remote A2A Agents)
Adds A2AAgent class following BaseAgent interface pattern, enabling tau2-bench to evaluate A2A-compliant agents via CLI (`tau2 run --agent a2a_agent --agent-a2a-endpoint <url>`) or Python API. Includes protocol translation layer for bidirectional message conversion between tau2-bench and A2A formats.

### Capability 2: tau2 A2A Server (Exposes Evaluations via A2A)
Creates ADK-based agent exposing tau2-bench evaluation capabilities via A2A protocol, allowing external agents to request evaluations programmatically. Implements RunTau2Evaluation and ListDomains tools as ADK BaseTools, with automatic A2A message handling via ADK's built-in a2a-sdk integration.

**Synergy**: Capability 2 depends on Capability 1, as the ADK server uses tau2's A2A client when evaluating A2A target agents.

**Core Value**: Enables tau2-bench to both evaluate A2A agents AND be evaluated by other agents, creating a bidirectional agent evaluation ecosystem with 100% backward compatibility.

## Technical Context

**Language/Version**: Python 3.10+ (per tau2-bench pyproject.toml requires-python)
**Primary Dependencies**: httpx (>=0.28.0) for async HTTP client, a2a-sdk (>=0.3.12) with http-server extras for A2A protocol, google-adk[a2a] for ADK server with A2A support, loguru (>=0.7.3) for structured logging, pydantic for message validation
**Storage**: N/A - stateless protocol translation layer with in-memory session management
**Testing**: pytest (>=8.3.5) with pytest-asyncio for async test support, httpx MockTransport or responses library for HTTP mocking
**Target Platform**: Linux server (primary), cross-platform Python execution
**Project Type**: Single Python package extending existing tau2-bench monorepo
**Performance Goals**: <10% evaluation overhead vs baseline LLM agents, <300ms protocol translation latency, support for 300s agent response timeout
**Constraints**: Zero breaking changes to tau2-bench core (backward compatibility NON-NEGOTIABLE), synchronous execution model (wrap async A2A in sync interface for BaseAgent compatibility), local tool execution only (no remote tool execution on A2A agents)
**Scale/Scope**:
- **tau2 A2A Client**: Single A2A agent type (A2AAgent), 3-4 new modules in src/tau2/agent/a2a_agent.py
- **ADK A2A Server**: ADK agent with 3 tools (RunTau2Evaluation, ListDomains, GetEvaluationResults), agent definition in tau2_agent/
- **Testing**: ~10-15 integration tests (5-7 for client, 5-7 for server, 1-2 end-to-end)
- **Protocol Translation**: Bidirectional translation for 4 message types (UserMessage, AssistantMessage, ToolMessage, MultiToolMessage)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Principle I: A2A/ADK/tau2 Compliance ✅

- **A2A Protocol Compliance**: Design includes bidirectional message translation (tau2 ↔ A2A) preserving semantics (ToolCall ↔ function_call, UserMessage ↔ user message, AssistantMessage ↔ assistant message)
- **tau2-bench Extension Pattern**: A2AAgent implements BaseAgent[A2AState] interface, registers via `registry.register_agent(A2AAgent, "a2a_agent")`
- **Message Fidelity**: Translation preserves tool names, tool arguments (JSON structure), message content, message ordering
- **Tool Execution Locality**: Tools execute locally in tau2-bench, A2A agents only provide reasoning and tool call decisions (FR-010)
- **Rationale**: Core mission alignment verified - A2A agents will evaluate correctly within tau2-bench framework

### Principle II: Backward Compatibility ✅

- **Zero Breaking Changes**: New A2A code isolated in src/tau2/a2a/, no modifications to existing agents (LLMAgent, LLMGTAgent)
- **Agent Registry**: A2AAgent registered alongside existing agents, no changes to existing agent constructors
- **CLI Compatibility**: New flags (--a2a-endpoint, --a2a-auth-token, --a2a-timeout) are additive and optional
- **BaseAgent Interface**: A2AAgent fully implements required methods (generate_next_message, get_init_state, stop, is_stop)
- **Data Model Compatibility**: No changes to Message types (UserMessage, AssistantMessage, ToolMessage)
- **Rationale**: Backward compatibility verified - existing benchmarks will run unchanged (SC-002)

### Principle III: Metrics & Observability ✅

- **Token Usage Tracking**: Protocol metrics track input/output tokens per A2A request/response (FR-021)
- **Execution Time Metrics**: Measure A2A protocol latency separate from local processing (FR-022)
- **Protocol Instrumentation**: Structured logging for all A2A interactions with endpoint, status, timing, context IDs (FR-023)
- **Metrics Export**: JSON export for A2A-specific metrics (tokens, latency, overhead) (FR-024)
- **Rationale**: Observability requirements satisfied - enables cost estimation and performance analysis

### Principle IV: Testing Philosophy ✅

- **Pragmatic Integration Testing**: Plan includes 5-10 integration tests covering core A2A functionality (SC-003)
- **Test Coverage**: Tests cover message translation, agent registration, tool calling, error handling, metrics (FR-006 through FR-025)
- **Test Isolation**: Use httpx MockTransport for HTTP mocking, fresh fixtures per test
- **No Coverage Gates**: Following tau2's pragmatic approach (~20-30% coverage target for new code)
- **Rationale**: Testing approach aligns with tau2-bench philosophy - sufficient for confidence without over-engineering

### Principle V: Code Quality Guidelines ✅

- **Type Hints**: Plan includes type hints for public APIs (A2AAgent, translation functions)
- **Async Patterns**: A2A uses httpx.AsyncClient, async/await for network I/O
- **Error Handling**: A2A protocol errors wrapped in A2AError exception type (FR-025)
- **Structured Logging**: loguru with structured context (endpoint, status, latency, context IDs)
- **Rationale**: Code quality standards met - type safety, async patterns, proper error handling

### Principle VI: Architecture Principles ✅

- **Separation of Concerns**: A2A implementation in src/tau2/a2a/, core tau2 code unchanged
- **Interface Compliance**: A2AAgent implements BaseAgent[A2AState] following llm_agent.py pattern
- **Registry Pattern**: Registers via tau2 registry for CLI usage
- **Message Translation Layer**: Bidirectional translators in src/tau2/a2a/translation.py
- **Configuration Management**: A2A config passed via constructor (endpoint, auth_token, timeout)
- **Rationale**: Architecture follows tau2 patterns - isolated, testable, registry-based

### Principle VII: Documentation Standards ✅

- **Docstrings**: Plan includes Google-style docstrings for public APIs
- **README Examples**: Quickstart.md will include A2A agent usage examples (Phase 1)
- **Architecture Documentation**: Plan includes data-model.md and contracts/ for A2A protocol details (Phase 1)
- **Inline Comments**: Translation code will document A2A spec requirements
- **Rationale**: Documentation standards met - public APIs documented, examples provided

### Gate Decision: **PASS** ✅

All constitution principles satisfied. No violations requiring complexity justification. Proceed to Phase 0 research.

---

## Post-Design Constitution Re-Check

*Re-evaluated after Phase 1 design (research.md, data-model.md, contracts/, quickstart.md completed)*

### Principle I: A2A/ADK/tau2 Compliance ✅ VERIFIED

**Design Validation**:
- ✅ **Message translation** defined in research.md with tau2 ↔ A2A mappings (TextPart for messages, DataPart for tool calls)
- ✅ **BaseAgent compliance** verified in data-model.md (A2AAgentState implements required state pattern)
- ✅ **Tool execution locality** enforced (data-model.md specifies tools execute in tau2-bench, not remote agent)
- ✅ **Message fidelity** preserved (tool names, arguments, content, ordering maintained in translation)
- ✅ **Protocol contracts** documented (contracts/ defines JSON-RPC 2.0 message/send, agent discovery)

**Rationale**: Design artifacts confirm A2A protocol compliance. Message translation patterns preserve semantics. Tool execution remains local per constitution.

### Principle II: Backward Compatibility ✅ VERIFIED

**Design Validation**:
- ✅ **Zero breaking changes** confirmed (new modules in src/tau2/a2a/, no modifications to existing agents)
- ✅ **CLI additive only** verified (--agent-a2a-* flags are optional, existing flags unchanged)
- ✅ **BaseAgent interface** compliance documented (A2AAgent implements generate_next_message, get_init_state, stop)
- ✅ **Data model compatibility** preserved (no changes to UserMessage, AssistantMessage, ToolMessage)
- ✅ **Isolated implementation** confirmed (contracts/ show A2A is separate protocol layer)

**Rationale**: Design review confirms backward compatibility. Existing workflows unaffected. Registry pattern enables coexistence.

### Principle III: Metrics & Observability ✅ VERIFIED

**Design Validation**:
- ✅ **Token tracking** designed (ProtocolMetrics entity includes input_tokens, output_tokens per request)
- ✅ **Latency metrics** specified (latency_ms per request, aggregated to avg_latency_ms, total_latency_ms)
- ✅ **Protocol instrumentation** defined (research.md specifies loguru structured logging with endpoint, status, timing)
- ✅ **Metrics export** documented (data-model.md defines JSON export format with task-level and summary metrics)
- ✅ **Overhead calculation** included (quickstart.md shows overhead_pct = (a2a_time - llm_baseline_time) / llm_baseline_time * 100)

**Rationale**: Observability design meets requirements. Token counting enables cost estimation. Metrics export supports analysis.

### Principle IV: Testing Philosophy ✅ VERIFIED

**Design Validation**:
- ✅ **Integration test approach** confirmed (research.md specifies httpx.MockTransport for protocol testing)
- ✅ **Test patterns** documented (research.md provides mock handler examples for success/error scenarios)
- ✅ **Coverage target** acknowledged (~20-30% for new A2A code, matching tau2 philosophy)
- ✅ **Test isolation** designed (MockTransport enables deterministic, fast, isolated tests)
- ✅ **Pragmatic scope** maintained (5-10 integration tests covering message translation, tool calling, errors)

**Rationale**: Testing design aligns with tau2's pragmatic approach. Integration-focused, not unit-coverage-driven.

### Principle V: Code Quality Guidelines ✅ VERIFIED

**Design Validation**:
- ✅ **Type hints** planned (data-model.md uses pydantic for validation, includes type annotations)
- ✅ **Async patterns** confirmed (research.md specifies httpx.AsyncClient, asyncio.run() wrapper)
- ✅ **Error handling** designed (A2AError exception type, httpx exception hierarchy documented)
- ✅ **Structured logging** specified (loguru with structured context: endpoint, status, latency, context_id)
- ✅ **No auth tokens in logs** enforced (research.md explicitly warns against logging auth tokens)

**Rationale**: Code quality standards embedded in design. Async patterns for performance. Structured logging for debugging.

### Principle VI: Architecture Principles ✅ VERIFIED

**Design Validation**:
- ✅ **Separation of concerns** confirmed (src/tau2/a2a/ module isolation, contracts/ separate from core)
- ✅ **Interface compliance** verified (A2AAgentState follows BaseAgent[AgentState] pattern)
- ✅ **Registry pattern** documented (quickstart.md shows --agent a2a_agent CLI usage)
- ✅ **Translation layer** designed (research.md defines tau2_to_a2a() and a2a_to_tau2() functions)
- ✅ **Configuration management** specified (A2AConfig dataclass with endpoint, auth_token, timeout)

**Rationale**: Architecture design follows tau2 patterns. Isolated, testable, registry-based.

### Principle VII: Documentation Standards ✅ VERIFIED

**Design Validation**:
- ✅ **Docstrings** planned (data-model.md includes docstring examples for public APIs)
- ✅ **README examples** delivered (quickstart.md provides complete usage examples with CLI flags)
- ✅ **Architecture docs** completed (research.md documents protocol patterns, data-model.md defines entities, contracts/ specify APIs)
- ✅ **Inline comments** guidance (research.md notes "why" over "what" for translation logic)
- ✅ **API contracts** formalized (contracts/ includes OpenAPI 3.0 specs for message protocol and discovery)

**Rationale**: Documentation exceeds requirements. Quickstart enables immediate usage. Contracts provide API reference.

### Post-Design Gate Decision: **PASS** ✅

**Summary**: All constitution principles re-verified after Phase 1 design. Design artifacts (research.md, data-model.md, contracts/, quickstart.md) demonstrate compliance with A2A protocol, backward compatibility, observability, testing philosophy, code quality, architecture, and documentation standards.

**No design changes required**. Proceed to Phase 2 (task generation via /speckit.tasks).

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
src/tau2/
├── agent/
│   ├── base.py             # UNCHANGED: BaseAgent interface
│   ├── llm_agent.py        # UNCHANGED: Existing LLM agent
│   ├── a2a_agent.py        # NEW: A2AAgent class (Capability 1: Client)
│   └── __init__.py
├── data_model/             # UNCHANGED: tau2 message types
├── registry.py             # MINOR UPDATE: Register A2AAgent
└── cli.py                  # UNCHANGED: Uses registry for --agent a2a_agent

tau2_agent/                 # NEW: ADK agent directory (Capability 2: Server)
├── __init__.py
├── agent.py                # ADK LlmAgent with tau2 evaluation tools
└── tools/
    ├── __init__.py
    ├── run_tau2_evaluation.py  # RunTau2Evaluation BaseTool
    ├── list_domains.py         # ListDomains BaseTool
    └── get_evaluation_results.py  # GetEvaluationResults BaseTool

tests/
├── test_a2a_client/        # NEW: tau2 A2A client tests (Capability 1)
│   ├── __init__.py
│   ├── test_a2a_agent.py   # A2AAgent integration tests
│   └── test_message_translation.py  # tau2 ↔ A2A translation tests
├── test_adk_server/        # NEW: ADK server tests (Capability 2)
│   ├── __init__.py
│   ├── test_agent_card.py  # Agent discovery tests
│   ├── test_tools.py       # ADK tool execution tests
│   └── test_a2a_endpoint.py  # A2A message/send endpoint tests
└── test_a2a_e2e/           # NEW: End-to-end A2A integration tests
    ├── __init__.py
    ├── test_evaluation_flow.py     # Complete A2A loop tests
    └── test_client_to_server.py    # Client-server communication tests
```

**Structure Decision**: Single Python project extending existing tau2-bench monorepo. New A2A code isolated in src/tau2/a2a/ module following tau2's registry pattern. Tests in tests/test_a2a/ mirroring tau2's test structure. Minimal changes to existing code (registry registration, CLI flags only).

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

**No violations**: Constitution Check passed all gates. No complexity justification required.
