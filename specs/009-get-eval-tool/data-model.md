# Data Model: GetEvaluationResults Tool Update

**Feature Branch**: `009-get-eval-tool`
**Date**: 2025-12-27
**Spec**: [spec.md](./spec.md)

## Entities

### 1. Tool Parameters (Input)

```python
class GetEvaluationResultsParams:
    """Input parameters for the GetEvaluationResults tool."""

    # Single evaluation retrieval
    evaluation_id: str | None  # e.g., "eval-1703697600000-a1b2c3"

    # List mode
    list_available: bool = False  # Trigger list mode

    # Filters (only used when list_available=true)
    domain: str | None  # "airline", "retail", "telecom", "mock"
    status: str | None  # "completed", "failed", "working", "submitted"
    after: str | None   # ISO 8601 timestamp, e.g., "2024-01-14T00:00:00Z"
    before: str | None  # ISO 8601 timestamp, e.g., "2024-01-15T00:00:00Z"
    agent_endpoint: str | None  # e.g., "https://my-agent.example.com"

    # Response control
    limit: int = 20  # Max results (max 100)
    include_simulations: bool = False  # Include full simulation data
    include_sessions: bool = True  # Include in-progress sessions
```

### 2. List Response (Output)

```python
class ListEvaluationsResponse:
    """Response format for list_available=true."""

    evaluations: list[EvaluationListItem]
    total_count: int
    filters_applied: dict[str, str]  # Non-null filters applied

class EvaluationListItem:
    """Single item in evaluation list."""

    evaluation_id: str
    domain: str
    agent_endpoint: str | None
    status: str  # "completed", "failed", "working", "submitted"
    created_at: str  # ISO 8601 with Z suffix
    completed_at: str | None  # ISO 8601, only for terminal states
    summary: EvaluationSummaryMetrics | None  # Only for completed evaluations

class EvaluationSummaryMetrics:
    """Quick metrics for completed evaluations."""

    success_rate: float  # 0.0 to 1.0
    total_tasks: int
    successful: int
```

### 3. Single Evaluation Response (Output)

```python
class SingleEvaluationResponse:
    """Response format for evaluation_id lookup."""

    evaluation_id: str
    domain: str
    agent_endpoint: str | None
    status: str
    created_at: str  # ISO 8601
    completed_at: str | None  # ISO 8601

    # Full state history
    state_history: list[StateTransitionRecord]

    # Original request
    request: EvaluationRequestRecord

    # Results (only for completed evaluations)
    results: EvaluationResultsRecord | None

    # Error (only for failed evaluations)
    error: str | None

class StateTransitionRecord:
    """A state change in evaluation lifecycle."""

    state: str  # "submitted", "working", "completed", "failed"
    at: str  # ISO 8601 timestamp
    progress: int | None  # Percentage at time of transition

class EvaluationRequestRecord:
    """Original evaluation request parameters."""

    user_llm: str | None
    num_trials: int
    num_tasks: int

class EvaluationResultsRecord:
    """Final evaluation results."""

    success_rate: float
    total_tasks: int
    successful: int
    tasks: list[TaskResultRecord]
    # Only if include_simulations=true
    simulations: list[SimulationDataRecord] | None

class TaskResultRecord:
    """Per-task result."""

    task_id: str
    success: bool
    reward: float

class SimulationDataRecord:
    """Full simulation data (only when include_simulations=true)."""

    task_id: str
    duration: float
    termination_reason: str
    messages: list[dict]  # Full message history
    reward_info: dict | None
```

### 4. Error Response (Output)

```python
class ErrorResponse:
    """Error response format."""

    error: str  # Error message
    message: str | None  # Additional context
    # For "not found" errors:
    available_evaluations: list[str] | None
```

## Validation Rules

### Input Validation

| Field | Rule | Error Message |
|-------|------|---------------|
| evaluation_id | Must match `^eval-\d{13}-[a-f0-9]{6}$` or alphanumeric legacy format | "Invalid evaluation_id format" |
| domain | Must be one of: airline, retail, telecom, mock | "Invalid domain. Valid: airline, retail, telecom, mock" |
| status | Must be one of: completed, failed, working, submitted | "Invalid status. Valid: completed, failed, working, submitted" |
| after | Must be valid ISO 8601 timestamp | "Invalid 'after' timestamp. Use ISO 8601 format (e.g., 2024-01-14T00:00:00Z)" |
| before | Must be valid ISO 8601 timestamp | "Invalid 'before' timestamp. Use ISO 8601 format (e.g., 2024-01-15T00:00:00Z)" |
| limit | Must be 1-100 | "Limit must be between 1 and 100" |
| after < before | If both provided, after must be before before | "Invalid time range: 'after' must be before 'before'" |

### Response Validation

| Field | Rule |
|-------|------|
| timestamps | All datetime fields use ISO 8601 with Z suffix |
| success_rate | 0.0 to 1.0 |
| total_count | Non-negative integer |
| evaluations | Sorted by created_at descending |

## State Transitions

```
                    ┌───────────────┐
                    │   SUBMITTED   │
                    └───────┬───────┘
                            │ update_progress()
                            ▼
                    ┌───────────────┐
            ┌───────│    WORKING    │───────┐
            │       └───────────────┘       │
            │ complete_evaluation()         │ fail_evaluation()
            ▼                               ▼
    ┌───────────────┐               ┌───────────────┐
    │   COMPLETED   │               │    FAILED     │
    └───────────────┘               └───────────────┘
```

Terminal states: COMPLETED, FAILED, ABANDONED

## Extended EvaluationSummary Model

The existing `EvaluationSummary` model in `src/tau2/store/models.py` needs extension:

```python
class EvaluationSummary(BaseModel):
    """Summary view of an evaluation for listing."""

    evaluation_id: str
    trace_id: str | None = None
    session_id: str | None = None
    status: EvaluationStatus
    domain: str
    agent_endpoint: str | None = None  # NEW: for filtering display
    created_at: datetime
    completed_at: datetime | None = None  # NEW: for duration info
    progress: int | None = None
    summary: dict | None = None  # NEW: {success_rate, total_tasks, successful}
```

## Relationship to Existing Models

| New Concept | Maps To | Location |
|-------------|---------|----------|
| EvaluationListItem | EvaluationSummary (extended) | src/tau2/store/models.py |
| SingleEvaluationResponse | Evaluation | src/tau2/store/models.py |
| EvaluationResultsRecord | EvaluationResults | src/tau2/store/models.py |
| TaskResultRecord | TaskResult | src/tau2/store/models.py |
| SimulationDataRecord | SimulationData | src/tau2/store/models.py |
