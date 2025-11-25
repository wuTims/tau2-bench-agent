# Feature Specification: Bidirectional A2A Protocol Integration for tau2-bench

**Feature Branch**: `001-a2a-integration`
**Created**: 2025-11-23
**Last Updated**: 2025-11-24 (Added bidirectional A2A support)
**Status**: Draft

**Input**: "Create specification for Phase 1: A2A Integration Layer - Extend tau2-bench to support BIDIRECTIONAL A2A protocol: (1) tau2-bench can evaluate remote A2A agents, AND (2) tau2-bench exposes evaluation capabilities via A2A for other agents to request evaluations"

## Architecture Overview

This feature implements **bidirectional A2A integration** with two complementary capabilities:

### Capability 1: tau2 A2A Client (Evaluates Remote A2A Agents)
```
tau2-bench → A2AAgent → Remote A2A Agent (being evaluated)
```
Enables tau2-bench to directly evaluate A2A-compliant agents via CLI or Python API.

### Capability 2: tau2 A2A Server (Exposes Evaluations via A2A)
```
External A2A Client → ADK Agent → tau2 RunTau2Evaluation tool → tau2.run_domain()
                                                                        ↓
                                               (uses Capability 1 if target is A2A)
```
Enables other agents to request tau2-bench evaluations via A2A protocol.

**Key Insight**: Capability 2 depends on Capability 1, as the ADK server needs tau2's A2A client to evaluate A2A target agents.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Benchmark A2A-Compliant Agent (Priority: P1)

A benchmark researcher wants to evaluate an A2A-compliant agent against the tau2-bench test suite to measure its performance on customer service tasks across multiple domains (airline, retail, telecom).

**Why this priority**: This is the core value proposition - enabling tau2-bench to evaluate agents using the A2A protocol, which is currently unsupported. Without this, A2A agents cannot be benchmarked using tau2-bench's standardized task suite.

**Independent Test**: Can be fully tested by running a single benchmark task against a mock A2A agent endpoint and verifying that the agent receives task context, responds appropriately, and results are evaluated correctly. Delivers immediate value by proving A2A protocol compatibility.

**Acceptance Scenarios**:

1. **Given** a running A2A-compliant agent at a known endpoint, **When** the researcher runs the benchmark command with the agent endpoint, **Then** the benchmark discovers the agent, sends task instructions, collects responses, and produces evaluation results
2. **Given** benchmark tasks in the airline domain, **When** the A2A agent receives tool descriptions and user context, **Then** the agent responds with appropriate tool call requests that are executed locally and results are returned to the agent
3. **Given** a completed benchmark run, **When** the researcher reviews results, **Then** they see standard metrics (pass rates, tool call accuracy, communication scores) identical to those produced by native tau2-bench agents

---

### User Story 2 - Monitor Protocol-Specific Metrics (Priority: P2)

A benchmark researcher wants to track A2A protocol-specific metrics (token usage, latency overhead, message sizes) to understand the performance characteristics of evaluating agents over the network versus local execution.

**Why this priority**: Essential for production use and performance optimization, but the core evaluation functionality (P1) must work first. These metrics inform capacity planning and protocol efficiency analysis.

**Independent Test**: Can be tested independently by running a single task, capturing protocol metrics (request/response sizes, network latency, token counts), and verifying they are logged and exported in a structured format.

**Acceptance Scenarios**:

1. **Given** an A2A agent evaluation run, **When** protocol messages are exchanged, **Then** token counts for each request and response are captured and logged
2. **Given** network communication with the A2A agent, **When** each request is made, **Then** the time spent waiting for responses is measured and compared against baseline local execution time
3. **Given** a completed evaluation run, **When** the researcher exports metrics, **Then** protocol-specific data (tokens per task, average latency, message counts) is available in JSON format for analysis

---

### User Story 3 - Maintain Backward Compatibility (Priority: P1)

An existing tau2-bench user wants to continue evaluating local LLM-based agents without any changes to their workflow, even after A2A protocol support is added.

**Why this priority**: Critical for adoption - breaking existing workflows would prevent users from upgrading. This ensures the A2A integration is truly additive with zero disruption.

**Independent Test**: Run existing benchmark commands (e.g., `tau2 run airline --agent llm_agent --agent-llm claude-3-5-sonnet-20241022`) before and after the A2A integration and verify identical behavior, output format, and results.

**Acceptance Scenarios**:

1. **Given** an existing benchmark command for an LLM agent, **When** the command is executed after A2A integration, **Then** the agent runs successfully with identical output and no new required parameters
2. **Given** existing configuration files and scripts, **When** users run benchmarks, **Then** no code changes or configuration updates are required
3. **Given** the tau2-bench codebase, **When** A2A support is added, **Then** no existing modules, classes, or functions are modified in ways that change their behavior for non-A2A use cases

---

### User Story 3B - Expose tau2-bench as A2A Evaluation Service (Priority: P1)

An AI research lab wants to integrate tau2-bench evaluations into their multi-agent workflow, where agents can request benchmark evaluations of other agents programmatically via A2A protocol without manual CLI intervention.

**Why this priority**: Enables tau2-bench to be part of automated agent ecosystems, allowing agents to self-evaluate or evaluate peers as part of continuous improvement pipelines. This is foundational for agent-driven development workflows.

**Independent Test**: Can be fully tested by deploying the ADK agent, sending an A2A message requesting an evaluation, and verifying that the agent receives evaluation results via A2A response. Validates the full server-side A2A integration.

**Acceptance Scenarios**:

1. **Given** a deployed ADK agent exposing tau2-bench tools, **When** an external A2A client sends a message requesting evaluation of an agent at a specific endpoint, **Then** the ADK agent validates the request, triggers tau2-bench evaluation, and returns results via A2A response
2. **Given** an evaluation request for an A2A-compliant target agent, **When** the ADK agent processes the request, **Then** tau2-bench uses its A2A client (Capability 1) to communicate with the target agent and successfully completes the evaluation
3. **Given** multiple concurrent evaluation requests from different A2A clients, **When** the ADK agent processes them, **Then** each evaluation runs in isolation with separate sessions and no state leakage between evaluations
4. **Given** an agent discovery request to the ADK agent, **When** an A2A client fetches `/.well-known/agent-card.json`, **Then** the agent card accurately describes available tau2-bench evaluation tools and their parameters

---

### User Story 4 - Debug Agent Communication Sessions (Priority: P3)

An agent developer wants to inspect message exchanges between tau2-bench and their A2A agent to debug issues with tool calling, context management, or response formatting.

**Why this priority**: Important for developer experience but not blocking core functionality. Developers can initially work around missing detailed logging by instrumenting their own agents.

**Independent Test**: Run a single task with debug logging enabled, then inspect logs to verify all A2A messages (requests and responses), context IDs, tool descriptions, and response parsing are captured with structured metadata.

**Acceptance Scenarios**:

1. **Given** a benchmark run with debug logging enabled, **When** messages are exchanged with the A2A agent, **Then** each request shows the full message payload including tool descriptions and conversation history
2. **Given** protocol errors or parsing failures, **When** the agent returns malformed responses, **Then** errors are logged with context about what was expected versus received
3. **Given** session continuity requirements, **When** context IDs are assigned and persisted, **Then** logs show context ID creation and reuse across message exchanges

---

### Edge Cases

- What happens when the A2A agent endpoint is unreachable or returns HTTP errors?
- How does the system handle agents that return responses in unexpected formats (missing required fields, malformed JSON)?
- What happens when the A2A agent takes longer than the configured timeout to respond?
- How does the system handle authentication failures with bearer tokens?
- What happens when an agent's response includes tool calls for tools that don't exist in the current domain?
- How does session state (context_id) behave when an evaluation spans multiple tasks?
- What happens when the agent discovery endpoint (/.well-known/agent-card.json) is missing or returns invalid data?

## Requirements *(mandatory)*

### Functional Requirements

#### Agent Discovery & Communication

- **FR-001**: System MUST discover A2A agent capabilities by fetching the agent card from the `/.well-known/agent-card.json` endpoint before beginning evaluation
- **FR-002**: System MUST communicate with A2A agents using HTTP-based message protocol with configurable endpoint URLs
- **FR-003**: System MUST support bearer token authentication for agents that require authorization
- **FR-004**: System MUST respect configurable timeout values (default 300 seconds) for agent responses
- **FR-005**: System MUST maintain HTTP client sessions across multiple requests to the same agent endpoint

#### Message Translation & Tool Handling

- **FR-006**: System MUST convert tau2-bench internal messages (user messages, tool results, system instructions) to A2A Message format with appropriate roles and content parts
- **FR-007**: System MUST convert A2A agent responses back to tau2-bench AssistantMessage format preserving content and tool calls
- **FR-008**: System MUST include tool descriptions as text content in messages sent to A2A agents (not as executable code)
- **FR-009**: System MUST parse tool call requests from A2A responses supporting both structured data parts and embedded JSON formats
- **FR-010**: System MUST execute requested tool calls locally within tau2-bench environment (not on the remote agent)
- **FR-011**: System MUST prepend system-level instructions to message content using structured tags to distinguish them from user content

#### Session & Context Management

- **FR-012**: System MUST persist context identifiers received from A2A agents across message exchanges within the same task evaluation
- **FR-013**: System MUST include the context identifier in subsequent messages to maintain session continuity
- **FR-014**: System MUST maintain separate conversation history for each task evaluation (no state leakage between tasks)
- **FR-015**: System MUST build system prompts from domain-specific policies provided by tau2-bench task configurations

#### CLI & Configuration

- **FR-016**: Users MUST be able to specify A2A agent endpoints via command-line flags
- **FR-017**: Users MUST be able to provide authentication tokens via command-line flags
- **FR-018**: Users MUST be able to configure request timeouts via command-line flags with sensible defaults
- **FR-019**: System MUST register A2A agent type using tau2-bench's standard agent registry pattern
- **FR-020**: System MUST extend run configuration to store A2A-specific parameters without breaking existing configurations

#### Metrics & Observability

- **FR-021**: System MUST track token counts for each A2A protocol request (input tokens) and response (output tokens)
- **FR-022**: System MUST measure time spent in A2A protocol communication separate from local processing time
- **FR-023**: System MUST log protocol interactions with structured metadata including endpoint, HTTP status, timing, and context IDs
- **FR-024**: System MUST export A2A-specific metrics to JSON format for post-run analysis
- **FR-025**: System MUST capture protocol-level errors (connection failures, timeouts, authentication failures) separately from agent reasoning errors

#### ADK Server & A2A Service Exposure

- **FR-029**: System MUST provide ADK-based agent that exposes tau2-bench evaluation capabilities via A2A protocol
- **FR-030**: ADK agent MUST serve agent card at `/.well-known/agent-card.json` describing available tau2 evaluation tools
- **FR-031**: ADK agent MUST implement `RunTau2Evaluation` tool accepting domain, agent endpoint, user LLM, and trial parameters
- **FR-032**: ADK agent MUST implement `ListDomains` tool returning available tau2-bench evaluation domains
- **FR-033**: ADK agent MUST handle A2A message/send requests and translate them to ADK tool invocations
- **FR-034**: ADK agent MUST map A2A context_id to ADK session_id for conversation state management
- **FR-035**: ADK agent MUST return evaluation results in A2A message format with proper success/error handling
- **FR-036**: ADK server MUST support deployment via `adk web --a2a` command for local development and production
- **FR-037**: ADK tools MUST internally use tau2's A2A client (Capability 1) when evaluating A2A target agents
- **FR-038**: ADK agent MUST isolate concurrent evaluation requests with separate sessions (no shared state)

#### Backward Compatibility

- **FR-039**: System MUST preserve all existing tau2-bench functionality for non-A2A agents without modification
- **FR-040**: System MUST not require any changes to existing benchmark task definitions, domain configurations, or evaluation logic
- **FR-041**: System MUST maintain identical command-line interfaces and output formats for existing agent types

### Key Entities *(include if feature involves data)*

- **A2AConfig**: Configuration bundle containing agent endpoint URL, optional authentication token, and timeout settings
- **A2AMessage**: Protocol message with unique identifier, role (user/agent), content parts (text/data/file), and optional context identifier
- **A2AAgentState**: Agent execution state containing conversation history, system messages, and session context identifier
- **AgentCard**: Discovery metadata describing agent capabilities, authentication requirements, and transport protocol details
- **ProtocolMetrics**: Performance measurements including token counts (input/output), request latency, message sizes, and HTTP status codes
- **MessagePart**: Content component of A2A messages - can be text (human-readable content), data (structured JSON), or file (resource reference)
- **ToolDescriptor**: Text representation of available tools sent to A2A agents, including tool name, parameter types, and usage description

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Benchmark command successfully evaluates A2A agents end-to-end - user can run `tau2 run airline --agent a2a_agent --a2a-endpoint <url>` and receive evaluation results
- **SC-002**: Existing benchmark workflows continue working unchanged - `tau2 run airline --agent llm_agent --agent-llm claude-3-5-sonnet-20241022` produces identical results before and after A2A integration
- **SC-003**: Integration test suite validates correctness - 5-10 automated tests pass covering agent discovery, message translation, tool calling, error handling, and metrics collection
- **SC-004**: Protocol metrics are captured completely - 100% of A2A requests include token count, latency, and status measurements in exported JSON
- **SC-005**: Session continuity is maintained - context identifiers are preserved across 100% of multi-turn conversations within a single task
- **SC-006**: Tool execution locality is enforced - 0% of tool calls are sent to remote A2A agents; 100% execute within tau2-bench's local environment
- **SC-007**: Error handling is comprehensive - network failures, timeouts, authentication errors, and malformed responses are all logged with actionable diagnostic information
- **SC-008**: Message translation is lossless - information content is preserved when converting between tau2-bench and A2A formats (validated by round-trip tests)

## Assumptions

- **AS-001**: A2A agents comply with the standard A2A protocol specification (message structure, agent card format, transport layer)
- **AS-002**: Tool calling conventions can vary by agent implementation; the system assumes either structured DataPart JSON or embedded JSON in text responses
- **AS-003**: Network connectivity to A2A agent endpoints is reliable during evaluation runs (transient failures are handled gracefully but persistent network issues are out of scope)
- **AS-004**: A2A agents return tool call requests but do not execute tools themselves - tool execution is always local to tau2-bench
- **AS-005**: The httpx library provides sufficient HTTP client functionality for A2A protocol communication
- **AS-006**: Loguru structured logging provides adequate observability for protocol debugging and performance analysis
- **AS-007**: Context identifiers are server-generated by A2A agents on first response and remain stable for the duration of a task evaluation
- **AS-008**: Benchmark tasks do not need to be modified to support A2A agents - existing task definitions work with protocol translation layer
- **AS-009**: Token counting for A2A protocol messages can be performed using standard tokenization methods (same as used for LLM agents)
- **AS-010**: Evaluation metrics (pass rates, tool accuracy, communication scores) are protocol-agnostic and apply equally to A2A and native agents

## Dependencies

- **DEP-001**: Python httpx library (>=0.28.0) for async HTTP client functionality
- **DEP-002**: Python a2a-sdk library with http-server extras (>=0.3.12) for A2A protocol implementation
- **DEP-003**: Python loguru library (already in tau2-bench) for structured logging
- **DEP-004**: tau2-bench BaseAgent interface and orchestrator (existing code, no changes required)
- **DEP-005**: tau2-bench registry system for agent registration (existing code, extension point)
- **DEP-006**: Access to A2A-compliant agent endpoints for testing and validation
- **DEP-007**: tau2-bench message and tool data models (existing code, no changes required)
- **DEP-008**: Google ADK Python library (google-adk) with A2A extras for server implementation
- **DEP-009**: ADK's FastAPI integration for HTTP server and A2A endpoint handling
- **DEP-010**: ADK's session management (SessionService) for context_id ↔ session_id mapping
- **DEP-011**: ADK's tool framework (BaseTool) for exposing tau2 evaluation functions

## Constraints

- **CON-001**: Zero breaking changes to tau2-bench core - all changes must be additive and backward-compatible
- **CON-002**: Tool execution must remain local to tau2-bench - remote A2A agents only provide reasoning and tool call decisions
- **CON-003**: Implementation must follow tau2-bench's existing registry pattern for agent types
- **CON-004**: HTTP transport only (gRPC support for A2A protocol is out of scope for Phase 1)
- **CON-005**: Synchronous execution model - must wrap async A2A calls to maintain compatibility with tau2-bench's synchronous orchestrator
- **CON-006**: Use httpx for HTTP client (not requests library) to enable future async optimizations
- **CON-007**: Use loguru for logging (not standard Python logging) to maintain consistency with tau2-bench's existing logging infrastructure
- **CON-008**: A2A agent state must be isolated per task evaluation - no shared state between concurrent evaluations
- **CON-009**: Configuration must extend existing RunConfig Pydantic model without breaking deserialization of existing configs
- **CON-010**: Metrics must be JSON-serializable and compatible with tau2-bench's existing metrics export formats

## Out of Scope

- **OOS-001**: gRPC transport support for A2A protocol (Phase 1 focuses on HTTP/JSON-RPC)
- **OOS-002**: MCP (Model Context Protocol) integration for tool definitions
- **OOS-003**: Advanced A2A features like file parts, streaming responses, or multi-agent coordination
- **OOS-004**: Automated conversion of existing LLM agents to A2A protocol
- **OOS-005**: A2A agent hosting, deployment, or lifecycle management
- **OOS-006**: Rate limiting or quota management for A2A endpoint requests
- **OOS-007**: Caching of A2A agent responses for repeated evaluations
- **OOS-008**: Custom A2A protocol extensions or vendor-specific features
- **OOS-009**: Performance optimization beyond baseline synchronous execution (async parallelization is Phase 2+)
- **OOS-010**: UI or dashboard for monitoring A2A protocol metrics in real-time

## Open Questions

*None - all requirements are sufficiently specified for implementation planning.*
