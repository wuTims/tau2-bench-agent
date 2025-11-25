"""
ADK agent definition for tau2-bench evaluation service.

This agent exposes tau2-bench evaluation capabilities via A2A protocol.
"""

from google.adk.agents import LlmAgent

from .tools import GetEvaluationResults, ListDomains, RunTau2Evaluation

# Agent instruction prompt
INSTRUCTION = """
You are a conversational agent evaluation service powered by tau2-bench.

You can evaluate other conversational agents across multiple customer service domains:
- airline: Flight booking, modifications, cancellations
- retail: Product orders, returns, exchanges
- telecom: Technical support, billing issues
- mock: Simple test scenarios

When a user requests an evaluation:
1. Clarify the evaluation parameters (domain, agent endpoint, number of tasks)
2. Use run_tau2_evaluation tool to execute the evaluation
3. Provide clear, actionable feedback on agent performance
4. Offer to retrieve detailed results using get_evaluation_results

Be helpful in explaining evaluation metrics and suggesting improvements.
"""


# Define the ADK Agent
root_agent = LlmAgent(
    name="tau2_eval_agent",
    model="gemini-2.0-flash-exp",
    instruction=INSTRUCTION,
    description="Agent evaluation service using tau2-bench framework across airline, retail, and telecom domains",
    tools=[
        RunTau2Evaluation(
            name="run_tau2_evaluation",
            description="""Run a tau2-bench evaluation of a conversational agent.

            Parameters:
            - domain: Evaluation domain (airline, retail, telecom, mock)
            - agent_endpoint: A2A endpoint of agent to evaluate
            - user_llm: LLM model for user simulator (default: gpt-4o)
            - num_trials: Number of trials per task (default: 1)
            - num_tasks: Number of tasks to evaluate (optional)
            - task_ids: Optional list of specific task IDs to run
            """,
        ),
        ListDomains(
            name="list_domains",
            description="List all available tau2-bench evaluation domains and their descriptions",
        ),
        GetEvaluationResults(
            name="get_evaluation_results",
            description="Get detailed results from a tau2-bench evaluation by evaluation_id",
        ),
    ],
)
