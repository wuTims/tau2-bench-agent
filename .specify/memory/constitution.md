<!--
============================================================================
Sync Impact Report
============================================================================
Version change: 1.0.0 → 1.1.0
Rationale: Material refinement to focus on core mission (A2A/ADK/tau2 compliance)
          and match tau2-bench's pragmatic development philosophy

Modified principles:
  - Principle I: "Code Quality Standards" → "A2A/ADK/tau2 Compliance" (reordered, refocused on primary mission)
  - Principle II: "Testing Requirements" → "Testing Philosophy" (softened to match tau2's pragmatic approach)
  - Principle V: "Code Quality Standards" (softened from strict to guidelines)

Added sections:
  - Principle III: Metrics & Observability (NEW - critical for benchmarking)
  - Guidelines: Performance Monitoring (moved from strict requirements)
  - Guidelines: Security Best Practices (moved from strict requirements)

Removed sections:
  - Strict security requirements (moved to guidelines)
  - Strict performance requirements (moved to guidelines)
  - Technology Stack section (too prescriptive, moved to inline guidance)

Reordered principles:
  - A2A/ADK/tau2 Compliance now Principle I (was scattered across principles)
  - Backward Compatibility now Principle II (elevated importance, NON-NEGOTIABLE)
  - Metrics & Observability now Principle III (NEW)
  - Testing Philosophy now Principle IV (was II, softened)
  - Code Quality Guidelines now Principle V (was I, softened)
  - Architecture Principles now Principle VI (was IV, unchanged)
  - Documentation Standards now Principle VII (was V, unchanged)

Templates requiring updates:
  ✅ plan-template.md - Constitution Check section aligns with new principle order
  ✅ spec-template.md - Requirements section aligns with updated standards
  ✅ tasks-template.md - Task structure supports pragmatic testing approach

Follow-up TODOs: None
============================================================================
-->

# tau2-bench-agent Development Constitution

## Core Principles

### I. A2A/ADK/tau2 Compliance (PRIMARY MISSION)

**Mission**: Extend tau2-bench to support A2A protocol agents and Google ADK integration while preserving tau2-bench's evaluation integrity.

**A2A Protocol Compliance**: A2A agents MUST communicate using the Agent-to-Agent protocol specification. Message translation MUST preserve semantics: tau2 ToolCall ↔ A2A function_call, tau2 UserMessage ↔ A2A user message, tau2 AssistantMessage ↔ A2A assistant message. Translation MUST be bidirectional for supported message types.

**ADK Integration**: Google ADK agents MUST integrate through the A2A adapter layer. ADK-specific features (context extensions, streaming) MAY be supported when they map to tau2-bench concepts. Unmapped features SHOULD log warnings and gracefully degrade.

**tau2-bench Extension Pattern**: Follow tau2's registry pattern (see src/tau2/registry.py). New agents MUST implement BaseAgent[AgentState] interface. Register via `registry.register_agent(A2AAgent, "a2a_agent")`. New domains follow `registry.register_domain()` pattern. Extend, don't modify core tau2 code.

**Message Fidelity**: Translation MUST preserve: tool names, tool arguments (JSON structure), message content text, message ordering. Metadata (timestamps, turn indices) SHOULD be preserved when present. Errors during translation MUST be logged with structured context (message type, translation direction, error details).

**Tool Execution Locality**: Tools MUST execute in the tau2-bench process, NOT on remote A2A agents. A2A agents receive tool schemas via protocol and respond with tool calls. tau2-bench executes tools and returns ToolMessage results. This preserves evaluation isolation and reproducibility.

**Rationale**: This is the core value proposition. A2A/ADK agents must evaluate correctly within tau2-bench. Message fidelity ensures fair evaluation. Local tool execution prevents non-determinism. Following tau2 patterns ensures maintainability.

### II. Backward Compatibility (NON-NEGOTIABLE)

**Zero Breaking Changes**: Existing tau2-bench functionality MUST remain unchanged. All existing unit tests MUST pass without modification. Evaluation results for LLM-based agents (LLMAgent, LLMGTAgent, LLMSoloAgent) MUST remain reproducible. Published benchmark results MUST NOT be invalidated.

**Agent Registry**: A2AAgent MUST be registered alongside existing agents via the registry pattern (see src/tau2/registry.py:83-94). Existing agent constructors and interfaces MUST NOT be modified. Registry lookup MUST support both old and new agent names.

**CLI Compatibility**: All new CLI flags MUST be additive only. Existing flags (`--agent`, `--user-llm`, `--domain`, etc.) MUST NOT change semantics or defaults. The `--agent` flag MUST accept new A2A agent names without breaking existing agent names. New flags (e.g., `--a2a-endpoint`, `--a2a-auth-token`) MUST be optional.

**BaseAgent Interface**: A2AAgent MUST fully implement the BaseAgent[AgentState] interface (src/tau2/agent/base.py:37-101): `generate_next_message()`, `get_init_state()`, `stop()`, `is_stop()`. Signature compatibility is required. Return types MUST match: `tuple[AssistantMessage, AgentState]`.

**Data Model Compatibility**: Message types (UserMessage, AssistantMessage, ToolMessage) MUST NOT change. Serialization format for trajectories MUST remain compatible with existing evaluation and leaderboard infrastructure.

**Rationale**: tau2-bench has published research results (arxiv:2506.07982) and an active leaderboard (taubench.com). Breaking changes invalidate comparisons and damage trust. The extension pattern (registry + BaseAgent) enables coexistence without disruption.

### III. Metrics & Observability

**Token Usage Tracking**: Track input/output tokens for all LLM calls (both A2A protocol calls and local LLM agents). Expose via metrics: `a2a_tokens_input`, `a2a_tokens_output`, `total_tokens`. Enable cost estimation: `estimated_cost = (input_tokens * input_price + output_tokens * output_price)`. Aggregate per task, per domain, per evaluation run.

**Execution Time Metrics**: Measure and log: (1) total task execution time, (2) A2A protocol latency (request → response), (3) tool execution time, (4) LLM generation time. Expose via structured logs and summary statistics. Enable performance analysis and optimization.

**Evaluation Overhead Monitoring**: Calculate overhead: `overhead_pct = (a2a_time - llm_baseline_time) / llm_baseline_time * 100`. Log overhead per task. Aggregate statistics across evaluation runs. Target: keep overhead visible and measurable for optimization.

**Protocol Instrumentation**: Log all A2A protocol interactions with structured context: endpoint, HTTP status, request/response size, latency. Use loguru with structured fields: `logger.info("A2A request", endpoint=url, latency_ms=duration, status=200)`. Enable debugging distributed agent interactions.

**Metrics Export**: Support exporting metrics to JSON for analysis. Include in evaluation summary output. Format: `{"task_id": "...", "tokens": {...}, "timing": {...}, "overhead_pct": ...}`. Enable integration with analysis pipelines.

**Rationale**: Benchmarking requires measuring cost (tokens) and performance (time). A2A protocol introduces network overhead - must be measurable. Token tracking enables cost estimation for researchers. Structured logging enables debugging production issues.

### IV. Testing Philosophy

**Pragmatic Integration Testing**: Follow tau2-bench's pragmatic testing approach. Focus on integration tests that verify correctness, not comprehensive unit tests that achieve coverage metrics. Add 5-10 integration tests covering core A2A functionality. Tests SHOULD verify components work together, not test every edge case.

**Match tau2 Test Patterns**: Mirror tau2's test structure. Place tests in `tests/test_a2a/` or `tests/test_domains/test_a2a/`. Use pytest fixtures from `tests/conftest.py`. Follow existing test patterns from `test_environment.py`, `test_orchestrator.py`, `test_domains/test_retail/test_tools_retail.py`.

**Integration Test Coverage**: Tests MUST cover: (1) A2A message translation (tau2 ↔ A2A format), (2) A2A agent registration and initialization, (3) Tool schema translation and tool call execution, (4) End-to-end task evaluation with mock A2A server. Use mock HTTP servers (httpx MockTransport or responses library), not real endpoints.

**Test Isolation**: Tests MUST NOT share state. Use fresh fixtures per test. Mock HTTP servers SHOULD run on random ports to enable parallel execution. Async fixtures MUST properly clean up event loops (use `pytest-asyncio`).

**No Coverage Gates**: Do NOT add coverage tooling (.coveragerc, coverage.py). Do NOT set coverage percentage requirements. Tests should be sufficient for confidence, not exhaustive. Aim for ~20-30% coverage of new A2A code, matching tau2's overall coverage level.

**Experimental Code**: For experimental A2A features, basic smoke tests are recommended but NOT required. Follow tau2's CONTRIBUTING.md guidance: "Experimental code: Basic smoke tests recommended but not required."

**Rationale**: tau2-bench uses pragmatic, integration-focused testing (~20-30% coverage, no CI test gates). Strict TDD and coverage requirements would be inconsistent with tau2's philosophy. Integration tests verify the core value (A2A agents work), which is sufficient.

### V. Code Quality Guidelines

**Type Hints for Public APIs**: Use type hints for all public functions and classes. Include parameter types, return types. Generic types SHOULD use TypeVar declarations (see src/tau2/agent/base.py:16). Internal/private functions MAY omit type hints if types are obvious. Aim for mypy compatibility, but strict mode is NOT required.

**Async Patterns**: A2A and ADK interactions SHOULD use async/await patterns. HTTP clients SHOULD be async (httpx.AsyncClient, aiohttp). Async resources SHOULD be cleaned up via async context managers or explicit shutdown. Avoid blocking the event loop with synchronous I/O in async contexts.

**Error Handling**: Catch and handle exceptions with informative messages. A2A protocol errors SHOULD be wrapped in domain-specific exception types (e.g., `A2AError`, following `AgentError` pattern from src/tau2/agent/base.py:20). Error messages SHOULD NOT expose sensitive data (auth tokens). Include context in error messages: operation, endpoint, status code.

**Structured Logging**: Use loguru for logging (matches tau2 convention). A2A protocol interactions SHOULD log structured context: `logger.info("A2A call", endpoint=url, status=200, latency_ms=123)`. Auth tokens MUST NEVER appear in logs. Use `logger.debug()` for verbose details, `logger.info()` for protocol events, `logger.error()` for failures.

**Code Formatting**: Follow tau2's formatting: black for Python formatting, ruff for linting. Use existing tau2 configurations (pyproject.toml). Run `black .` and `ruff check .` before committing.

**Rationale**: Type hints improve IDE support and catch bugs early, but strict mypy enforcement is overkill. Async patterns are needed for network I/O performance. Structured logging enables debugging distributed systems. Consistency with tau2 conventions (loguru, black, ruff) eases maintenance.

### VI. Architecture Principles

**Separation of Concerns**: A2A implementation SHOULD live in separate modules (src/tau2/a2a/). Core tau2-bench code (orchestrator, environment, evaluator) MUST NOT import A2A modules. A2A modules MAY import tau2 base classes (BaseAgent, Message types, Environment). This prevents A2A complexity from polluting the core.

**Interface Compliance**: A2AAgent MUST implement BaseAgent[AgentState]. Follow the pattern in src/tau2/agent/llm_agent.py. Implement required methods: `generate_next_message()`, `get_init_state()`, `stop()`. Optionally override: `is_stop()`, `set_seed()`. State type can be custom (e.g., `A2AState` with session info).

**Registry Pattern**: Register A2A components via tau2's registry (src/tau2/registry.py). Example:
```python
from tau2.registry import registry
from tau2.agent.a2a_agent import A2AAgent

registry.register_agent(A2AAgent, "a2a_agent")
```
This enables CLI usage: `tau2 run --agent a2a_agent --a2a-endpoint http://...`

**Message Translation Layer**: Create bidirectional translators: `tau2_to_a2a(msg: Message) -> A2AMessage` and `a2a_to_tau2(msg: A2AMessage) -> Message`. Place in `src/tau2/a2a/translation.py`. Handle all tau2 message types: UserMessage, AssistantMessage, ToolMessage, MultiToolMessage. Raise ValueError for unsupported message types.

**Configuration Management**: A2A config (endpoint URL, auth token, timeout) SHOULD be passed via constructor or environment variables. Avoid global state. Example: `A2AAgent(endpoint=url, auth_token=token, timeout=300)`. CLI flags map to constructor args.

**Rationale**: Separation keeps A2A code isolated and testable. BaseAgent compliance enables drop-in replacement in tau2's orchestrator. Registry pattern matches tau2 conventions. Translation layer centralizes message conversion logic.

### VII. Documentation Standards

**Docstrings**: Public APIs (classes, functions) SHOULD have Google-style docstrings. Include: purpose, parameters (with types), return value (with type), exceptions raised. Example:

```python
def translate_message(msg: Message) -> A2AMessage:
    """Translate tau2 Message to A2A protocol format.

    Args:
        msg: tau2 Message (UserMessage, AssistantMessage, ToolMessage)

    Returns:
        A2AMessage in A2A protocol format

    Raises:
        ValueError: If message type is not supported
    """
```

**Type Hints**: Include type hints in docstrings for clarity, especially for complex types. Example: `state (A2AState): Current agent state with session info`.

**README Examples**: README SHOULD include working example of A2A agent usage. Show: (1) endpoint configuration, (2) auth token setup (env var), (3) running evaluation with `tau2 run --agent a2a_agent --a2a-endpoint ...`. Include ADK example if ADK support is implemented.

**Architecture Documentation**: Create docs/a2a-architecture.md or update existing design docs. Document: (1) A2A message translation logic (tau2 ↔ A2A mappings), (2) auth token flow, (3) timeout behavior, (4) error handling strategy, (5) unsupported features and limitations.

**Inline Comments**: Use comments for non-obvious logic, especially in translation code. Avoid obvious comments ("increment counter"). Focus on "why" not "what": `# A2A spec requires function_call.id, generate UUID if missing`.

**Rationale**: Google-style docstrings match tau2-bench conventions. Examples reduce onboarding friction. Architecture docs help future maintainers. Good documentation is especially important for protocol translation code where bugs are subtle.

## Guidelines (Non-Strict)

### Performance Monitoring

**Monitor Overhead**: Track evaluation overhead (A2A time vs LLM baseline). Target <10% overhead for typical tasks. If overhead exceeds 10%, investigate and optimize (connection pooling, reduce translation overhead, optimize serialization).

**Configurable Timeouts**: Support configurable timeouts for HTTP requests. Reasonable defaults: 300s for agent generation (matches tau2's LLM timeout), 30s for health checks. Expose via CLI: `--a2a-timeout 300`. Prevent hung evaluations with timeout enforcement.

**Connection Pooling**: Use HTTP client connection pooling (httpx.AsyncClient with limits). Reuse connections across requests. Limit concurrent connections to prevent resource exhaustion. Example: `httpx.AsyncClient(limits=httpx.Limits(max_connections=100))`.

**Resource Cleanup**: Clean up async resources on shutdown. Use async context managers where possible. Ensure clients are closed even on exceptions: `async with httpx.AsyncClient() as client: ...` or `try/finally` blocks.

### Security Best Practices

**Auth Token Protection**: Do NOT log auth tokens. Do NOT include tokens in error messages. Pass tokens via environment variables (recommended) or secure config files. CLI `--a2a-auth-token` MAY be supported but SHOULD warn about shell history exposure. Example: `logger.warning("Token via CLI flag may be exposed in shell history")`.

**Input Validation**: Validate A2A endpoint URLs. Check scheme is http/https. Reject suspicious URLs (file://, javascript:, etc.). Example: `if not url.startswith(("http://", "https://")): raise ValueError("Invalid URL scheme")`. Validation prevents basic injection attacks.

**Error Sanitization**: Error messages shown to users SHOULD NOT contain: auth tokens, internal file paths, stack traces with sensitive data. Include enough context for debugging but not sensitive details. Stack traces MAY be logged at DEBUG level for developer debugging.

**Timeout Enforcement**: Enforce timeouts on all network operations. Prevent resource exhaustion from hung connections. Log timeout events for monitoring: `logger.warning("A2A request timeout", endpoint=url, timeout_s=300)`.

## Technology Stack

**Language**: Python 3.10+ (matches tau2-bench requirement from README.md)

**HTTP Client**: httpx (async support, good test mocking) or aiohttp (mature, widely used)

**Validation**: pydantic for A2A message models (matches tau2 convention, see src/tau2/data_model/)

**Logging**: loguru (matches tau2 convention, see imports in src/tau2/)

**Testing**: pytest + pytest-asyncio (matches tau2, see tests/)

**ADK**: Google ADK library when available (version TBD based on official release)

## Development Workflow

**Branch Strategy**: Feature branches off `main`. Branch names: `feature/a2a-client`, `feature/a2a-agent`, `feature/adk-integration`. Merge to `main` via PR after review.

**Commit Messages**: Follow Conventional Commits: `feat:`, `fix:`, `docs:`, `test:`, `refactor:`. Example: `feat(a2a): add message translation for ToolCall`, `test(a2a): add integration test for agent initialization`.

**Code Review**: PRs MUST pass: (1) all existing tests, (2) new tests for changes, (3) code review from maintainer. PRs SHOULD pass: black formatting, ruff linting. Breaking changes (violate Principle II) MUST be rejected.

**Manual CI**: tau2-bench does not run tests in CI (see .github/workflows/). Run tests manually before PR: `pytest tests/`. Verify backward compatibility: all existing tests pass.

## Governance

**Constitution Authority**: This constitution governs all tau2-bench-agent development. In conflicts between this document and other guidance, this document prevails.

**Amendment Process**: Amendments require: (1) written proposal with rationale, (2) review by maintainers, (3) version bump following semantic versioning. Breaking principle changes = MAJOR bump, new sections/principles = MINOR bump, clarifications = PATCH bump.

**Compliance Verification**: All PRs SHOULD verify:
- [ ] Backward compatibility: existing tests pass without modification
- [ ] A2A compliance: message translation preserves semantics
- [ ] BaseAgent interface: A2A agent implements required methods
- [ ] Metrics: token usage and timing instrumentation present
- [ ] Testing: integration tests cover core functionality
- [ ] Security: no auth tokens in logs or error messages
- [ ] Documentation: public APIs have docstrings

**Complexity Justification**: Violations of simplicity principles (e.g., adding abstraction layers beyond BaseAgent, creating new frameworks) MUST be justified in PR description with: (1) problem solved, (2) simpler alternatives considered and rejected, (3) future maintenance cost acknowledged.

**Rationale**: Constitution prevents architecture drift as project evolves. Compliance checklist makes reviews objective and consistent. Complexity justification forces intentional design decisions and prevents over-engineering.

**Version**: 1.1.0 | **Ratified**: 2025-11-23 | **Last Amended**: 2025-11-23
