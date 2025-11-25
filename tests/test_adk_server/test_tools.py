"""
Integration test for ADK tools (T024).

Tests that RunTau2Evaluation and ListDomains tools work correctly.
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest

from tau2_agent.tools.get_evaluation_results import GetEvaluationResults
from tau2_agent.tools.list_domains import ListDomains
from tau2_agent.tools.run_tau2_evaluation import RunTau2Evaluation

# Mark all tests in this module as mock-based (no real endpoints)
pytestmark = pytest.mark.a2a_mock


@pytest.fixture
def mock_tool_context():
    """Create mock tool context for ADK tools"""
    context = Mock()
    context.session = Mock()
    context.session.state = {}
    return context


@pytest.mark.asyncio
async def test_list_domains_tool(mock_tool_context):
    """Test ListDomains tool returns available domains"""
    tool = ListDomains(
        name="list_domains",
        description="List all available tau2-bench evaluation domains",
    )

    result = await tool(mock_tool_context)

    assert "domains" in result, "ListDomains should return domains list"
    domains = result["domains"]
    assert len(domains) > 0, "Should have at least one domain"

    # Check required domains are present
    domain_names = [d["name"] for d in domains]
    assert "airline" in domain_names, "Should include airline domain"
    assert "retail" in domain_names, "Should include retail domain"
    assert "telecom" in domain_names, "Should include telecom domain"

    # Check domain structure
    for domain in domains:
        assert "name" in domain, "Domain should have name"
        assert "description" in domain, "Domain should have description"
        assert "num_tasks" in domain, "Domain should have num_tasks"


@pytest.mark.asyncio
async def test_run_tau2_evaluation_tool_success(mock_tool_context):
    """Test RunTau2Evaluation tool with successful evaluation"""
    tool = RunTau2Evaluation(
        name="run_tau2_evaluation", description="Run tau2-bench evaluation"
    )

    # Mock tau2-bench Results structure
    mock_simulation = Mock()
    mock_simulation.success = True

    mock_task = Mock()
    mock_task.id = "task-1"
    mock_task.name = "Test Task"

    mock_results = Mock()
    mock_results.timestamp = "2025-11-24T10:00:00Z"
    mock_results.simulations = [mock_simulation] * 10  # 10 successful simulations
    mock_results.tasks = [mock_task]

    with patch("tau2.run.run_domain", return_value=mock_results):
        result = await tool(
            mock_tool_context,
            domain="airline",
            agent_endpoint="https://agent.example.com",
            user_llm="gpt-4o",
            num_trials=1,
        )

    assert result["status"] == "completed", "Evaluation should complete successfully"
    assert result["timestamp"] == "2025-11-24T10:00:00Z", "Should include timestamp"
    assert "summary" in result, "Should include summary"
    assert result["summary"]["success_rate"] == 1.0, "All simulations should succeed"
    assert result["summary"]["total_simulations"] == 10, "Should have 10 simulations"


@pytest.mark.asyncio
async def test_run_tau2_evaluation_tool_invalid_domain(mock_tool_context):
    """Test RunTau2Evaluation tool with invalid domain"""
    tool = RunTau2Evaluation(
        name="run_tau2_evaluation", description="Run tau2-bench evaluation"
    )

    with pytest.raises(ValueError, match="Invalid domain"):
        await tool(
            mock_tool_context,
            domain="invalid_domain",
            agent_endpoint="https://agent.example.com",
            user_llm="gpt-4o",
        )


@pytest.mark.asyncio
async def test_get_evaluation_results_tool(mock_tool_context):
    """Test GetEvaluationResults tool (placeholder implementation)"""
    tool = GetEvaluationResults(
        name="get_evaluation_results", description="Get evaluation results"
    )

    result = await tool(mock_tool_context, evaluation_id="eval-123")

    # For now, this tool returns an error message
    assert "error" in result or "message" in result, (
        "GetEvaluationResults should return error/message"
    )
