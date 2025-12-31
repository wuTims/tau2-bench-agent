# Research: GetEvaluationResults Tool Update

**Feature Branch**: `009-get-eval-tool`
**Date**: 2025-12-27
**Spec**: [spec.md](./spec.md)

## Dependencies

### Runtime Dependencies

| Package | Version | Purpose | Verified |
|---------|---------|---------|----------|
| pydantic | >=2.0.0 | Data validation, ISO 8601 datetime parsing | [x] Already installed |
| google-adk | >=0.4.0 | BaseTool, LlmAgent, types.FunctionDeclaration | [x] Already installed |
| loguru | >=0.7.3 | Structured logging | [x] Already installed |

### Development Dependencies

| Package | Version | Purpose | Verified |
|---------|---------|---------|----------|
| pytest | >=7.0.0 | Testing framework | [x] Already installed |
| pytest-asyncio | >=0.21.0 | Async test support | [x] Already installed |

### Version Constraints

| Constraint | Reason | Impact |
|------------|--------|--------|
| pydantic >=2.0.0 | datetime parsing uses v2 API (model_validate) | Already satisfied by project |
| Python >=3.10 | datetime.fromisoformat() supports timezone suffixes | Already satisfied by project |

## Decision Registry

### DEC-001: Use EvaluationStore as Data Source

**Decision**: Rewrite GetEvaluationResults to use `create_store()` and EvaluationStore API instead of tau2's DATA_DIR/simulations/.

**Pattern**:
```python
from tau2.store import create_store

store = create_store()
```

**Verify In**: `tau2_agent/tools/get_evaluation_results.py`

**Rationale**: EvaluationStore is the canonical storage for agent-created evaluations. It has structured metadata (domain, status, created_at, agent_endpoint) that simulations/ files lack. The spec explicitly states this is the target architecture.

**Alternatives Rejected**:
- Correlate simulations/ with EvaluationStore: UUID-based save_to paths in simulations/ cannot be correlated to our eval-{ts}-{hex} IDs
- Read from both sources: Adds complexity without benefit, EvaluationStore is source of truth

**Verification Points**:
- [ ] Tool imports create_store from tau2.store
- [ ] Tool does NOT import DATA_DIR from tau2.utils.utils
- [ ] Tool does NOT read from simulations/ directory

---

### DEC-002: Extend list_evaluations with Time-Based Filtering

**Decision**: Add `after` and `before` parameters to `EvaluationStore.list_evaluations()` for ISO 8601 timestamp filtering.

**Pattern**:
```python
def list_evaluations(
    self,
    *,
    domain: str | None = None,
    status: str | None = None,
    after: datetime | None = None,
    before: datetime | None = None,
    agent_endpoint: str | None = None,
    include_sessions: bool = True,
    limit: int = 100,
) -> list[EvaluationSummary]:
```

**Verify In**: `src/tau2/store/store.py`

**Rationale**: Time-based filtering is essential for queries like "show me evaluations from yesterday". The LLM converts natural language to ISO 8601 timestamps, tool filters by comparing created_at.

**Alternatives Rejected**:
- Natural language parsing in tool: LLM handles this better, tool should take structured input
- Offset-based filtering (last 24h): Less flexible than explicit timestamps

**Verification Points**:
- [ ] list_evaluations accepts `after: datetime | None` parameter
- [ ] list_evaluations accepts `before: datetime | None` parameter
- [ ] list_evaluations accepts `agent_endpoint: str | None` parameter
- [ ] Filtering compares against evaluation.created_at

---

### DEC-003: System Prompt Time Injection

**Decision**: Inject current UTC time into agent's system prompt to enable LLM-based natural language time interpretation.

**Pattern**:
```python
from datetime import datetime, timezone

current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
INSTRUCTION = f"""...
Current UTC time: {current_time}
...
"""
```

**Verify In**: `tau2_agent/agent.py`

**Rationale**: The LLM needs to know current time to interpret "yesterday" or "last week". Injecting into system prompt is simpler than adding a tool and follows the spec's design principle.

**Alternatives Rejected**:
- Separate "get current time" tool: Adds unnecessary tool call overhead
- Let tool parse natural language: Tools should be deterministic, LLM handles interpretation

**Verification Points**:
- [ ] INSTRUCTION includes "Current UTC time:" with ISO 8601 timestamp
- [ ] Timestamp is generated at module load time using datetime.now(timezone.utc)
- [ ] System prompt mentions using get_evaluation_results with ISO timestamps

---

### DEC-004: ISO 8601 Timestamp Parsing

**Decision**: Use Python's datetime.fromisoformat() for parsing ISO 8601 timestamps from tool arguments.

**Pattern**:
```python
from datetime import datetime

after = datetime.fromisoformat(args["after"]) if args.get("after") else None
before = datetime.fromisoformat(args["before"]) if args.get("before") else None
```

**Verify In**: `tau2_agent/tools/get_evaluation_results.py`

**Rationale**: Python 3.10+ datetime.fromisoformat() handles timezone-aware ISO 8601 strings including Z suffix. No additional libraries needed.

**Alternatives Rejected**:
- dateutil.parser.parse(): External dependency not needed
- Manual regex parsing: More error-prone, less maintainable

**Verification Points**:
- [ ] Tool parses `after` and `before` args using datetime.fromisoformat()
- [ ] Invalid timestamp format returns descriptive error message
- [ ] Tool handles both naive and timezone-aware timestamps

---

### DEC-005: EvaluationSummary Extension for Results

**Decision**: Extend `EvaluationSummary` model to include agent_endpoint and optional summary metrics for list responses.

**Pattern**:
```python
class EvaluationSummary(BaseModel):
    evaluation_id: str
    trace_id: str | None = None
    session_id: str | None = None
    status: EvaluationStatus
    domain: str
    agent_endpoint: str | None = None  # NEW
    created_at: datetime
    completed_at: datetime | None = None  # NEW
    progress: int | None = None
    summary: dict | None = None  # NEW: {success_rate, total_tasks, successful}
```

**Verify In**: `src/tau2/store/models.py`

**Rationale**: List responses need agent_endpoint for filtering display, completed_at for duration info, and summary metrics for quick evaluation overview without loading full simulation data.

**Alternatives Rejected**:
- Return full Evaluation objects: Too much data for list view
- Separate summary endpoint: Over-engineering for MVP

**Verification Points**:
- [ ] EvaluationSummary includes agent_endpoint field
- [ ] EvaluationSummary includes completed_at field
- [ ] EvaluationSummary includes optional summary dict for completed evaluations

---

### DEC-006: Tool Response Format Alignment

**Decision**: Update GetEvaluationResults response format to match spec, including filters_applied metadata.

**Pattern**:
```python
# List response
{
    "evaluations": [...],
    "total_count": 5,
    "filters_applied": {
        "domain": "airline",
        "after": "2024-01-14T00:00:00Z"
    }
}

# Single evaluation response
{
    "evaluation_id": "eval-...",
    "domain": "airline",
    ...
}
```

**Verify In**: `tau2_agent/tools/get_evaluation_results.py`

**Rationale**: Response format matches spec exactly, providing consistent interface for LLM to interpret.

**Alternatives Rejected**:
- Reuse old response format: Old format used tau2 Results.load() structure, incompatible with EvaluationStore

**Verification Points**:
- [ ] List response includes `total_count` field
- [ ] List response includes `filters_applied` object
- [ ] Single evaluation response includes `state_history` when available

---

## Integration Notes

### Dependency Interactions

| Dependency A | Dependency B | Interaction | Notes |
|--------------|--------------|-------------|-------|
| pydantic | datetime | ISO 8601 serialization | Use model_dump(mode="json") for Z-suffix timestamps |
| google-adk | EvaluationStore | Tool uses store API | create_store() at tool invocation, not module load |

### Decision Dependencies

| Decision | Depends On | Reason |
|----------|------------|--------|
| DEC-006 | DEC-001 | Response format depends on using EvaluationStore data structure |
| DEC-006 | DEC-005 | Response format uses extended EvaluationSummary |
| DEC-003 | DEC-004 | System prompt enables LLM to generate ISO timestamps for tool |

## Open Questions

| Question | Status | Resolution |
|----------|--------|------------|
| Should include_simulations default to false? | RESOLVED | Yes, per spec - only load full simulation data when explicitly requested |
| Should include_sessions default to true? | RESOLVED | Yes, per spec clarification - show both in-progress and completed by default |

## Research Complete

- [x] All NEEDS CLARIFICATION items resolved (none identified)
- [x] All dependencies verified compatible (using existing project dependencies)
- [x] All decisions have verification points
- [x] No open blocking questions
- [x] Ready for /speckit.tasks to generate research-compliance.md
