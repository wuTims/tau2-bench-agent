# Implementation Plan: GetEvaluationResults Tool Update

**Branch**: `009-get-eval-tool` | **Date**: 2025-12-27 | **Spec**: [spec.md](./spec.md)
**Input**: Feature specification from `/specs/009-get-eval-tool/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command. See `.specify/templates/commands/plan.md` for the execution workflow.

## Summary

Update the `GetEvaluationResults` tool to read from `EvaluationStore` (our structured evaluation storage) instead of tau2's native `simulations/` directory. Add filtering by domain, status, time range (ISO 8601), and agent_endpoint. Inject current UTC time into the agent's system prompt to enable LLM-based natural language time interpretation.

## Technical Context

**Language/Version**: Python 3.10+ (per tau2-bench pyproject.toml requires-python)
**Primary Dependencies**: google-adk (BaseTool, LlmAgent), pydantic (data models), loguru (logging)
**Storage**: Filesystem JSON files in `$TAU2_DATA_DIR` (default `./data`) via EvaluationStore
**Testing**: pytest + pytest-asyncio (matches tau2 convention)
**Target Platform**: Linux server (GCP Cloud Run deployment context)
**Project Type**: single
**Performance Goals**: Response time < 500ms for list queries with limit <= 20 (NFR-001)
**Constraints**: Full simulation data only loaded when include_simulations=true (NFR-002)
**Scale/Scope**: Single-tenant service, typically <1000 evaluations

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### Pre-Design Gate Check

| Principle | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **I. A2A/ADK/tau2 Compliance** | Follow ADK tool patterns | ✅ PASS | Extends existing `BaseTool` pattern, uses `create_store()` |
| **II. Backward Compatibility** | No breaking changes | ✅ PASS | Internal tool rewrite, same tool name/interface for agent |
| **III. Metrics & Observability** | Token/time tracking | N/A | Tool doesn't invoke LLM, no new metrics needed |
| **IV. Testing Philosophy** | Pragmatic integration tests | ✅ PASS | Will add 3-5 integration tests for new filtering |
| **V. Code Quality** | Type hints, async patterns | ✅ PASS | Maintains existing patterns, adds ISO 8601 parsing |
| **VI. Architecture** | Separation of concerns | ✅ PASS | Tool uses store API, doesn't modify store internals |
| **VII. Documentation** | Docstrings for public APIs | ✅ PASS | Will update tool docstrings |

### Key Compliance Notes

1. **Backward Compatibility**: The tool interface changes (new parameters) but remains backward compatible:
   - `list_available=true` still works, returns from EvaluationStore instead of simulations/
   - `evaluation_id` parameter still works, retrieves from EvaluationStore
   - New optional parameters: `domain`, `status`, `after`, `before`, `agent_endpoint`, `limit`, `include_simulations`, `include_sessions`

2. **Breaking Change Acknowledgment**: This is a **data source migration** from tau2 `simulations/` to EvaluationStore `evaluations/`. Per spec, this is intentional and acceptable because:
   - Old simulations/ files remain accessible via tau2 CLI directly
   - EvaluationStore is the canonical storage for agent-created evaluations
   - No correlation was possible between old UUIDs and our evaluation IDs

3. **No New Dependencies**: Uses existing `pydantic` for datetime parsing (already installed)

## Project Structure

### Documentation (this feature)

```text
specs/009-get-eval-tool/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output (/speckit.plan command)
├── data-model.md        # Phase 1 output (/speckit.plan command)
├── quickstart.md        # Phase 1 output (/speckit.plan command)
├── contracts/           # Phase 1 output (/speckit.plan command)
└── tasks.md             # Phase 2 output (/speckit.tasks command - NOT created by /speckit.plan)
```

### Source Code (repository root)

```text
tau2_agent/
├── tools/
│   └── get_evaluation_results.py   # MODIFY: Rewrite to use EvaluationStore
├── agent.py                        # MODIFY: Inject current UTC time in system prompt
└── ...

src/tau2/store/
├── store.py                        # MODIFY: Add after, before, agent_endpoint filters
└── models.py                       # Reference: EvaluationSummary already has needed fields

tests/
├── test_tau2_agent/
│   └── test_get_evaluation_results.py  # NEW: Comprehensive tool tests
└── test_store/
    └── test_store.py                   # MODIFY: Add filter tests
```

**Structure Decision**: Single project structure. This feature modifies existing files in `tau2_agent/tools/` and `src/tau2/store/`, adding tests in `tests/`. No new modules required - extends existing EvaluationStore API and rewrites GetEvaluationResults tool implementation.

## Complexity Tracking

> **Fill ONLY if Constitution Check has violations that must be justified**

No constitution violations. All gates pass.

### Post-Design Gate Check

| Principle | Requirement | Status | Notes |
|-----------|-------------|--------|-------|
| **I. A2A/ADK/tau2 Compliance** | Follow ADK tool patterns | ✅ PASS | Tool contract uses BaseTool protocol, store extension uses existing patterns |
| **II. Backward Compatibility** | No breaking changes | ✅ PASS | Tool name unchanged, new params are optional, data source migration documented |
| **III. Metrics & Observability** | Token/time tracking | N/A | No LLM calls in tool |
| **IV. Testing Philosophy** | Pragmatic integration tests | ✅ PASS | Test plan includes 3-5 integration tests |
| **V. Code Quality** | Type hints, async patterns | ✅ PASS | TypedDict contracts, async run_async preserved |
| **VI. Architecture** | Separation of concerns | ✅ PASS | Tool → Store API → Filesystem, clean layering |
| **VII. Documentation** | Docstrings for public APIs | ✅ PASS | Quickstart with examples, contract file documented |

## Generated Artifacts

| Artifact | Path | Description |
|----------|------|-------------|
| Implementation Plan | `specs/009-get-eval-tool/plan.md` | This file |
| Research Document | `specs/009-get-eval-tool/research.md` | Dependencies and decisions |
| Data Model | `specs/009-get-eval-tool/data-model.md` | Input/output type definitions |
| Tool Contract | `specs/009-get-eval-tool/contracts/tool_interface.py` | TypedDict interface contract |
| Quickstart Guide | `specs/009-get-eval-tool/quickstart.md` | Usage examples |

## Next Steps

Run `/speckit.tasks` to generate `tasks.md` with implementation tasks based on this plan.
