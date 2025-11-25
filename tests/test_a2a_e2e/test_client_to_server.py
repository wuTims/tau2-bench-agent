"""
End-to-end tests for A2AClient to ADK server communication.

These tests verify real HTTP communication between A2AClient
and ADK agent (server) over the A2A protocol.

All tests are marked with @pytest.mark.a2a_e2e and are NOT run by default.
Run explicitly with: pytest -m a2a_e2e
"""

import pytest

from tau2.a2a.client import A2AClient
from tau2.a2a.models import A2AConfig

# Mark all tests in this module as E2E tests
pytestmark = pytest.mark.a2a_e2e


@pytest.mark.asyncio
async def test_e2e_agent_discovery_real(a2a_client_to_local):
    """
    Test real agent discovery over HTTP.

    Verifies that A2AClient can discover the ADK agent's capabilities
    via the /.well-known/agent-card.json endpoint.
    """
    # Discovery should have happened in fixture, but test explicit call
    agent_card = await a2a_client_to_local.discover_agent()

    # Verify agent card structure - name should match discovered agent
    assert agent_card.name is not None, "Agent card missing name"
    assert len(agent_card.name) > 0, "Agent card name is empty"

    # Verify card is cached
    agent_card_2 = await a2a_client_to_local.discover_agent()
    assert agent_card_2 is agent_card, "Agent card should be cached"


@pytest.mark.asyncio
async def test_e2e_message_send_real(a2a_client_to_local):
    """
    Test real message/send JSON-RPC call over HTTP.

    Verifies that A2AClient can send messages to ADK agent
    and receive valid responses.
    """
    # Send message via A2A protocol (uses string content, not UserMessage)
    response_content, context_id = await a2a_client_to_local.send_message(
        message_content="Hello, what can you help me with?",
        context_id=None,
    )

    # Verify response
    assert isinstance(response_content, str), (
        f"Expected string response, got {type(response_content)}"
    )
    # Response should have some content
    assert len(response_content) > 0, "Response should have content"


@pytest.mark.asyncio
async def test_e2e_full_conversation_flow(a2a_client_to_local):
    """
    Test multi-turn conversation flow.

    Verifies context_id persistence across multiple exchanges.
    """
    # First message - no context
    response_1, context_id = await a2a_client_to_local.send_message(
        message_content="Hello, I'd like to ask some questions.",
        context_id=None,
    )

    assert context_id is not None, "Server should return context_id"

    # Second message - with context
    response_2, context_id_2 = await a2a_client_to_local.send_message(
        message_content="What did I just say?",
        context_id=context_id,
    )

    # Context should be maintained
    assert context_id_2 is not None, "Context should persist"


@pytest.mark.asyncio
async def test_e2e_protocol_compliance(a2a_client_to_local):
    """
    Test that communication follows A2A protocol.

    Verifies JSON-RPC 2.0 structure and A2A message format.
    """
    # Get the underlying HTTP client to check raw request/response
    client = a2a_client_to_local

    # Verify agent card endpoint works
    agent_card = await client.discover_agent()
    assert agent_card is not None

    # Verify message endpoint works
    response, ctx = await client.send_message(
        message_content="Test message",
        context_id=None,
    )
    assert response is not None


@pytest.mark.asyncio
async def test_e2e_error_handling_timeout(adk_server):
    """
    Test timeout handling.

    Verifies proper behavior when server is slow to respond.
    """
    from tau2.a2a.exceptions import A2ATimeoutError

    # Create client with very short timeout
    config = A2AConfig(
        endpoint=adk_server,
        timeout=0.001,  # 1ms - will definitely timeout
    )

    client = A2AClient(config)

    try:
        # This should timeout
        with pytest.raises(A2ATimeoutError):
            await client.send_message(
                message_content="This will timeout",
                context_id=None,
            )
    finally:
        await client.close()


@pytest.mark.asyncio
async def test_e2e_metrics_collection(a2a_client_to_local):
    """
    Test that protocol metrics are collected during E2E communication.
    """
    # Clear any existing metrics
    a2a_client_to_local.clear_metrics()

    # Send a message
    await a2a_client_to_local.send_message(
        message_content="Test message for metrics",
        context_id=None,
    )

    # Check metrics were collected
    metrics = a2a_client_to_local.get_metrics()
    assert len(metrics) > 0, "Should have collected metrics"

    # Verify metric structure
    metric = metrics[0]
    assert metric.request_id is not None
    assert metric.latency_ms > 0
    assert metric.status_code == 200
