"""
GetEvaluationResults Tool Interface Contract

This file defines the expected interface for the GetEvaluationResults tool.
It serves as a contract between the tool implementation and its consumers.

Note: This is a design artifact, not production code. The actual implementation
lives in tau2_agent/tools/get_evaluation_results.py.
"""

from datetime import datetime
from typing import Any, Protocol, TypedDict


# ============================================================================
# Input Types
# ============================================================================


class ToolArgs(TypedDict, total=False):
    """Tool input arguments schema."""

    # Single evaluation retrieval
    evaluation_id: str  # e.g., "eval-1703697600000-a1b2c3"

    # List mode
    list_available: bool  # If true, list evaluations with filters

    # Filters (only used when list_available=true)
    domain: str  # "airline", "retail", "telecom", "mock"
    status: str  # "completed", "failed", "working", "submitted"
    after: str  # ISO 8601 timestamp, e.g., "2024-01-14T00:00:00Z"
    before: str  # ISO 8601 timestamp, e.g., "2024-01-15T00:00:00Z"
    agent_endpoint: str  # Filter by agent endpoint URL

    # Response control
    limit: int  # Max results (default 20, max 100)
    include_simulations: bool  # Include full simulation data (default false)
    include_sessions: bool  # Include in-progress sessions (default true)


# ============================================================================
# Output Types - List Mode
# ============================================================================


class SummaryMetrics(TypedDict, total=False):
    """Quick metrics for completed evaluations."""

    success_rate: float  # 0.0 to 1.0
    total_tasks: int
    successful: int


class EvaluationListItem(TypedDict, total=False):
    """Single item in evaluation list."""

    evaluation_id: str
    domain: str
    agent_endpoint: str | None
    status: str  # "completed", "failed", "working", "submitted"
    created_at: str  # ISO 8601 with Z suffix
    completed_at: str | None  # ISO 8601, only for terminal states
    summary: SummaryMetrics | None  # Only for completed evaluations


class FiltersApplied(TypedDict, total=False):
    """Record of non-null filters applied to query."""

    domain: str
    status: str
    after: str
    before: str
    agent_endpoint: str


class ListResponse(TypedDict):
    """Response format for list_available=true."""

    evaluations: list[EvaluationListItem]
    total_count: int
    filters_applied: FiltersApplied


# ============================================================================
# Output Types - Single Evaluation Mode
# ============================================================================


class StateTransitionRecord(TypedDict):
    """A state change in evaluation lifecycle."""

    state: str  # "submitted", "working", "completed", "failed"
    at: str  # ISO 8601 timestamp
    progress: int | None  # Percentage at time of transition


class RequestRecord(TypedDict, total=False):
    """Original evaluation request parameters."""

    user_llm: str | None
    num_trials: int
    num_tasks: int


class TaskResultRecord(TypedDict):
    """Per-task result."""

    task_id: str
    success: bool
    reward: float


class SimulationRecord(TypedDict, total=False):
    """Full simulation data (only when include_simulations=true)."""

    task_id: str
    duration: float
    termination_reason: str
    messages: list[dict[str, Any]]
    reward_info: dict[str, Any] | None


class ResultsRecord(TypedDict, total=False):
    """Final evaluation results."""

    success_rate: float
    total_tasks: int
    successful: int
    tasks: list[TaskResultRecord]
    simulations: list[SimulationRecord] | None  # Only if include_simulations=true


class SingleEvaluationResponse(TypedDict, total=False):
    """Response format for evaluation_id lookup."""

    evaluation_id: str
    domain: str
    agent_endpoint: str | None
    status: str
    created_at: str  # ISO 8601
    completed_at: str | None  # ISO 8601
    state_history: list[StateTransitionRecord]
    request: RequestRecord
    results: ResultsRecord | None  # Only for completed evaluations
    error: str | None  # Only for failed evaluations


# ============================================================================
# Output Types - Error
# ============================================================================


class ErrorResponse(TypedDict, total=False):
    """Error response format."""

    error: str  # Error message
    message: str  # Additional context
    available_evaluations: list[str]  # For "not found" errors


# ============================================================================
# Tool Protocol
# ============================================================================


class GetEvaluationResultsTool(Protocol):
    """Protocol defining the GetEvaluationResults tool interface."""

    name: str  # "get_evaluation_results"
    description: str

    async def run_async(
        self,
        *,
        args: ToolArgs,
        tool_context: Any,
    ) -> ListResponse | SingleEvaluationResponse | ErrorResponse:
        """
        Execute the tool.

        Args:
            args: Tool input arguments
            tool_context: ADK tool context (unused)

        Returns:
            One of:
            - ListResponse when list_available=true
            - SingleEvaluationResponse when evaluation_id provided
            - ErrorResponse on validation or not-found errors
        """
        ...


# ============================================================================
# Store Extension Protocol
# ============================================================================


class ListEvaluationsProtocol(Protocol):
    """Extended list_evaluations signature for EvaluationStore."""

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
    ) -> list[Any]:  # Returns list[EvaluationSummary]
        """
        List evaluations with optional filters.

        Args:
            domain: Filter by domain name
            status: Filter by evaluation status
            after: Return evaluations created after this time (NEW)
            before: Return evaluations created before this time (NEW)
            agent_endpoint: Filter by agent endpoint URL (NEW)
            include_sessions: Whether to include in-progress sessions
            limit: Maximum number of results

        Returns:
            List of EvaluationSummary objects, sorted by created_at descending
        """
        ...
