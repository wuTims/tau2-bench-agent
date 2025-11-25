"""
RunTau2Evaluation tool for ADK agent.

This tool enables external agents to request tau2-bench evaluations via A2A protocol.
"""

from typing import Any

from google.adk.tools import BaseTool
from loguru import logger


class RunTau2Evaluation(BaseTool):
    """Tool to run tau2-bench agent evaluation"""

    name = "run_tau2_evaluation"
    description = """
    Run a tau2-bench evaluation of a conversational agent.

    Parameters:
    - domain: Evaluation domain (airline, retail, telecom, mock)
    - agent_endpoint: A2A endpoint of agent to evaluate (e.g., https://agent.example.com)
    - user_llm: LLM model for user simulator (e.g., gpt-4o, claude-3-5-sonnet-20241022)
    - num_trials: Number of trials per task (default: 1)
    - num_tasks: Number of tasks to evaluate (default: all tasks in domain)
    - task_ids: Optional list of specific task IDs to run

    Returns:
    - status: Evaluation completion status
    - timestamp: Evaluation start timestamp
    - summary: Evaluation metrics (success_rate, total_simulations, total_tasks)
    - tasks: List of evaluated tasks with IDs and names
    """

    async def __call__(
        self,
        tool_context,
        domain: str,
        agent_endpoint: str,
        user_llm: str = "gpt-4o",
        num_trials: int = 1,
        num_tasks: int | None = None,
        task_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        """Execute tau2-bench evaluation"""
        try:
            # Validate domain
            valid_domains = ["airline", "retail", "telecom", "mock"]
            if domain not in valid_domains:
                raise ValueError(
                    f"Invalid domain: {domain}. Must be one of {valid_domains}"
                )

            # Import tau2-bench components
            from tau2.data_model.simulation import RunConfig
            from tau2.run import run_domain

            logger.info(
                "Starting tau2-bench evaluation",
                domain=domain,
                agent_endpoint=agent_endpoint,
                user_llm=user_llm,
                num_trials=num_trials,
            )

            # Create run configuration
            config = RunConfig(
                domain=domain,
                agent="a2a_agent",  # Use A2A client implementation
                user="user_simulator",
                task_ids=task_ids,
                llm_agent=agent_endpoint,  # A2A agent endpoint
                llm_args_agent={},
                llm_user=user_llm,
                llm_args_user={},
                num_trials=num_trials,
                max_steps=50,
                max_errors=10,
                save_to=None,
                llm_review=False,
                max_concurrency=3,
            )

            # Run evaluations
            results = run_domain(config)

            # Extract metrics from Results object
            # Results contains: timestamp, info, tasks, simulations
            total_simulations = len(results.simulations)
            successful_sims = sum(1 for sim in results.simulations if sim.success)
            success_rate = (
                successful_sims / total_simulations if total_simulations > 0 else 0.0
            )

            logger.info(
                "Evaluation completed",
                domain=domain,
                agent_endpoint=agent_endpoint,
                success_rate=success_rate,
                total_simulations=total_simulations,
            )

            return {
                "status": "completed",
                "timestamp": results.timestamp,
                "summary": {
                    "total_simulations": total_simulations,
                    "total_tasks": len(results.tasks),
                    "success_rate": success_rate,
                    "successful_simulations": successful_sims,
                },
                "tasks": [
                    {"task_id": task.id, "name": task.name} for task in results.tasks
                ],
            }

        except ValueError as e:
            logger.error("Invalid evaluation parameters", error=str(e))
            raise

        except Exception as e:
            logger.error(
                "Evaluation failed",
                domain=domain,
                agent_endpoint=agent_endpoint,
                error=str(e),
                exc_info=True,
            )
            raise
