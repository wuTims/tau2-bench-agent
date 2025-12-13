"""
Test backward compatibility for LLM agent functionality.

Verifies that existing LLM agent behavior is unchanged after A2A integration.
"""

import pytest
from unittest.mock import Mock, patch

from tau2.agent.llm_agent import LLMAgent, LLMAgentState
from tau2.data_model.message import UserMessage, AssistantMessage, ToolMessage, SystemMessage
from tau2.environment.tool import Tool


@pytest.fixture
def mock_tools():
    """Create mock tools for testing"""
    tool1 = Mock(spec=Tool)
    tool1.name = "search_flights"
    tool1.description = "Search for available flights"
    tool1.parameters = {
        "type": "object",
        "properties": {
            "origin": {"type": "string"},
            "destination": {"type": "string"}
        },
        "required": ["origin", "destination"]
    }

    tool2 = Mock(spec=Tool)
    tool2.name = "book_flight"
    tool2.description = "Book a flight"
    tool2.parameters = {
        "type": "object",
        "properties": {
            "flight_id": {"type": "string"}
        },
        "required": ["flight_id"]
    }

    return [tool1, tool2]


@pytest.fixture
def llm_agent(mock_tools):
    """Create an LLMAgent instance"""
    domain_policy = "Help users with flight bookings according to airline policies."
    return LLMAgent(
        tools=mock_tools,
        domain_policy=domain_policy,
        llm="gpt-4o",
        llm_args={"temperature": 0.7}
    )


class TestLLMAgentInterface:
    """Test that LLMAgent interface is unchanged"""

    def test_agent_initialization(self, llm_agent, mock_tools):
        """Test LLMAgent can be initialized with existing parameters"""
        assert llm_agent.llm == "gpt-4o"
        assert llm_agent.llm_args == {"temperature": 0.7}
        assert llm_agent.tools == mock_tools
        assert "airline policies" in llm_agent.domain_policy

    def test_get_init_state_returns_valid_state(self, llm_agent):
        """Test get_init_state returns LLMAgentState with system messages"""
        state = llm_agent.get_init_state()

        assert isinstance(state, LLMAgentState)
        assert len(state.system_messages) == 1
        assert state.system_messages[0].role == "system"
        assert "customer service agent" in state.system_messages[0].content.lower()
        assert len(state.messages) == 0

    def test_get_init_state_with_message_history(self, llm_agent):
        """Test get_init_state with existing message history"""
        history = [
            UserMessage(role="user", content="I need help"),
            AssistantMessage(role="assistant", content="How can I help you?", tool_calls=[])
        ]

        state = llm_agent.get_init_state(message_history=history)

        assert isinstance(state, LLMAgentState)
        assert len(state.messages) == 2
        assert state.messages[0].content == "I need help"
        assert state.messages[1].content == "How can I help you?"

    def test_system_prompt_includes_domain_policy(self, llm_agent):
        """Test system prompt includes domain policy"""
        system_prompt = llm_agent.system_prompt

        assert "airline policies" in system_prompt
        assert "customer service agent" in system_prompt
        assert "policy" in system_prompt.lower()

    @patch("tau2.agent.llm_agent.generate")
    def test_generate_next_message_signature(self, mock_generate, llm_agent):
        """Test generate_next_message has correct signature and return type"""
        # Mock LLM response
        mock_generate.return_value = AssistantMessage(
            role="assistant",
            content="I can help you search for flights.",
            tool_calls=[]
        )

        # Create state
        state = llm_agent.get_init_state()

        # Create user message
        user_msg = UserMessage(role="user", content="I need to book a flight")

        # Call generate_next_message
        response, new_state = llm_agent.generate_next_message(user_msg, state)

        # Verify return types
        assert isinstance(response, AssistantMessage)
        assert isinstance(new_state, LLMAgentState)
        assert response.content == "I can help you search for flights."

    def test_stop_method_exists(self, llm_agent):
        """Test stop method exists and can be called"""
        state = llm_agent.get_init_state()
        user_msg = UserMessage(role="user", content="Goodbye")

        # Should not raise exception
        llm_agent.stop(message=user_msg, state=state)

    def test_is_stop_method_exists(self, llm_agent):
        """Test is_stop class method exists"""
        msg = AssistantMessage(role="assistant", content="Goodbye!", tool_calls=[])
        result = llm_agent.is_stop(msg)

        # Default behavior: returns False
        assert result is False

    def test_set_seed_method_exists(self, llm_agent):
        """Test set_seed method exists and can be called"""
        # Should not raise exception (may log warning)
        llm_agent.set_seed(42)


class TestLLMAgentBackwardCompatibility:
    """Test specific backward compatibility scenarios"""

    @patch("tau2.agent.llm_agent.generate")
    def test_tool_calling_flow_unchanged(self, mock_generate, llm_agent):
        """Test that tool calling flow works as before"""
        # Mock LLM response with tool call
        from tau2.data_model.message import ToolCall

        tool_call = ToolCall(
            id="call_123",
            name="search_flights",
            arguments={"origin": "NYC", "destination": "LAX"}
        )
        mock_generate.return_value = AssistantMessage(
            role="assistant",
            content="",
            tool_calls=[tool_call]
        )

        state = llm_agent.get_init_state()
        user_msg = UserMessage(role="user", content="Find flights from NYC to LAX")

        response, new_state = llm_agent.generate_next_message(user_msg, state)

        # Verify tool call structure is preserved
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "search_flights"
        assert response.tool_calls[0].arguments["origin"] == "NYC"
        assert response.tool_calls[0].arguments["destination"] == "LAX"

    @patch("tau2.agent.llm_agent.generate")
    def test_multi_turn_conversation_flow(self, mock_generate, llm_agent):
        """Test multi-turn conversation works as expected"""
        # Turn 1: User asks question
        mock_generate.return_value = AssistantMessage(
            role="assistant",
            content="I can help you with that.",
            tool_calls=[]
        )

        state = llm_agent.get_init_state()
        msg1 = UserMessage(role="user", content="Hello")
        response1, state = llm_agent.generate_next_message(msg1, state)

        # Turn 2: User follows up
        mock_generate.return_value = AssistantMessage(
            role="assistant",
            content="Sure, let me search.",
            tool_calls=[]
        )

        msg2 = UserMessage(role="user", content="I need a flight")
        response2, state = llm_agent.generate_next_message(msg2, state)

        # Verify conversation history is preserved
        assert len(state.messages) >= 2
        assert response2.content == "Sure, let me search."

    def test_agent_state_structure_unchanged(self, llm_agent):
        """Test that LLMAgentState structure is unchanged"""
        state = llm_agent.get_init_state()

        # Verify state has expected attributes
        assert hasattr(state, "system_messages")
        assert hasattr(state, "messages")
        assert isinstance(state.system_messages, list)
        assert isinstance(state.messages, list)

        # Verify state is serializable (Pydantic model)
        state_dict = state.model_dump()
        assert "system_messages" in state_dict
        assert "messages" in state_dict


class TestLLMAgentRegistry:
    """Test LLM agent registry integration is unchanged"""

    def test_llm_agent_registered_in_registry(self):
        """Test LLMAgent is still registered in registry"""
        from tau2.registry import registry

        agents = registry.get_agents()
        assert "llm_agent" in agents
        assert "llm_agent_gt" in agents
        assert "llm_agent_solo" in agents

    def test_llm_agent_constructor_accessible(self):
        """Test LLMAgent constructor can be retrieved from registry"""
        from tau2.registry import registry

        agent_class = registry.get_agent_constructor("llm_agent")
        assert agent_class == LLMAgent

    def test_llm_agent_can_be_instantiated_from_registry(self, mock_tools):
        """Test LLMAgent can be instantiated via registry"""
        from tau2.registry import registry

        agent_class = registry.get_agent_constructor("llm_agent")
        agent = agent_class(
            tools=mock_tools,
            domain_policy="Test policy",
            llm="gpt-4o",
            llm_args={}
        )

        assert isinstance(agent, LLMAgent)
        assert agent.llm == "gpt-4o"


class TestLLMAgentNoBreakingChanges:
    """Test that no breaking changes were introduced"""

    def test_llm_agent_imports_unchanged(self):
        """Test that LLMAgent imports work as before"""
        # These imports should work without errors
        from tau2.agent.llm_agent import LLMAgent, LLMAgentState, LLMGTAgent, LLMSoloAgent
        from tau2.agent.base import BaseAgent, LocalAgent, ValidAgentInputMessage

        assert LLMAgent is not None
        assert LLMAgentState is not None
        assert BaseAgent is not None

    def test_llm_agent_inherits_from_local_agent(self):
        """Test LLMAgent still inherits from LocalAgent"""
        from tau2.agent.base import LocalAgent

        assert issubclass(LLMAgent, LocalAgent)

    def test_llm_agent_constructor_signature_unchanged(self, mock_tools):
        """Test LLMAgent constructor accepts same parameters"""
        # Test with all parameters
        agent1 = LLMAgent(
            tools=mock_tools,
            domain_policy="Policy",
            llm="gpt-4o",
            llm_args={"temperature": 0.7}
        )
        assert agent1 is not None

        # Test with optional parameters as None
        agent2 = LLMAgent(
            tools=mock_tools,
            domain_policy="Policy",
            llm=None,
            llm_args=None
        )
        assert agent2 is not None

        # Test with minimal parameters
        agent3 = LLMAgent(
            tools=mock_tools,
            domain_policy="Policy"
        )
        assert agent3 is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])