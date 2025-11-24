"""
GetEvaluationResults tool for ADK agent.

This tool enables external agents to retrieve completed evaluation results.
Note: This is a placeholder implementation for Phase 1.
"""

from typing import Any

from google.adk.tools import BaseTool


class GetEvaluationResults(BaseTool):
    """Retrieve results from a completed evaluation"""

    name = "get_evaluation_results"
    description = "Get detailed results from a tau2-bench evaluation by evaluation_id"

    async def __call__(self, tool_context, evaluation_id: str) -> dict[str, Any]:
        """Load evaluation results from storage"""
        # tau2-bench Results are returned directly from run_domain()
        # This tool would need to load from saved results if save_to was specified
        # For Phase 1, return guidance to use run_tau2_evaluation which returns results directly
        return {
            "error": "Results retrieval not yet implemented",
            "message": "Use run_tau2_evaluation tool which returns results directly. "
            + "For persisted results, tau2-bench saves to JSON files which can be loaded manually.",
        }
