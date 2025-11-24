# Phase 1: A2A Integration Layer

This phase implements core A2A protocol support within tau2-bench following constitution principles: backward compatibility, pragmatic testing, and metrics observability.

## 1.1 Create Feature Specification

**Command:** `/speckit.specify`

**Prompt:**
```
Create specification for Phase 1: A2A Integration Layer

CONTEXT:
- Extend tau2-bench (agent evaluation framework) to support A2A protocol agents
- A2A (Agent-to-Agent): protocol for agent communication over HTTP/gRPC
- Reference design: tau2-bench-adk-design.md sections 1.1-1.5
- Follow constitution principles: backward compatibility (Principle II), pragmatic testing (Principle IV), metrics & observability (Principle III)

REQUIREMENTS (see design doc for implementation details):

1. A2A Client (src/tau2/a2a/client.py) - Design section 1.1
   - Discover agents via /.well-known/agent-card.json endpoint
   - Send messages using A2A Message format (role, parts, context_id)
   - Handle authentication via bearer tokens, configurable timeouts (default 300s)
   - Persist context_id for session continuity
   - HTTP client lifecycle management (async context)

2. Message Translation (src/tau2/a2a/translation.py) - Design section 1.2
   - tau2_to_a2a: Convert tau2 messages → A2A Messages
   - a2a_to_tau2: Convert A2A Messages → tau2 AssistantMessage
   - Support both DataPart and embedded JSON tool calls (multi-strategy parsing)
   - Preserve tool names, arguments, message ordering
   - System messages → <system> tags in text

3. A2AAgent (src/tau2/a2a/agent.py) - Design section 1.3
   - Implement BaseAgent[AgentState] interface (generate_next_message, get_init_state, stop)
   - Wrap async A2A calls with asyncio.run for sync compatibility
   - Maintain A2AAgentState (messages, system_messages, context_id)
   - Build system prompt from domain policy

4. CLI Integration - Design section 1.4
   - Add CLI flags: --a2a-endpoint, --a2a-auth-token, --a2a-timeout
   - Instantiate A2AAgent when --agent a2a_agent specified
   - Register A2AAgent via registry pattern (src/tau2/registry.py)
   - Extend RunConfig (src/tau2/data_model/simulation.py)

5. Metrics & Observability (src/tau2/a2a/metrics.py) - Constitution Principle III
   - Track A2A protocol tokens (input/output per request)
   - Measure protocol latency (A2A request time vs LLM baseline)
   - Log protocol interactions with structured context (endpoint, status, timing)
   - Export metrics to JSON for analysis

CONSTRAINTS:
- Zero breaking changes to existing tau2-bench code (Constitution Principle II)
- Tools execute locally in tau2-bench, NOT on remote A2A agent
- Follow tau2 registry pattern for agent registration
- Use httpx for HTTP client (not requests)
- Use loguru for structured logging

SUCCESS CRITERIA:
- `tau2 run airline --agent a2a_agent --a2a-endpoint <url>` evaluates tasks
- Existing `tau2 run airline --agent llm_agent --agent-llm claude-3-5-sonnet-20241022` works unchanged
- 5-10 integration tests pass (Constitution Principle IV - pragmatic testing)
- Token tracking and latency metrics captured
```

**Validation Checkpoint:**
- Compare generated spec against design document sections 1.1-1.5
- Verify backward compatibility requirements explicit
- Ensure metrics & observability (Principle III) included

---

## 1.2 Clarify Ambiguities

**Command:** `/speckit.clarify`

**Prompt:**
```
Review Phase 1 specification and ask clarifying questions about:
1. A2A SDK API usage (exact class names, methods from a2a-sdk package)
2. Tool calling conventions (DataPart vs embedded JSON - which to prioritize?)
3. Error handling strategies (network failures, malformed responses)
4. Testing approach (mock A2A server implementation strategy)
5. Context ID persistence (when to create new vs reuse)
6. Metrics export format and integration points
```

**Human Interaction:**
- Answer clarifying questions based on design document
- Reference specific design sections (e.g., "See section 1.1 for A2AClient structure")
- Add notes about A2A SDK verification needs ("Verify exact API with a2a-sdk docs")

---

## 1.3 Create Technical Plan

**Command:** `/speckit.plan`

**Prompt:**
```
Create technical implementation plan for Phase 1: A2A Integration Layer

TECHNOLOGY STACK:
- Python 3.10+
- Dependencies: a2a-sdk[http-server]>=0.3.12, httpx>=0.28.0
- Existing tau2-bench architecture (orchestrator, registry, BaseAgent)

ARCHITECTURE DECISIONS:

1. Package: a2a-sdk vs custom implementation
   Decision: Use a2a-sdk for protocol compliance
   Rationale: Reduces maintenance burden, ensures spec compliance

2. HTTP Client: httpx vs requests
   Decision: httpx (async support)
   Rationale: Native async/await, better timeout handling

3. Sync/Async Boundary: Where to wrap async calls?
   Decision: asyncio.run() in A2AAgent.generate_next_message
   Rationale: Maintains BaseAgent sync interface, isolated async context

4. Tool Call Parsing: DataPart only vs multi-strategy
   Decision: Support both DataPart and embedded JSON
   Rationale: Robustness across A2A agent implementations

5. Module Location: utils vs separate a2a module
   Decision: src/tau2/a2a/ (Constitution Principle VI)
   Rationale: Separation of concerns, prevents A2A complexity polluting core

IMPLEMENTATION SEQUENCE:

1. Phase 1a: A2A Client (src/tau2/a2a/client.py)
   - A2AConfig dataclass
   - A2AClient with discover_agent, send_message, close
   - HTTP client lifecycle management
   - Bearer token authentication

2. Phase 1b: Message Translation (src/tau2/a2a/translation.py)
   - tau2_to_a2a: Build A2A Message from tau2 messages
   - a2a_to_tau2: Parse A2A response to AssistantMessage
   - Tool description formatting
   - Tool call extraction (DataPart + regex fallback)

3. Phase 1c: Metrics & Observability (src/tau2/a2a/metrics.py)
   - Token tracking for A2A protocol calls
   - Latency measurement (A2A request time)
   - Structured logging with loguru
   - Metrics export to JSON

4. Phase 1d: A2AAgent (src/tau2/a2a/agent.py)
   - A2AAgentState dataclass
   - A2AAgent class with BaseAgent interface
   - System prompt builder
   - Async wrapper methods
   - Metrics integration

5. Phase 1e: CLI Integration
   - Add arguments to src/tau2/cli.py
   - Modify src/tau2/run.py to instantiate A2AAgent
   - Update src/tau2/registry.py
   - Extend RunConfig in src/tau2/data_model/simulation.py

6. Phase 1f: Integration Testing
   - Mock A2A server fixture (pytest-httpx)
   - 5-10 integration tests covering core flows
   - Backward compatibility verification

FILE STRUCTURE:
```
src/tau2/
  a2a/                  # NEW MODULE (Constitution Principle VI)
    __init__.py         # NEW
    client.py           # NEW - A2AClient
    translation.py      # NEW - Message translation
    metrics.py          # NEW - Observability
    agent.py            # NEW - A2AAgent
  cli.py                # MODIFIED - Add A2A flags
  run.py                # MODIFIED - A2AAgent instantiation
  registry.py           # MODIFIED - Register A2AAgent
  data_model/
    simulation.py       # MODIFIED - Extend RunConfig

tests/
  a2a/                  # NEW
    test_a2a_integration.py  # NEW - 5-10 integration tests
    conftest.py         # NEW - Mock A2A server fixture
```

TESTING STRATEGY (Constitution Principle IV - Pragmatic Testing):
- 5-10 integration tests (NOT comprehensive unit tests)
- Mock A2A server using pytest-httpx
- Verify backward compatibility: existing tests pass unchanged
- NO coverage tooling (per constitution)
- Focus: verify components work together for core A2A flows

METRICS INSTRUMENTATION (Constitution Principle III):
- Token tracking: log input/output tokens for A2A protocol calls
- Latency measurement: A2A request time, tool execution time, overhead vs LLM baseline
- Structured logging: loguru with endpoint, status, timing context
- Export format: JSON with task_id, tokens, timing, overhead_pct

DEPENDENCIES (pyproject.toml):
```toml
[project.dependencies]
a2a-sdk = {version = ">=0.3.12", extras = ["http-server"]}
httpx = ">=0.28.0"
```

RISK MITIGATION:
- Risk: A2A SDK API mismatch
  Mitigation: Verify SDK docs before implementation, add abstraction layer
- Risk: Tool call parsing fragility
  Mitigation: Multi-strategy parsing, comprehensive test cases
- Risk: Async context management
  Mitigation: Use async context managers, thorough cleanup testing
```

**Validation Checkpoint:**
- Verify plan covers all design document components (sections 1.1-1.5)
- Check implementation sequence matches design roadmap
- Ensure testing strategy is pragmatic (5-10 tests, not exhaustive)
- Confirm metrics & observability included

---

## 1.4 Validate Plan

**Manual Review Process:**

1. **Design Alignment Check:**
   - Does plan implement all components from design sections 1.1-1.5?
   - Are class structures identical to design (A2AClient, A2AAgent)?
   - Are all design notes addressed (tool locality, sync wrappers)?

2. **Constitution Alignment Check:**
   - Backward compatibility (Principle II): Zero breaking changes?
   - Metrics & observability (Principle III): Token tracking and latency measurement?
   - Testing philosophy (Principle IV): 5-10 integration tests, NO coverage gates?
   - Architecture (Principle VI): A2A code in separate module (src/tau2/a2a/)?
   - Documentation (Principle VII): Public APIs need Google-style docstrings?

3. **Completeness Check:**
   - All new/modified files listed?
   - Dependencies specified?
   - Integration test coverage adequate?

4. **Feasibility Check:**
   - Can a2a-sdk be verified before implementation?
   - Is asyncio.run pattern appropriate?
   - Are error handling strategies realistic?

---

## 1.5 Generate Tasks

**Command:** `/speckit.tasks`

**Prompt:**
```
Break down Phase 1 implementation into ~10-15 tasks aligned with integration testing approach.

TASK GRANULARITY:
- Each task = one component implementation + basic validation
- Dependencies should be explicit
- Each task should produce testable artifact
- Target: 2-4 hours per task

INTEGRATION-FIRST STRUCTURE:
1. Setup & Dependencies (1 task)
2. A2A Client (2-3 tasks: implement, integrate, validate)
3. Message Translation (2-3 tasks: implement, integrate, validate)
4. Metrics & Observability (1-2 tasks)
5. A2AAgent (2-3 tasks: implement, integrate, validate)
6. CLI Integration (1-2 tasks)
7. Integration Testing (2-3 tasks: mock server, core flows, backward compatibility)

NOT: 30+ micro-tasks with separate unit test tasks for each method.

Include specific file paths, key function signatures, and integration test scenarios.
```

**Expected Task Output Structure:**
```
1. Setup & Dependencies
   [ ] 1.1: Add a2a-sdk and httpx to pyproject.toml
   [ ] 1.2: Create src/tau2/a2a/ module structure with __init__.py

2. A2A Client Implementation (Phase 1a)
   [ ] 2.1: Implement A2AConfig and A2AClient (discover_agent, send_message, close)
   [ ] 2.2: Add authentication and timeout handling
   [ ] 2.3: Validate with basic integration test (mock server)

3. Message Translation (Phase 1b)
   [ ] 3.1: Implement tau2_to_a2a (SystemMessage, User/Assistant, tools)
   [ ] 3.2: Implement a2a_to_tau2 (TextPart, DataPart, tool call extraction)
   [ ] 3.3: Validate round-trip translation with integration test

4. Metrics & Observability (Phase 1c)
   [ ] 4.1: Implement token tracking and latency measurement
   [ ] 4.2: Add structured logging and metrics export

5. A2AAgent Implementation (Phase 1d)
   [ ] 5.1: Implement A2AAgentState and A2AAgent class
   [ ] 5.2: Implement BaseAgent methods (generate_next_message, get_init_state, stop)
   [ ] 5.3: Integrate metrics and validate with integration test

6. CLI Integration (Phase 1e)
   [ ] 6.1: Add CLI arguments and extend RunConfig
   [ ] 6.2: Add A2AAgent instantiation in run.py and register in registry.py
   [ ] 6.3: Validate CLI with integration test

7. Integration Testing (Phase 1f)
   [ ] 7.1: Create mock A2A server fixture (pytest-httpx)
   [ ] 7.2: Write 5-10 integration tests (discovery, message exchange, tool calling, E2E)
   [ ] 7.3: Verify backward compatibility (existing tests pass)
```

---

## 1.6 Analyze & Validate

**Command:** `/speckit.analyze`

**Prompt:**
```
Analyze Phase 1 specification, plan, and tasks for:
1. Consistency: Do tasks fully implement the plan? Does plan match spec?
2. Coverage: Are all design document requirements (sections 1.1-1.5) addressed?
3. Dependencies: Are task dependencies correctly ordered?
4. Testing: Are 5-10 integration tests planned (not exhaustive unit tests)?
5. Documentation: Are Google-style docstrings planned for public APIs?
6. Constitution Compliance:
   - Backward compatibility (Principle II): Zero breaking changes verified?
   - A2A compliance (Principle I): Message fidelity preserved?
   - Metrics (Principle III): Token tracking and latency measurement present?
   - Testing (Principle IV): 5-10 integration tests, NO coverage gates?
   - Architecture (Principle VI): A2A code in src/tau2/a2a/ module?
   - Security: Auth tokens not logged?
```

**Design Alignment Validation:**

Create traceability matrix:
```markdown
| Design Section | Spec Requirement | Plan Component | Task IDs |
|----------------|------------------|----------------|----------|
| 1.1 A2A Client | discover_agent method | Phase 1a | 2.1 |
| 1.1 A2A Client | send_message method | Phase 1a | 2.1 |
| 1.2 Message Translation | tau2_to_a2a | Phase 1b | 3.1 |
| 1.2 Message Translation | a2a_to_tau2 | Phase 1b | 3.2 |
| 1.3 A2AAgent | BaseAgent interface | Phase 1d | 5.1-5.2 |
| 1.4 CLI Integration | CLI arguments | Phase 1e | 6.1 |
| 1.5 RunConfig | New fields | Phase 1e | 6.1 |
| Metrics (Const. III) | Token tracking | Phase 1c | 4.1 |
```

**Constitution Compliance Checklist** (from Governance section):
```markdown
- [ ] Backward compatibility: existing tests pass without modification
- [ ] A2A compliance: message translation preserves semantics
- [ ] BaseAgent interface: required methods implemented
- [ ] Metrics: token usage and timing instrumentation present
- [ ] Testing: 5-10 integration tests (NOT exhaustive unit tests)
- [ ] Security: no auth tokens in logs or error messages
- [ ] Documentation: public APIs have Google-style docstrings
```

---

## 1.7 Implement Phase 1

**Command:** `/speckit.implement`

**Prompt:**
```
Implement all tasks for Phase 1: A2A Integration Layer

EXECUTION GUIDELINES:
1. Follow task order from /speckit.tasks output
2. Validate after each component with basic integration test
3. Commit after each logical unit (client, translation, agent, cli)
4. Reference design document code snippets when applicable

IMPLEMENTATION CHECKPOINTS:
After completing Phase 1a (A2A Client):
  - Validation: Can discover agent card from mock endpoint
  - Validation: Can send message and receive response

After completing Phase 1b (Message Translation):
  - Validation: Messages round-trip correctly (tau2 → A2A → tau2)
  - Validation: Tool descriptions formatted correctly

After completing Phase 1c (Metrics):
  - Validation: Token counts logged for A2A calls
  - Validation: Latency metrics captured

After completing Phase 1d (A2AAgent):
  - Validation: A2AAgent implements all BaseAgent methods
  - Validation: Agent can generate messages via A2A protocol

After completing Phase 1e (CLI Integration):
  - Validation: `tau2 run --help` shows new flags
  - Validation: CLI accepts A2A parameters

After completing Phase 1f (Testing):
  - Validation: 5-10 integration tests pass
  - Validation: Existing tests still pass (backward compatibility)

QUALITY GATES (Constitution-aligned):
- 5-10 integration tests pass (Constitution Principle IV)
- Existing tests pass (backward compatibility - Principle II)
- black formatting passes
- ruff linting passes (warnings acceptable)
- Manual verification: Both existing and new agent types work:
  - `tau2 run airline --agent llm_agent --agent-llm gpt-4o` (existing)
  - `tau2 run airline --agent a2a_agent --a2a-endpoint <mock>` (new)
```

**Post-Implementation Validation:**

Run comprehensive validation:
```bash
# Integration tests
pytest tests/a2a/test_a2a_integration.py -v

# Backward compatibility check
pytest tests/ -k "not a2a" -v

# Formatting
black src/tau2/a2a/ tests/a2a/

# Linting (warnings OK)
ruff check src/tau2/a2a/ tests/a2a/

# Manual verification with mock server
tau2 run airline --agent a2a_agent --a2a-endpoint http://localhost:8000 --max-steps 5
```

**Design Document Reconciliation:**

After implementation, update `tau2-bench-adk-design.md` with:
- Verified A2A SDK API usage (actual vs. assumed)
- Implementation deviations from design (with rationale)
- Lessons learned (edge cases, challenges)
- Metrics collected (token usage, latency measurements)

---

## Summary of Changes from Original Plan

**Testing Philosophy**: Replaced comprehensive unit tests + >90% coverage with 5-10 pragmatic integration tests per Constitution Principle IV.

**File Structure**: Changed `src/tau2/utils/` to `src/tau2/a2a/` per Constitution Principle VI (separation of concerns).

**Metrics & Observability**: Added explicit Phase 1c for metrics implementation per Constitution Principle III.

**Prompt Simplification**: Removed embedded code snippets, added design doc references for conciseness and agent autonomy during clarification.

**Constitution Compliance**: Added explicit compliance checklist in analyze step referencing Governance section.

**Quality Gates**: Removed strict requirements (mypy --strict, >90% coverage) in favor of pragmatic gates (black, ruff warnings OK, integration tests pass).
