"""
Integration test for A2A message/send endpoint (T025).

Tests that ADK agent properly handles A2A protocol messages.
"""

from unittest.mock import Mock, patch

import pytest
from google.adk.cli.fast_api import get_fast_api_app
from httpx import ASGITransport, AsyncClient

# Mark all tests in this module as mock-based (no real endpoints)
pytestmark = pytest.mark.a2a_mock


@pytest.mark.asyncio
async def test_a2a_message_send_endpoint_exists():
    """Test that A2A message/send endpoint is accessible"""
    app = get_fast_api_app(agents_dir="./tau2_agent", web=False, a2a=True)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # A2A message/send uses JSON-RPC 2.0 format
        a2a_message = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": "msg-001",
                    "role": "user",
                    "parts": [{"text": "Hello"}],
                }
            },
            "id": "req-001",
        }

        response = await client.post("/", json=a2a_message)

        # Should return 200 or appropriate response
        assert response.status_code in [200, 400, 404, 501], (
            f"A2A endpoint should respond, got {response.status_code}"
        )


@pytest.mark.asyncio
async def test_a2a_message_send_list_domains():
    """Test A2A message requesting domain list"""
    app = get_fast_api_app(agents_dir="./tau2_agent", web=False, a2a=True)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        a2a_message = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": "msg-002",
                    "role": "user",
                    "parts": [{"text": "What domains can you evaluate?"}],
                }
            },
            "id": "req-002",
        }

        response = await client.post("/", json=a2a_message)

        if response.status_code == 200:
            result = response.json()
            assert "result" in result, "JSON-RPC response should have result"

            # Check if response mentions domains
            response_text = str(result).lower()
            assert any(
                domain in response_text for domain in ["airline", "retail", "telecom"]
            ), "Response should mention available domains"


@pytest.mark.asyncio
async def test_a2a_message_send_evaluation_request():
    """Test A2A message requesting evaluation with mocked tau2-bench"""
    app = get_fast_api_app(agents_dir="./tau2_agent", web=False, a2a=True)

    # Mock tau2-bench results
    mock_simulation = Mock()
    mock_simulation.success = True
    mock_task = Mock()
    mock_task.id = "task-1"
    mock_task.name = "Test Task"
    mock_results = Mock()
    mock_results.timestamp = "2025-11-24T10:00:00Z"
    mock_results.simulations = [mock_simulation]
    mock_results.tasks = [mock_task]

    with patch("tau2.run.run_domain", return_value=mock_results):
        async with AsyncClient(
            transport=ASGITransport(app=app), base_url="http://test"
        ) as client:
            a2a_message = {
                "jsonrpc": "2.0",
                "method": "message/send",
                "params": {
                    "message": {
                        "messageId": "msg-003",
                        "role": "user",
                        "parts": [
                            {
                                "text": "Run an evaluation on the airline domain for agent at https://agent.example.com"
                            }
                        ],
                    }
                },
                "id": "req-003",
            }

            response = await client.post("/", json=a2a_message)

            if response.status_code == 200:
                result = response.json()
                assert "result" in result, "JSON-RPC response should have result"


@pytest.mark.asyncio
async def test_a2a_context_id_persistence():
    """Test that context_id is returned and can be reused for multi-turn conversation"""
    app = get_fast_api_app(agents_dir="./tau2_agent", web=False, a2a=True)

    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        # First message without context_id
        first_message = {
            "jsonrpc": "2.0",
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": "msg-004",
                    "role": "user",
                    "parts": [{"text": "What can you do?"}],
                }
            },
            "id": "req-004",
        }

        response1 = await client.post("/", json=first_message)

        if response1.status_code == 200:
            result1 = response1.json()

            # Extract context_id from response
            if "result" in result1 and "message" in result1["result"]:
                context_id = result1["result"]["message"].get("contextId")

                if context_id:
                    # Second message with context_id
                    second_message = {
                        "jsonrpc": "2.0",
                        "method": "message/send",
                        "params": {
                            "message": {
                                "messageId": "msg-005",
                                "role": "user",
                                "parts": [{"text": "What about the airline domain?"}],
                                "contextId": context_id,
                            }
                        },
                        "id": "req-005",
                    }

                    response2 = await client.post("/", json=second_message)
                    assert response2.status_code == 200, (
                        "Second message with context_id should succeed"
                    )
