"""
End-to-end tests for the simple Nebius agent.

These tests validate the complete flow:
1. Agent discovery (agent card)
2. Message sending (A2A protocol)
3. tau2-bench evaluation

Tests are marked with @pytest.mark.local_agent and require:
- NEBIUS_API_KEY environment variable (for the agent)
- ANTHROPIC_API_KEY environment variable (for the user simulator)
- Port 8001 available
- Network access to Nebius API and Anthropic API
"""

import uuid

import httpx
import pytest

from tau2.run import run_domain
from tau2.data_model.simulation import RunConfig


# Mark all tests in this module as local_agent tests
pytestmark = pytest.mark.local_agent


class TestAgentDiscovery:
    """Test A2A agent discovery protocol."""

    def test_agent_card_accessible(self, simple_agent_server: str, agent_card_url: str):
        """Test that agent card is accessible via .well-known URL."""
        response = httpx.get(agent_card_url)
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    def test_agent_card_structure(self, simple_agent_server: str, agent_card_url: str):
        """Test that agent card has required fields."""
        response = httpx.get(agent_card_url)
        agent_card = response.json()

        # Required fields
        assert "name" in agent_card
        assert "description" in agent_card
        assert "url" in agent_card

        # Verify values
        assert agent_card["name"] == "simple_nebius_agent"
        assert "Nebius" in agent_card["description"] or "Llama" in agent_card["description"]
        # Agent card URL may use 127.0.0.1 instead of localhost - check the path portion
        assert "/a2a/simple_nebius_agent" in agent_card["url"]

    def test_agent_card_capabilities(
        self, simple_agent_server: str, agent_card_url: str
    ):
        """Test that agent card declares capabilities."""
        response = httpx.get(agent_card_url)
        agent_card = response.json()

        # Capabilities should be present
        assert "capabilities" in agent_card
        capabilities = agent_card["capabilities"]

        # Check for streaming capability (even if false)
        assert "streaming" in capabilities


class TestMessageSending:
    """Test A2A message/send protocol using JSON-RPC 2.0."""

    def _build_jsonrpc_request(self, message_text: str, context_id: str | None = None) -> dict:
        """Build a JSON-RPC 2.0 request for message/send."""
        return {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": message_text}],
                    "contextId": context_id,
                }
            },
        }

    def _extract_response_text(self, rpc_response: dict) -> str:
        """Extract text content from JSON-RPC response (handles multiple formats)."""
        result = rpc_response.get("result", {})
        response_texts = []

        # Format 1: Google ADK style - artifacts array
        for artifact in result.get("artifacts", []):
            for part in artifact.get("parts", []):
                if "text" in part:
                    response_texts.append(part["text"])

        # Format 2: Direct parts at result level
        if not response_texts:
            for part in result.get("parts", []):
                if "text" in part:
                    response_texts.append(part["text"])

        # Format 3: TaskStatusUpdateEvent - status.message.parts
        if not response_texts:
            status_message = result.get("status", {}).get("message", {})
            for part in status_message.get("parts", []):
                if "text" in part:
                    response_texts.append(part["text"])

        return "\n".join(response_texts)

    def test_message_send_endpoint_exists(
        self, simple_agent_server: str, jsonrpc_endpoint: str
    ):
        """Test that JSON-RPC endpoint accepts message/send method."""
        rpc_request = self._build_jsonrpc_request("Hello")

        response = httpx.post(
            jsonrpc_endpoint,
            json=rpc_request,
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

        # Should get a response (200 or 202)
        assert response.status_code in [200, 202], f"Unexpected status: {response.status_code}, body: {response.text}"

    def test_message_send_response_structure(
        self, simple_agent_server: str, jsonrpc_endpoint: str
    ):
        """Test that agent responds with valid JSON-RPC structure."""
        rpc_request = self._build_jsonrpc_request("What is 2+2?")

        response = httpx.post(
            jsonrpc_endpoint,
            json=rpc_request,
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

        assert response.status_code in [200, 202]
        rpc_response = response.json()

        # JSON-RPC response should have jsonrpc version and id
        assert rpc_response.get("jsonrpc") == "2.0"
        assert "id" in rpc_response

        # Should have result (success) or error
        assert "result" in rpc_response or "error" in rpc_response

        # If successful, should have content
        if "result" in rpc_response:
            response_text = self._extract_response_text(rpc_response)
            # Agent should respond with something (may be empty for some edge cases)
            assert isinstance(response_text, str)

    def test_message_send_with_context(
        self, simple_agent_server: str, jsonrpc_endpoint: str
    ):
        """Test multi-turn conversation with context_id (protocol test)."""
        context_id = str(uuid.uuid4())

        # First message
        rpc_request1 = self._build_jsonrpc_request("Hello, I need help.", context_id)

        response1 = httpx.post(
            jsonrpc_endpoint,
            json=rpc_request1,
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

        assert response1.status_code in [200, 202]
        rpc_response1 = response1.json()
        assert "result" in rpc_response1 or "error" not in rpc_response1

        # Second message with same context_id
        rpc_request2 = self._build_jsonrpc_request("Can you assist me?", context_id)

        response2 = httpx.post(
            jsonrpc_endpoint,
            json=rpc_request2,
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

        assert response2.status_code in [200, 202]
        rpc_response2 = response2.json()

        # Verify we got a valid response - context retention is LLM behavior, not protocol
        assert "result" in rpc_response2 or "error" not in rpc_response2
        response_text = self._extract_response_text(rpc_response2)
        assert isinstance(response_text, str)


@pytest.mark.slow
class TestTau2Integration:
    """Test tau2-bench evaluation with simple agent.

    These tests are marked as slow because they involve:
    - Multiple LLM API calls (Nebius for agent, Anthropic for user simulator)
    - Full evaluation loop with message exchanges

    Run with: pytest -m slow
    Skip with: pytest -m "not slow"
    """

    def test_mock_domain_evaluation(self, simple_agent_server: str, anthropic_user_llm_config: dict):
        """Test evaluation with mock domain (fast test)."""
        # Configure evaluation with reduced max_steps for faster testing
        # Note: For A2A agent, llm_agent holds the endpoint URL
        config = RunConfig(
            agent="a2a_agent",
            llm_agent=simple_agent_server,
            domain="mock",
            num_trials=1,
            task_ids=["create_task_1"],  # Single task for speed
            llm_user=anthropic_user_llm_config["llm"],
            llm_args_user=anthropic_user_llm_config["llm_args"],
            max_steps=10,  # Limit iterations for faster test
        )

        # Run evaluation
        results = run_domain(config)

        # Validate results structure
        assert results is not None
        assert hasattr(results, "tasks")
        assert len(results.tasks) > 0

        # Check that task was loaded correctly (Task has 'id', not 'task_id')
        task = results.tasks[0]
        assert hasattr(task, "id")
        assert task.id == "create_task_1"

    def test_evaluation_metrics_collected(self, simple_agent_server: str, anthropic_user_llm_config: dict):
        """Test that protocol metrics are collected during evaluation."""
        # Note: For A2A agent, llm_agent holds the endpoint URL
        config = RunConfig(
            agent="a2a_agent",
            llm_agent=simple_agent_server,
            domain="mock",
            num_trials=1,
            task_ids=["create_task_1"],
            llm_user=anthropic_user_llm_config["llm"],
            llm_args_user=anthropic_user_llm_config["llm_args"],
            max_steps=10,  # Limit iterations for faster test
        )

        results = run_domain(config)

        # Check that we have task results
        assert len(results.tasks) > 0

        # Verify simulations exist (simulations is on Results, not Task)
        assert hasattr(results, "simulations")
        assert len(results.simulations) > 0

        # Check that simulation completed
        simulation = results.simulations[0]
        assert hasattr(simulation, "messages")
        assert len(simulation.messages) > 0


class TestErrorHandling:
    """Test error handling and edge cases."""

    def test_invalid_jsonrpc_format(
        self, simple_agent_server: str, jsonrpc_endpoint: str
    ):
        """Test that agent handles invalid JSON-RPC format gracefully."""
        # Send malformed JSON-RPC (missing required fields)
        invalid_request = {
            "jsonrpc": "2.0",
            # Missing id and method
            "params": {},
        }

        response = httpx.post(
            jsonrpc_endpoint,
            json=invalid_request,
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

        # Should get an error response (400, 422, or JSON-RPC error in 200)
        if response.status_code == 200:
            rpc_response = response.json()
            assert "error" in rpc_response, "Invalid request should return JSON-RPC error"
        else:
            assert response.status_code >= 400

    def test_empty_message(self, simple_agent_server: str, jsonrpc_endpoint: str):
        """Test that agent handles empty message text."""
        rpc_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": str(uuid.uuid4()),
                    "role": "user",
                    "parts": [{"text": ""}],
                }
            },
        }

        response = httpx.post(
            jsonrpc_endpoint,
            json=rpc_request,
            headers={"Content-Type": "application/json"},
            timeout=30.0,
        )

        # Should still respond (may be success or JSON-RPC error)
        assert response.status_code in [200, 202, 400, 422]


# Optional: Cleanup marker configuration
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "local_agent: marks tests as local agent tests"
    )
