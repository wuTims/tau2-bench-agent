# Feature Specification: GetEvaluationResults Tool Update

**Feature Branch**: `009-get-eval-tool`
**Created**: 2025-12-27
**Updated**: 2025-12-27
**Status**: Draft
**Depends On**: `002-evaluation-store`
**Depended On By**: None

**Input**: "Update GetEvaluationResults tool to retrieve evaluations from EvaluationStore with filtering and natural language time-based queries"

## Problem Statement

The current `GetEvaluationResults` tool has a critical disconnect:

1. **Wrong data source**: Reads from tau2's native `simulations/` directory instead of EvaluationStore
2. **No correlation**: Due to UUID-based `save_to` paths (`tau2_eval_{uuid}`), files in `simulations/` cannot be correlated to our structured evaluation IDs
3. **No filtering**: Cannot filter by domain, time range, agent endpoint, or status
4. **Poor human ergonomics**: A user asking "show me airline evaluations from yesterday" cannot be served

### Current Architecture (Broken)

```
run_tau2_evaluation                         get_evaluation_results
        │                                           │
        ▼                                           ▼
┌─────────────────────┐                ┌─────────────────────────┐
│   EvaluationStore   │                │  tau2 simulations/      │
│   evaluations/      │                │  (random UUIDs)         │
├─────────────────────┤                ├─────────────────────────┤
│ eval-{ts}-{hex}.json│                │ tau2_eval_{uuid}.json   │
│ ✅ Has metadata     │                │ ❌ No correlation       │
│ ✅ Has domain       │                │ ❌ No domain in name    │
│ ✅ Has timestamps   │                │ ❌ No timestamps        │
└─────────────────────┘                └─────────────────────────┘
        │                                           │
        │ NOT USED BY TOOL                          │ CURRENTLY USED
        └───────────────────────────────────────────┘
```

### Target Architecture

```
run_tau2_evaluation                         get_evaluation_results
        │                                           │
        ▼                                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                       EvaluationStore                            │
│                       evaluations/                               │
├─────────────────────────────────────────────────────────────────┤
│ eval-{ts}-{hex}.json                                            │
│ ✅ domain, agent_endpoint, created_at, status                   │
│ ✅ results.simulations (full message data)                      │
│ ✅ Filterable by time, domain, status                           │
└─────────────────────────────────────────────────────────────────┘
```

## Design Principles

1. **Tool takes structured input** - ISO 8601 timestamps, not natural language
2. **LLM handles interpretation** - Natural language → ISO timestamp conversion is the LLM's job
3. **System prompt provides context** - Current UTC time injected for time-based reasoning
4. **EvaluationStore is source of truth** - All queries go through the store API

## Architecture

### Time-Based Query Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│ Human: "Show me airline evaluations from yesterday"                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ System Prompt includes: "Current UTC time: 2024-01-15T14:30:00Z"        │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LLM (natural language understanding)                                    │
│ - Reads current time from system prompt                                 │
│ - Interprets "yesterday" → 2024-01-14T00:00:00Z to 2024-01-14T23:59:59Z │
│ - Converts to ISO 8601 timestamps                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Tool call:                                                              │
│ get_evaluation_results(                                                 │
│     list_available=true,                                                │
│     domain="airline",                                                   │
│     after="2024-01-14T00:00:00Z",                                       │
│     before="2024-01-15T00:00:00Z"                                       │
│ )                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ Tool returns structured data:                                           │
│ {                                                                       │
│   "evaluations": [...],                                                 │
│   "total_count": 2,                                                     │
│   "filters_applied": {"domain": "airline", "after": "..."}              │
│ }                                                                       │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ LLM generates response (we don't control phrasing):                     │
│ "Found 2 airline evaluations from yesterday:                            │
│  1. eval-1705233600000-a1b2c3 at 2:00 PM - 85% success rate             │
│  2. eval-1705248000000-d4e5f6 at 6:00 PM - 92% success rate"            │
└─────────────────────────────────────────────────────────────────────────┘
```

**Note**: The final response text is generated by the LLM based on tool output. We control the structured data returned by the tool, not how the LLM phrases it to the user.

## Core Components

### 1. Updated Tool Interface

Following the ADK tool pattern established in `list_domains.py` and `run_tau2_evaluation.py`:

```python
"""
GetEvaluationResults tool for ADK agent.

This tool enables external agents to retrieve completed evaluation results
from the EvaluationStore with filtering capabilities.
"""

from typing import Any

from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types

from tau2.store import create_store


class GetEvaluationResults(BaseTool):
    """Retrieve results from completed evaluations in EvaluationStore"""

    name = "get_evaluation_results"
    description = (
        "Get evaluation results from the store. "
        "Provide evaluation_id for a specific evaluation, or set list_available=true "
        "with optional filters (domain, status, after, before) to list evaluations."
    )

    def _get_declaration(self) -> types.FunctionDeclaration | None:
        """
        Create a FunctionDeclaration describing this tool for ADK integration.

        Returns:
            types.FunctionDeclaration | None: A FunctionDeclaration with the tool's
            name, description, and parameter schema.
        """
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "evaluation_id": types.Schema(
                        type=types.Type.STRING,
                        description="Specific evaluation ID (e.g., eval-1703697600000-a1b2c3)",
                    ),
                    "list_available": types.Schema(
                        type=types.Type.BOOLEAN,
                        description="List evaluations matching filters",
                    ),
                    "domain": types.Schema(
                        type=types.Type.STRING,
                        description="Filter by domain: airline, retail, telecom, mock",
                    ),
                    "status": types.Schema(
                        type=types.Type.STRING,
                        description="Filter by status: completed, failed, working",
                    ),
                    "after": types.Schema(
                        type=types.Type.STRING,
                        description="ISO 8601 timestamp - evaluations created after this time",
                    ),
                    "before": types.Schema(
                        type=types.Type.STRING,
                        description="ISO 8601 timestamp - evaluations created before this time",
                    ),
                    "agent_endpoint": types.Schema(
                        type=types.Type.STRING,
                        description="Filter by agent endpoint URL",
                    ),
                    "limit": types.Schema(
                        type=types.Type.INTEGER,
                        description="Max results (default 20, max 100)",
                    ),
                    "include_simulations": types.Schema(
                        type=types.Type.BOOLEAN,
                        description="Include full simulation data with messages (default false)",
                    ),
                    "include_sessions": types.Schema(
                        type=types.Type.BOOLEAN,
                        description="Include in-progress sessions in list results (default true)",
                    ),
                },
                required=[],
            ),
        )

    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext,  # noqa: ARG002
    ) -> Any:
        """
        Retrieve or list tau2 evaluation results from EvaluationStore.

        Parameters:
            args (dict): Input arguments. Recognized keys:
                - evaluation_id (str): Specific evaluation to retrieve.
                - list_available (bool): If true, list evaluations with filters.
                - domain (str): Filter by domain name.
                - status (str): Filter by evaluation status.
                - after (str): ISO 8601 timestamp, return evaluations after this.
                - before (str): ISO 8601 timestamp, return evaluations before this.
                - agent_endpoint (str): Filter by agent endpoint URL.
                - limit (int): Max results to return (default 20, max 100).
                - include_simulations (bool): Include full simulation data.
                - include_sessions (bool): Include in-progress sessions (default true).
            tool_context: ADK-provided execution context (unused).

        Returns:
            dict: List payload, single evaluation, or error (see Response Formats).
        """
        store = create_store()
        # Implementation: route to _get_single_evaluation or _list_evaluations
        ...
```

### 2. Response Formats

**List Response (`list_available=true`):**

```python
{
    "evaluations": [
        {
            "evaluation_id": "eval-1703697600000-a1b2c3",
            "domain": "airline",
            "agent_endpoint": "https://my-agent.example.com",
            "status": "completed",
            "created_at": "2024-01-15T14:30:00Z",
            "completed_at": "2024-01-15T14:35:00Z",
            "summary": {
                "success_rate": 0.85,
                "total_tasks": 10,
                "successful": 8
            }
        }
    ],
    "total_count": 1,
    "filters_applied": {
        "domain": "airline",
        "after": "2024-01-14T00:00:00Z"
    }
}
```

**Single Evaluation Response:**

```python
{
    "evaluation_id": "eval-1703697600000-a1b2c3",
    "domain": "airline",
    "agent_endpoint": "https://my-agent.example.com",
    "status": "completed",
    "created_at": "2024-01-15T14:30:00Z",
    "completed_at": "2024-01-15T14:35:00Z",
    "state_history": [
        {"state": "submitted", "at": "2024-01-15T14:30:00Z"},
        {"state": "working", "at": "2024-01-15T14:30:01Z", "progress": 0},
        {"state": "completed", "at": "2024-01-15T14:35:00Z"}
    ],
    "request": {
        "user_llm": "gpt-4o",
        "num_trials": 1,
        "num_tasks": 10
    },
    "results": {
        "success_rate": 0.85,
        "total_tasks": 10,
        "successful": 8,
        "tasks": [
            {"task_id": "task_001", "success": true, "reward": 0.95}
        ],
        # Only if include_simulations=true
        "simulations": [
            {
                "task_id": "task_001",
                "duration": 12.5,
                "termination_reason": "success",
                "messages": [...],
                "reward_info": {...}
            }
        ]
    }
}
```

### 3. EvaluationStore Enhancement

Extend `list_evaluations` to support time-based and agent filtering:

```python
# In store.py
def list_evaluations(
    self,
    *,
    domain: str | None = None,
    status: str | None = None,
    after: datetime | None = None,      # NEW
    before: datetime | None = None,     # NEW
    agent_endpoint: str | None = None,  # NEW
    include_sessions: bool = True,
    limit: int = 100,
) -> list[EvaluationSummary]:
```

### 4. System Prompt Time Injection

Inject current UTC time into the agent's system prompt:

```python
# In agent.py or server.py
from datetime import datetime, timezone

def get_system_instruction() -> str:
    current_time = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")

    return f"""You are tau2_agent, an evaluation service for conversational agents.

Current UTC time: {current_time}

When users ask for evaluations by relative time (e.g., "yesterday", "last week"),
convert to ISO 8601 timestamps for the get_evaluation_results tool.
...
"""
```

## Requirements

### Functional Requirements

| ID | Requirement | Priority |
|----|-------------|----------|
| FR-001 | Tool SHALL read from EvaluationStore, not tau2 simulations/ | P0 |
| FR-002 | Tool SHALL support filtering by domain | P0 |
| FR-003 | Tool SHALL support filtering by status (completed, failed, working) | P0 |
| FR-004 | Tool SHALL support filtering by time range (after, before) as ISO 8601 | P0 |
| FR-005 | Tool SHALL support filtering by agent_endpoint | P1 |
| FR-006 | Tool SHALL support pagination via limit parameter (default 20, max 100) | P1 |
| FR-007 | Tool SHALL optionally include full simulation data via include_simulations | P1 |
| FR-008 | List response SHALL include summary metrics (success_rate, total_tasks) | P0 |
| FR-009 | Single evaluation response SHALL include full state_history | P1 |
| FR-010 | System prompt SHALL include current UTC time for LLM time interpretation | P0 |

### Non-Functional Requirements

| ID | Requirement |
|----|-------------|
| NFR-001 | Response time < 500ms for list queries with limit <= 20 |
| NFR-002 | Full simulation data only loaded when include_simulations=true |
| NFR-003 | ISO 8601 parsing SHALL handle timezone-aware and naive timestamps |
| NFR-004 | Invalid filter values SHALL return descriptive error messages |

## Constraints

### No User Concept

The system currently has **no user identity or authentication context**. This means:

- Evaluations cannot be filtered by "who requested them"
- All evaluations are globally visible to anyone querying the store
- Queries like "show me *my* evaluations" are not possible

**Available filters are:**
- Time range (after/before)
- Domain (airline, retail, mock, telecom)
- Status (completed, failed, working)
- Agent endpoint (the agent that was evaluated)

**Not available:**
- User ID / requester identity
- API key correlation
- Session-based ownership

This is acceptable for the current use case (single-tenant service, internal tooling) but would need to be addressed for multi-tenant deployments.

## What We're NOT Building

- **User/tenant isolation** - No user concept exists in the system
- **Natural language time parsing in tool** - LLM handles this, tool takes ISO 8601
- **Current time tool** - System prompt injection is simpler and sufficient
- **Correlation with tau2 simulations/** - Clean break, EvaluationStore is source of truth
- **Backwards compatibility shim** - Old simulations/ files remain accessible via tau2 CLI

## Success Criteria

| ID | Criterion |
|----|-----------|
| SC-001 | `get_evaluation_results(list_available=true)` returns evaluations from EvaluationStore |
| SC-002 | Filtering by domain returns only matching evaluations |
| SC-003 | Filtering by time range (after/before) returns correctly bounded results |
| SC-004 | `get_evaluation_results(evaluation_id="eval-...")` returns full evaluation data |
| SC-005 | `include_simulations=true` includes full message history in response |
| SC-006 | LLM can interpret "yesterday" using system prompt time and call tool with ISO timestamps |
| SC-007 | Response format includes human-readable timestamps (ISO 8601 with Z suffix) |

## File Structure

```
tau2_agent/
├── tools/
│   └── get_evaluation_results.py   # REWRITE: Use EvaluationStore
├── agent.py                        # MODIFY: Inject current time in system prompt
└── ...

src/tau2/store/
├── store.py                        # MODIFY: Add after, before, agent_endpoint filters
└── ...

tests/
├── test_tau2_agent/
│   └── test_get_evaluation_results.py  # NEW: Comprehensive tests
└── test_store/
    └── test_store.py                   # MODIFY: Add filter tests
```

## Implementation Notes

1. **Rewrite** `get_evaluation_results.py` to use `create_store()` instead of tau2 DATA_DIR
2. **Extend** `EvaluationStore.list_evaluations()` with `after`, `before`, `agent_endpoint` params
3. **Modify** agent system prompt to include current UTC time
4. **Add** ISO 8601 parsing with timezone handling in store filtering
5. **Add** unit tests for new filtering capabilities
6. **Add** integration test for LLM time interpretation flow

## Migration

| Aspect | Old Behavior | New Behavior |
|--------|--------------|--------------|
| Data source | tau2 `simulations/` | EvaluationStore `evaluations/` |
| Available IDs | `tau2_eval_{uuid}` | `eval-{ts}-{hex}` |
| Metadata in list | None | domain, agent_endpoint, created_at, status |
| Time filtering | Not supported | ISO 8601 after/before |
| Domain filtering | Not supported | Supported |

**Note**: This is a breaking change for any code relying on the old simulations/ file format. The tau2 CLI can still access those files directly.

## Clarifications

### Session 2025-12-27

- Q: Should `list_available` include in-progress sessions or only completed evaluations? → A: Include both by default with `include_sessions` filter parameter
- Q: Should we support offset-based pagination for large result sets? → A: Defer, limit-only is sufficient for MVP

## Open Questions

1. ~~**Include sessions?**~~ - **RESOLVED**: Include both in-progress sessions and completed evaluations by default. Add `include_sessions` boolean parameter (default `true`) to allow filtering to completed-only when `include_sessions=false`.

2. ~~**Pagination offset?**~~ - **RESOLVED/DEFERRED**: Limit-only pagination is sufficient for MVP. Offset or cursor-based pagination can be added later if result sets grow large enough to require it.

## References

- [002-evaluation-store spec](../002-evaluation-store/spec.md) - EvaluationStore implementation
- [008-gcp-integration spec](../008-gcp-integration/spec.md) - tau2_agent deployment context
- [EvaluationStore models](../../src/tau2/store/models.py) - Data models
