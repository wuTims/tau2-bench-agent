# Tasks: Bidirectional A2A Protocol Integration

**Input**: Design documents from `/specs/001-a2a-integration/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Integration tests are included per SC-003 requirement (5-10 automated tests)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3B)
- Include exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and dependency setup

- [X] T001 Add A2A dependencies to pyproject.toml (httpx>=0.28.0, a2a-sdk[http-server]>=0.3.12, google-adk[a2a])
- [X] T002 [P] Create directory structure src/tau2/a2a/ for A2A client implementation
- [X] T003 [P] Create directory structure tau2_agent/ for ADK server implementation
- [X] T004 [P] Create test directories tests/test_a2a_client/, tests/test_adk_server/, tests/test_a2a_e2e/
- [X] T005 Install dependencies and verify imports (httpx, a2a-sdk, google-adk)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core data models and utilities that ALL user stories depend on

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 [P] Create A2A data models in src/tau2/a2a/models.py (A2AConfig, A2AMessage, MessagePart, AgentCard per data-model.md)
- [X] T007 [P] Create protocol metrics model in src/tau2/a2a/metrics.py (ProtocolMetrics entity per data-model.md)
- [X] T008 [P] Create A2A exception types in src/tau2/a2a/exceptions.py (A2AError, A2ATimeoutError, A2AAuthError)
- [X] T009 Create message translation utilities in src/tau2/a2a/translation.py (tau2_to_a2a, a2a_to_tau2 functions)
- [X] T010 Create tool descriptor formatting in src/tau2/a2a/translation.py (format_tools_as_text function)

**Checkpoint**: Foundation ready - user story implementation can now begin in parallel

---

## Phase 3: User Story 1 - Benchmark A2A-Compliant Agent (Priority: P1) 🎯 MVP Core

**Goal**: Enable tau2-bench to evaluate remote A2A-compliant agents via CLI, supporting agent discovery, message protocol, tool calling, and session management

**Independent Test**: Run a single benchmark task against a mock A2A agent endpoint and verify correct message exchange, tool execution, and evaluation results

### Tests for User Story 1

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [X] T011 [P] [US1] Create mock A2A agent test fixture in tests/test_a2a_client/conftest.py using httpx.MockTransport
- [X] T012 [P] [US1] Integration test for agent discovery in tests/test_a2a_client/test_agent_discovery.py
- [X] T013 [P] [US1] Integration test for message translation in tests/test_a2a_client/test_message_translation.py
- [X] T014 [P] [US1] Integration test for A2A agent execution in tests/test_a2a_client/test_a2a_agent.py

### Implementation for User Story 1

- [X] T015 [US1] Implement A2A HTTP client in src/tau2/a2a/client.py (discover_agent, send_message methods)
- [X] T016 [US1] Implement A2AAgent class extending LocalAgent in src/tau2/agent/a2a_agent.py (BaseAgent interface compliance)
- [X] T017 [US1] Implement generate_next_message method in A2AAgent (message translation, HTTP request, response parsing)
- [X] T018 [US1] Implement get_init_state method in A2AAgent (returns AgentState with empty message_history)
- [X] T019 [US1] Implement context_id persistence in A2AAgent (session management across turns)
- [X] T020 [US1] Add A2AAgent registration in src/tau2/registry.py (register as "a2a_agent")
- [X] T021 [US1] Add CLI arguments in src/tau2/cli.py (--agent-a2a-endpoint, --agent-a2a-auth-token, --agent-a2a-timeout)
- [X] T022 [US1] Add error handling for network failures, timeouts, auth errors in src/tau2/a2a/client.py

**Checkpoint**: At this point, User Story 1 should be fully functional - can run `tau2 run airline --agent a2a_agent --agent-a2a-endpoint <url>` successfully

---

## Phase 4: User Story 3B - Expose tau2-bench as A2A Evaluation Service (Priority: P1)

**Goal**: Enable external A2A clients to request tau2-bench evaluations programmatically via ADK-based agent exposing RunTau2Evaluation, ListDomains, and GetEvaluationResults tools

**Independent Test**: Deploy ADK agent, send A2A message requesting evaluation, verify evaluation runs and results are returned via A2A response

**Dependency**: Requires User Story 1 (A2A client) because ADK agent uses tau2's A2A client to evaluate A2A target agents

### Tests for User Story 3B

- [~] T023 [P] [US3B] Integration test for agent card serving in tests/test_adk_server/test_agent_card.py (Partial - requires ADK A2A config)
- [X] T024 [P] [US3B] Integration test for ADK tools in tests/test_adk_server/test_tools.py (RunTau2Evaluation, ListDomains)
- [X] T025 [P] [US3B] Integration test for A2A message/send endpoint in tests/test_adk_server/test_a2a_endpoint.py

### Implementation for User Story 3B

- [X] T026 [P] [US3B] Create RunTau2Evaluation tool in tau2_agent/tools/run_tau2_evaluation.py (BaseTool, uses tau2.run.run_domain)
- [X] T027 [P] [US3B] Create ListDomains tool in tau2_agent/tools/list_domains.py (BaseTool, returns available domains)
- [X] T028 [P] [US3B] Create GetEvaluationResults tool in tau2_agent/tools/get_evaluation_results.py (BaseTool, placeholder for Phase 2)
- [X] T029 [US3B] Create __init__.py in tau2_agent/tools/ exporting all tools
- [X] T030 [US3B] Create ADK agent definition in tau2_agent/agent.py (LlmAgent with tau2 evaluation tools, gemini-2.0-flash-exp)
- [X] T031 [US3B] Create tau2_agent/__init__.py importing agent module
- [X] T032 [US3B] Update RunTau2Evaluation to use correct tau2.data_model.simulation.RunConfig and Results structure
- [X] T033 [US3B] Add agent instruction prompt in tau2_agent/agent.py (evaluation service description)

**Checkpoint**: At this point, User Story 3B should work - can run `adk web --a2a tau2_agent/` and send A2A evaluation requests

---

## Phase 5: User Story 2 - Monitor Protocol-Specific Metrics (Priority: P2)

**Goal**: Track A2A protocol metrics (token usage, latency, message sizes) and export to structured JSON format for performance analysis

**Independent Test**: Run single task, capture protocol metrics, verify they are logged and exported in JSON format with correct token counts and latency measurements

### Tests for User Story 2

- [X] T034 [P] [US2] Unit test for metrics collection in tests/test_a2a_client/test_metrics.py
- [X] T035 [P] [US2] Integration test for metrics export in tests/test_a2a_client/test_metrics_export.py

### Implementation for User Story 2

- [X] T036 [P] [US2] Add metrics collection in src/tau2/a2a/client.py (create ProtocolMetrics per request)
- [X] T037 [P] [US2] Add token counting in src/tau2/a2a/metrics.py (estimate tokens for A2A messages)
- [X] T038 [US2] Add latency tracking in src/tau2/a2a/client.py (measure request/response time)
- [X] T039 [US2] Add structured logging for metrics in src/tau2/a2a/client.py (loguru with endpoint, status, timing, context_id)
- [X] T040 [US2] Add metrics aggregation in src/tau2/a2a/metrics.py (total_requests, avg_latency, total_tokens)
- [X] T041 [US2] Add metrics export to JSON in A2AAgent (integrate with tau2 results export)

**Checkpoint**: Metrics are captured and exported - verify metrics.json includes a2a_protocol_metrics section

---

## Phase 6: User Story 3 - Maintain Backward Compatibility (Priority: P1)

**Goal**: Ensure existing tau2-bench workflows (LLM agents, CLI, configurations) work unchanged after A2A integration

**Independent Test**: Run existing benchmark commands (e.g., `tau2 run airline --agent llm_agent --agent-llm claude-3-5-sonnet-20241022`) before and after A2A integration, verify identical behavior

### Tests for User Story 3

- [X] T042 [P] [US3] Integration test for LLM agent unchanged in tests/test_backward_compatibility/test_llm_agent.py
- [X] T043 [P] [US3] Integration test for CLI compatibility in tests/test_backward_compatibility/test_cli.py
- [X] T044 [P] [US3] Regression test suite comparing results before/after in tests/test_backward_compatibility/test_regression.py

### Implementation for User Story 3

- [X] T045 [US3] Verify no changes to existing agents (llm_agent.py, base.py should be unchanged)
- [X] T046 [US3] Verify CLI backward compatibility (existing flags work, new flags are optional)
- [X] T047 [US3] Verify registry pattern compatibility (A2AAgent registered alongside existing agents)
- [X] T048 [US3] Code review for any breaking changes (CRITICAL: must be zero breaking changes)

**Checkpoint**: All backward compatibility tests pass - existing workflows unaffected

---

## Phase 7: User Story 4 - Debug Agent Communication Sessions (Priority: P3)

**Goal**: Enable detailed logging of A2A message exchanges with structured metadata for debugging tool calling, context management, and response formatting issues

**Independent Test**: Run single task with debug logging enabled, verify all A2A messages (requests/responses), context IDs, and tool descriptions are captured in logs

### Tests for User Story 4

- [X] T049 [P] [US4] Integration test for debug logging in tests/test_a2a_client/test_debug_logging.py

### Implementation for User Story 4

- [X] T050 [P] [US4] Add debug logging for message payloads in src/tau2/a2a/client.py (full request/response logging)
- [X] T051 [P] [US4] Add debug logging for context_id lifecycle in A2AAgent (creation, reuse, session tracking)
- [X] T052 [US4] Add debug logging for tool descriptions in message translation (tools sent to agent)
- [X] T053 [US4] Add debug logging for protocol errors in src/tau2/a2a/client.py (malformed responses, parsing failures)
- [X] T054 [US4] Add CLI flag --a2a-debug for enabling verbose A2A logging

**Checkpoint**: Debug logging provides actionable information for troubleshooting A2A agent issues

---

## Phase 8: End-to-End Integration & Polish

**Purpose**: Validate complete bidirectional flow and finalize documentation

- [X] T055 [P] End-to-end test: External A2A client → ADK agent → tau2 → target A2A agent in tests/test_a2a_e2e/test_evaluation_flow.py::test_complete_a2a_loop
- [X] T056 [P] Update quickstart.md with actual CLI examples and verified output
- [X] T057 [P] Update README.md with A2A integration overview and quickstart link
- [X] T058 [P] Add docstrings to all public APIs (A2AAgent, A2AClient, tools) using Google-style format
- [X] T059 Validate quickstart.md examples work end-to-end
- [X] T060 Performance testing: measure <10% overhead vs baseline LLM agents (per plan.md performance goals)
- [X] T061 Security review: verify no auth tokens in logs, proper SSL verification
- [X] T062 Code cleanup: remove debug code, unused imports, add type hints where missing

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational - tau2 A2A Client (MVP core capability)
- **User Story 3B (Phase 4)**: Depends on Foundational AND User Story 1 - ADK server uses tau2 A2A client
- **User Story 2 (Phase 5)**: Depends on Foundational AND User Story 1 - metrics for A2A client
- **User Story 3 (Phase 6)**: Can run in parallel with other stories - mostly testing
- **User Story 4 (Phase 7)**: Depends on User Story 1 - debug logging enhancement
- **Polish (Phase 8)**: Depends on all user stories being complete

### Critical Path

```
Setup → Foundational → User Story 1 (A2A Client) → User Story 3B (ADK Server)
                                ↓
                         User Story 2 (Metrics)
                                ↓
                         User Story 4 (Debug)
                                ↓
                            Polish
```

### User Story Dependencies

- **User Story 1 (P1)**: Can start after Foundational - BLOCKING for User Story 3B
- **User Story 3B (P1)**: Can start after User Story 1 - uses A2A client to evaluate target agents
- **User Story 2 (P2)**: Can start after User Story 1 - adds metrics collection
- **User Story 3 (P1)**: Can start anytime - independent testing of backward compatibility
- **User Story 4 (P3)**: Can start after User Story 1 - adds debug logging

### Parallel Opportunities

- **Setup tasks (T002-T004)**: All [P] tasks can run in parallel (different directories)
- **Foundational tasks (T006-T008)**: All [P] tasks can run in parallel (different files)
- **US1 tests (T011-T014)**: All [P] tests can run in parallel
- **US3B tools (T026-T028)**: All [P] tool files can run in parallel
- **US2 tasks (T036-T037)**: Independent metrics tasks can run in parallel
- **US3 tests (T042-T044)**: All [P] tests can run in parallel
- **US4 tasks (T050-T051)**: Independent debug logging tasks can run in parallel
- **Polish tasks (T055-T058)**: Documentation and test tasks can run in parallel

---

## Parallel Example: User Story 1 Implementation

```bash
# After tests are written and failing, launch model implementations in parallel:
Task T011: "Create mock A2A agent test fixture in tests/test_a2a_client/conftest.py"
Task T012: "Integration test for agent discovery in tests/test_a2a_client/test_agent_discovery.py"
Task T013: "Integration test for message translation in tests/test_a2a_client/test_message_translation.py"
Task T014: "Integration test for A2A agent execution in tests/test_a2a_client/test_a2a_agent.py"

# Then implement core components (some can be parallel):
# T015 and T016 can be done in parallel (different files)
# T017-T019 are sequential (same file, A2AAgent methods)
# T020-T021 can be done in parallel (different files)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (T001-T005)
2. Complete Phase 2: Foundational (T006-T010) - CRITICAL
3. Complete Phase 3: User Story 1 (T011-T022)
4. **STOP and VALIDATE**: Test A2A client with mock agent
5. Demo: `tau2 run airline --agent a2a_agent --agent-a2a-endpoint <url>`

### Full P1 Delivery (MVP + ADK Server)

1. Complete MVP (Phases 1-3)
2. Complete Phase 4: User Story 3B (T023-T033)
3. **STOP and VALIDATE**: Test bidirectional flow
4. Demo: External agent → ADK → tau2 → A2A target agent

### Incremental Delivery

1. **Milestone 1**: Setup + Foundational → Foundation ready
2. **Milestone 2**: + User Story 1 → Test independently → Deploy/Demo (tau2 can evaluate A2A agents!)
3. **Milestone 3**: + User Story 3B → Test independently → Deploy/Demo (tau2 exposed as A2A service!)
4. **Milestone 4**: + User Story 2 → Add metrics → Deploy/Demo (performance visibility!)
5. **Milestone 5**: + User Story 3 → Validate backward compatibility (safety guaranteed!)
6. **Milestone 6**: + User Story 4 → Add debug logging → Deploy/Demo (developer experience!)
7. **Milestone 7**: Polish → Production ready

### Parallel Team Strategy

With multiple developers:

1. **Week 1**: Team completes Setup + Foundational together (T001-T010)
2. **Week 2-3**: Once Foundational is done:
   - Developer A: User Story 1 (T011-T022) - A2A Client
   - Developer B: User Story 3 (T042-T048) - Backward compatibility testing
   - Developer C: Setup ADK structure (prepare for User Story 3B)
3. **Week 4**:
   - Developer A: User Story 3B (T023-T033) - ADK Server (uses US1)
   - Developer B: User Story 2 (T034-T041) - Metrics (uses US1)
   - Developer C: User Story 4 (T049-T054) - Debug logging (uses US1)
4. **Week 5**: All developers: Polish (T055-T062)

---

## Notes

- [P] tasks = different files, no dependencies, can run in parallel
- [Story] label maps task to specific user story for traceability
- Each user story should be independently completable and testable
- Tests for US1 validate core A2A client functionality (discovery, translation, execution)
- Tests for US3B validate ADK server and A2A exposure
- Tests for US3 ensure zero breaking changes (CRITICAL)
- User Story 3B MUST wait for User Story 1 (ADK agent uses tau2 A2A client)
- Verify tests fail before implementing
- Commit after each task or logical group
- Stop at any checkpoint to validate story independently
- Avoid: breaking changes, tight coupling between stories, skipping backward compatibility validation

---

## Success Validation Checklist

Before marking feature complete, verify all success criteria from spec.md:

- [ ] **SC-001**: Can run `tau2 run airline --agent a2a_agent --agent-a2a-endpoint <url>` and receive evaluation results
- [ ] **SC-002**: Can run `tau2 run airline --agent llm_agent --agent-llm claude-3-5-sonnet-20241022` with identical results before/after
- [ ] **SC-003**: 5-10 automated integration tests pass (T011-T014, T023-T025, T034-T035, T042-T044, T055)
- [ ] **SC-004**: Protocol metrics captured in 100% of A2A requests (token count, latency, status in exported JSON)
- [ ] **SC-005**: Context IDs preserved across 100% of multi-turn conversations within a task
- [ ] **SC-006**: 0% of tool calls sent to remote agents; 100% execute locally in tau2-bench
- [ ] **SC-007**: Network failures, timeouts, auth errors, malformed responses all logged with diagnostic info
- [ ] **SC-008**: Round-trip translation tests pass (tau2 → A2A → tau2 preserves information content)
- [ ] **Performance**: <10% overhead vs baseline LLM agents (per plan.md)
- [ ] **ADK Server**: Can deploy `adk web --a2a tau2_agent/` and handle evaluation requests from external A2A clients
- [ ] **Agent Card**: `/.well-known/agent-card.json` accurately describes RunTau2Evaluation, ListDomains tools

---

## Task Count Summary

- **Phase 1 (Setup)**: 5 tasks
- **Phase 2 (Foundational)**: 5 tasks
- **Phase 3 (User Story 1 - P1)**: 12 tasks (4 tests + 8 implementation)
- **Phase 4 (User Story 3B - P1)**: 11 tasks (3 tests + 8 implementation)
- **Phase 5 (User Story 2 - P2)**: 8 tasks (2 tests + 6 implementation)
- **Phase 6 (User Story 3 - P1)**: 7 tasks (3 tests + 4 validation)
- **Phase 7 (User Story 4 - P3)**: 6 tasks (1 test + 5 implementation)
- **Phase 8 (Polish)**: 8 tasks

**Total**: 62 tasks

**Test tasks**: 13 integration/e2e tests (meets SC-003 requirement of 5-10 tests with room for depth)

**Parallelizable tasks**: 26 tasks marked [P] (42% of total)

**Critical path tasks**: Setup (5) → Foundational (5) → US1 core (8) → US3B core (8) → E2E (1) = 27 tasks

**MVP scope (recommended)**: Phase 1 + Phase 2 + Phase 3 = 22 tasks (User Story 1 only)
