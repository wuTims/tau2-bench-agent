"""
End-to-end tests for A2AAgent client to ADK server communication.

These tests verify real HTTP communication between A2AAgent (client)
and ADK agent (server) over the A2A protocol.

All tests are marked with @pytest.mark.a2a_e2e and are NOT run by default.
Run explicitly with: pytest -m a2a_e2e
"""

import pytest

from tau2.a2a.models import A2AConfig
from tau2.agent.a2a_agent import A2AAgent
from tau2.data_model.message import AssistantMessage, ToolMessage, UserMessage

# Mark all tests in this module as E2E tests
pytestmark = pytest.mark.a2a_e2e


@pytest.mark.asyncio
async def test_e2e_agent_discovery_real(a2a_client_to_local, verify_server_health):
    """
    Test real agent discovery over HTTP.

    Verifies that A2AClient can discover the ADK agent's capabilities
    via the /.well-known/agent-card.json endpoint.
    """
    # Discovery should have happened in fixture, but test explicit call
    agent_card = await a2a_client_to_local.discover_agent()

    # Verify agent card structure
    assert agent_card.name == "tau2_eval_agent", (
        f"Expected agent name 'tau2_eval_agent', got '{agent_card.name}'"
    )
    assert agent_card.url is not None, "Agent card missing URL"
    assert agent_card.capabilities is not None, "Agent card missing capabilities"

    # Verify card is cached
    agent_card_2 = await a2a_client_to_local.discover_agent()
    assert agent_card_2 is agent_card, "Agent card should be cached"


@pytest.mark.asyncio
async def test_e2e_message_send_real(
    a2a_client_to_local, verify_server_health, sample_test_tools
):
    """
    Test real message/send JSON-RPC call over HTTP.

    Verifies that A2AClient can send messages to ADK agent
    and receive valid responses.
    """
    # Create user message
    user_msg = UserMessage(
        role="user",
        content="What evaluation domains are available?",
    )

    # Send message via A2A protocol
    response_msg, context_id = await a2a_client_to_local.send_message(
        message=user_msg,
        context_id=None,
        tools=sample_test_tools,
    )

    # Verify response
    assert isinstance(response_msg, AssistantMessage), (
        f"Expected AssistantMessage, got {type(response_msg)}"
    )
    assert response_msg.role == "assistant"
    assert context_id is not None, "Server should return context_id"

    # Response should mention domains (airline, retail, telecom)
    response_text = response_msg.content or ""
    assert len(response_text) > 0 or response_msg.is_tool_call(), (
        "Response should have content or tool call"
    )


@pytest.mark.asyncio
async def test_e2e_full_conversation_flow(
    a2a_client_to_local, verify_server_health, sample_test_tools
):
    """
    Test multi-turn conversation with context persistence.

    Verifies that context_id is properly maintained across
    multiple message exchanges.
    """
    context_id = None

    # Turn 1: Initial greeting
    user_msg_1 = UserMessage(
        role="user",
        content="Hello, what can you help me with?",
    )

    response_1, context_id = await a2a_client_to_local.send_message(
        message=user_msg_1,
        context_id=context_id,
        tools=sample_test_tools,
    )

    assert isinstance(response_1, AssistantMessage)
    assert context_id is not None, "Context ID should be set after first turn"
    first_context_id = context_id

    # Turn 2: Follow-up question
    user_msg_2 = UserMessage(
        role="user",
        content="Can you list the available domains?",
    )

    response_2, context_id = await a2a_client_to_local.send_message(
        message=user_msg_2,
        context_id=context_id,
        tools=sample_test_tools,
    )

    assert isinstance(response_2, AssistantMessage)
    assert context_id == first_context_id, "Context ID should persist across turns"

    # Turn 3: Another follow-up
    user_msg_3 = UserMessage(
        role="user",
        content="Tell me more about the airline domain",
    )

    response_3, context_id = await a2a_client_to_local.send_message(
        message=user_msg_3,
        context_id=context_id,
        tools=sample_test_tools,
    )

    assert isinstance(response_3, AssistantMessage)
    assert context_id == first_context_id, "Context ID should persist across all turns"


@pytest.mark.asyncio
async def test_e2e_tool_call_execution(adk_server, verify_server_health, sample_test_tools):
    """
    Test complete tool call cycle over real HTTP.

    Verifies the full flow:
    1. User requests action requiring tool
    2. Agent responds with tool call
    3. Tool is executed
    4. Tool result sent back to agent
    5. Agent responds with final answer
    """
    # Create A2AAgent with real HTTP client
    config = A2AConfig(endpoint=adk_server, timeout=30)
    agent = A2AAgent(
        config=config,
        tools=sample_test_tools,
        domain_policy="Test airline customer service agent",
    )

    # Get initial state
    state = agent.get_init_state()

    # User requests domain information (should trigger ListDomains tool)
    user_msg = UserMessage(
        role="user",
        content="What evaluation domains do you support?",
    )

    # Generate response - agent may call tool or respond directly
    assistant_msg, state = agent.generate_next_message(user_msg, state)

    assert isinstance(assistant_msg, AssistantMessage)
    assert state.context_id is not None, "Context should be established"

    # If agent made a tool call, execute it and send result back
    if assistant_msg.is_tool_call():
        assert assistant_msg.tool_calls is not None
        assert len(assistant_msg.tool_calls) > 0

        # For now, just verify the flow works - in real scenario
        # the orchestrator would execute the tool and send result back
        tool_call = assistant_msg.tool_calls[0]

        # Simulate tool execution result
        tool_result = ToolMessage(
            id=tool_call.id,
            role="tool",
            content='{"domains": ["airline", "retail", "telecom"]}',
            error=False,
            requestor="assistant",
        )

        # Send tool result back
        final_msg, state = agent.generate_next_message(tool_result, state)

        assert isinstance(final_msg, AssistantMessage)
        assert state.request_count == 2, "Should have made 2 requests"


def test_e2e_a2a_agent_sync_interface(adk_server, verify_server_health, sample_test_tools):
    """
    Test A2AAgent synchronous interface over real HTTP.

    A2AAgent wraps async operations in sync interface for compatibility
    with tau2-bench. This test verifies the sync wrapper works correctly.
    """
    # Create A2AAgent
    config = A2AConfig(endpoint=adk_server, timeout=30)
    agent = A2AAgent(
        config=config,
        tools=sample_test_tools,
        domain_policy="Test customer service agent",
    )

    # Get initial state
    state = agent.get_init_state()

    # Send message (sync call)
    user_msg = UserMessage(
        role="user",
        content="Hello, what domains can you evaluate?",
    )

    # This should work without explicit async/await
    assistant_msg, new_state = agent.generate_next_message(user_msg, state)

    # Verify response
    assert isinstance(assistant_msg, AssistantMessage)
    assert new_state.request_count == 1
    assert new_state.context_id is not None


@pytest.mark.asyncio
async def test_e2e_error_handling_network(adk_server, sample_test_tools):
    """
    Test error handling with real network conditions.

    Verifies that A2AAgent handles network errors gracefully.
    """
    from tau2.a2a.exceptions import A2AError

    # Create client with very short timeout to trigger timeout
    config = A2AConfig(endpoint=adk_server, timeout=0.001)  # 1ms timeout
    agent = A2AAgent(
        config=config,
        tools=sample_test_tools,
        domain_policy="Test agent",
    )

    state = agent.get_init_state()
    user_msg = UserMessage(role="user", content="Test")

    # Should raise timeout error
    with pytest.raises(A2AError):
        agent.generate_next_message(user_msg, state)


@pytest.mark.asyncio
async def test_e2e_protocol_compliance(a2a_client_to_local, verify_server_health):
    """
    Test A2A protocol compliance over real HTTP.

    Verifies that the ADK server properly implements:
    - JSON-RPC 2.0 format
    - A2A message structure
    - Required response fields
    """
    import httpx

    # Get the http_client from our A2A client
    http_client = a2a_client_to_local._http_client

    # Send raw JSON-RPC request to verify protocol compliance
    jsonrpc_request = {
        "jsonrpc": "2.0",
        "method": "message/send",
        "params": {
            "message": {
                "messageId": "test-msg-001",
                "role": "user",
                "parts": [{"text": "Hello"}],
            }
        },
        "id": "test-req-001",
    }

    response = await http_client.post("/", json=jsonrpc_request)

    # Verify response structure
    assert response.status_code == 200, f"Expected 200, got {response.status_code}"

    result = response.json()

    # Verify JSON-RPC 2.0 structure
    assert "jsonrpc" in result, "Response missing 'jsonrpc' field"
    assert result["jsonrpc"] == "2.0", f"Expected JSON-RPC 2.0, got {result['jsonrpc']}"
    assert "id" in result, "Response missing 'id' field"
    assert result["id"] == "test-req-001", "Response ID should match request ID"

    # Verify result structure
    assert "result" in result, "Response missing 'result' field"
    result_data = result["result"]

    assert "message" in result_data, "Result missing 'message' field"
    message = result_data["message"]

    # Verify message structure
    assert "messageId" in message, "Message missing 'messageId'"
    assert "role" in message, "Message missing 'role'"
    assert message["role"] == "agent", f"Expected role 'agent', got {message['role']}"
    assert "parts" in message, "Message missing 'parts'"
    assert len(message["parts"]) > 0, "Message parts should not be empty"


@pytest.mark.asyncio
async def test_e2e_concurrent_requests(adk_server, verify_server_health, sample_test_tools):
    """
    Test handling of concurrent requests to the same agent.

    Verifies that the ADK server can handle multiple simultaneous
    requests without interference.
    """
    import asyncio

    # Create multiple clients
    config = A2AConfig(endpoint=adk_server, timeout=30)

    agents = [
        A2AAgent(
            config=config,
            tools=sample_test_tools,
            domain_policy=f"Test agent {i}",
        )
        for i in range(3)
    ]

    # Create concurrent requests
    async def send_message_async(agent, msg_num):
        state = agent.get_init_state()
        user_msg = UserMessage(
            role="user",
            content=f"Request {msg_num}: What domains are available?",
        )
        # Run sync method in executor
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, agent.generate_next_message, user_msg, state
        )

    # Send concurrent requests
    tasks = [send_message_async(agent, i) for i, agent in enumerate(agents)]
    results = await asyncio.gather(*tasks)

    # Verify all requests succeeded
    assert len(results) == 3
    for assistant_msg, state in results:
        assert isinstance(assistant_msg, AssistantMessage)
        assert state.context_id is not None
