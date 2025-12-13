"""
Regression test suite for backward compatibility.

Compares results before and after A2A integration to ensure identical behavior
when using existing LLM agents.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from copy import deepcopy

from tau2.agent.llm_agent import LLMAgent
from tau2.data_model.message import (
    UserMessage,
    AssistantMessage,
    ToolMessage,
    ToolCall,
)
from tau2.data_model.simulation import RunConfig
from tau2.environment.tool import Tool
from tau2.registry import registry


@pytest.fixture
def mock_tools():
    """Create mock tools"""
    tool = Mock(spec=Tool)
    tool.name = "test_tool"
    tool.description = "Test tool"
    tool.parameters = {"type": "object", "properties": {}}
    return [tool]


@pytest.mark.unit
class TestLLMAgentRegressionBehavior:
    """Test that LLM agent behavior is unchanged"""

    @patch("tau2.agent.llm_agent.generate")
    def test_simple_conversation_unchanged(self, mock_generate, mock_tools):
        """Test simple back-and-forth conversation produces same results"""
        # Mock LLM responses
        responses = [
            AssistantMessage(role="assistant", content="Hello! How can I help?", tool_calls=[]),
            AssistantMessage(role="assistant", content="I can help you with that.", tool_calls=[]),
        ]
        mock_generate.side_effect = responses

        # Create agent
        agent = LLMAgent(
            tools=mock_tools,
            domain_policy="Test policy",
            llm="gpt-4o",
            llm_args={}
        )

        # Execute conversation
        state = agent.get_init_state()
        msg1 = UserMessage(role="user", content="Hello")
        response1, state = agent.generate_next_message(msg1, state)

        msg2 = UserMessage(role="user", content="I need help")
        response2, state = agent.generate_next_message(msg2, state)

        # Verify responses match expected
        assert response1.content == "Hello! How can I help?"
        assert response2.content == "I can help you with that."
        assert len(state.messages) == 4  # 2 user + 2 assistant

    @patch("tau2.agent.llm_agent.generate")
    def test_tool_calling_sequence_unchanged(self, mock_generate, mock_tools):
        """Test tool calling sequence produces same results"""
        # Mock tool call response
        tool_call = ToolCall(
            id="call_1",
            name="test_tool",
            arguments={"param": "value"}
        )
        mock_generate.return_value = AssistantMessage(
            role="assistant",
            content="",
            tool_calls=[tool_call]
        )

        agent = LLMAgent(
            tools=mock_tools,
            domain_policy="Test policy",
            llm="gpt-4o",
            llm_args={}
        )

        state = agent.get_init_state()
        msg = UserMessage(role="user", content="Use the tool")
        response, state = agent.generate_next_message(msg, state)

        # Verify tool call structure unchanged
        assert len(response.tool_calls) == 1
        assert response.tool_calls[0].name == "test_tool"
        assert response.tool_calls[0].arguments == {"param": "value"}

    @patch("tau2.agent.llm_agent.generate")
    def test_message_history_accumulation_unchanged(self, mock_generate, mock_tools):
        """Test message history accumulates correctly"""
        mock_generate.return_value = AssistantMessage(
            role="assistant",
            content="Response",
            tool_calls=[]
        )

        agent = LLMAgent(
            tools=mock_tools,
            domain_policy="Test policy",
            llm="gpt-4o",
            llm_args={}
        )

        # Start with history
        initial_history = [
            UserMessage(role="user", content="Previous message"),
            AssistantMessage(role="assistant", content="Previous response", tool_calls=[]),
        ]
        state = agent.get_init_state(message_history=initial_history)

        # Add new message
        msg = UserMessage(role="user", content="New message")
        response, state = agent.generate_next_message(msg, state)

        # Verify history preserved and extended
        assert len(state.messages) == 4  # 2 initial + 2 new
        assert state.messages[0].content == "Previous message"
        assert state.messages[2].content == "New message"


@pytest.mark.unit
class TestAgentStateRegressionBehavior:
    """Test agent state management is unchanged"""

    def test_init_state_structure_unchanged(self, mock_tools):
        """Test get_init_state returns expected structure"""
        agent = LLMAgent(
            tools=mock_tools,
            domain_policy="Policy",
            llm="gpt-4o",
            llm_args={}
        )

        state = agent.get_init_state()

        # Verify state structure
        assert hasattr(state, "system_messages")
        assert hasattr(state, "messages")
        assert len(state.system_messages) == 1
        assert len(state.messages) == 0

    def test_state_serialization_unchanged(self, mock_tools):
        """Test state can be serialized/deserialized"""
        agent = LLMAgent(
            tools=mock_tools,
            domain_policy="Policy",
            llm="gpt-4o",
            llm_args={}
        )

        state = agent.get_init_state()

        # Serialize and deserialize
        state_dict = state.model_dump()
        from tau2.agent.llm_agent import LLMAgentState
        restored_state = LLMAgentState(**state_dict)

        # Verify restoration
        assert restored_state.system_messages == state.system_messages
        assert restored_state.messages == state.messages


@pytest.mark.unit
class TestRegistryRegressionBehavior:
    """Test registry behavior is unchanged"""

    def test_existing_agents_still_registered(self):
        """Test all pre-A2A agents still registered"""
        agents = registry.get_agents()

        # Pre-A2A agents must be present
        assert "llm_agent" in agents
        assert "llm_agent_gt" in agents
        assert "llm_agent_solo" in agents

    def test_registry_constructor_access_unchanged(self):
        """Test agent constructors accessible via registry"""
        llm_agent_class = registry.get_agent_constructor("llm_agent")
        assert llm_agent_class == LLMAgent

        # Verify instantiation works
        mock_tool = Mock(spec=Tool)
        agent = llm_agent_class(
            tools=[mock_tool],
            domain_policy="Policy",
            llm="gpt-4o",
            llm_args={}
        )
        assert isinstance(agent, LLMAgent)

    def test_registry_info_includes_all_agents(self):
        """Test registry info includes all agents"""
        info = registry.get_info()

        # All agent types should be present
        assert "llm_agent" in info.agents
        assert "a2a_agent" in info.agents  # New agent added

    def test_domain_registration_unchanged(self):
        """Test domain registration unchanged"""
        domains = registry.get_domains()

        # Core domains must be present
        assert "mock" in domains
        assert "airline" in domains
        assert "retail" in domains
        assert "telecom" in domains

    def test_user_registration_unchanged(self):
        """Test user registration unchanged"""
        users = registry.get_users()

        # Core users must be present
        assert "user_simulator" in users
        assert "dummy_user" in users


@pytest.mark.unit
class TestRunConfigRegressionBehavior:
    """Test RunConfig structure is unchanged"""

    def test_run_config_accepts_llm_agent(self):
        """Test RunConfig accepts llm_agent configuration"""
        config = RunConfig(
            domain="mock",
            agent="llm_agent",
            user="user_simulator",
            llm_agent="gpt-4o",
            llm_args_agent={},
            llm_user="gpt-4o",
            llm_args_user={},
            num_trials=1,
            max_steps=50,
            max_errors=10,
        )

        assert config.domain == "mock"
        assert config.agent == "llm_agent"
        assert config.llm_agent == "gpt-4o"

    def test_run_config_serialization_unchanged(self):
        """Test RunConfig can be serialized"""
        config = RunConfig(
            domain="airline",
            agent="llm_agent",
            user="user_simulator",
            llm_agent="gpt-4o",
            llm_args_agent={"temperature": 0.7},
            llm_user="gpt-4o",
            llm_args_user={},
            num_trials=1,
            max_steps=50,
            max_errors=10,
        )

        # Serialize
        config_dict = config.model_dump()

        # Verify structure
        assert config_dict["domain"] == "airline"
        assert config_dict["agent"] == "llm_agent"
        assert config_dict["llm_agent"] == "gpt-4o"


@pytest.mark.unit
class TestMessageFormatRegressionBehavior:
    """Test message format is unchanged"""

    def test_user_message_structure_unchanged(self):
        """Test UserMessage structure unchanged"""
        msg = UserMessage(role="user", content="Hello")

        assert msg.role == "user"
        assert msg.content == "Hello"
        assert hasattr(msg, "is_tool_call")

    def test_assistant_message_structure_unchanged(self):
        """Test AssistantMessage structure unchanged"""
        tool_call = ToolCall(
            id="call_1",
            name="tool",
            arguments={"key": "value"}
        )
        msg = AssistantMessage(
            role="assistant",
            content="Response",
            tool_calls=[tool_call]
        )

        assert msg.role == "assistant"
        assert msg.content == "Response"
        assert len(msg.tool_calls) == 1
        assert msg.tool_calls[0].name == "tool"

    def test_tool_message_structure_unchanged(self):
        """Test ToolMessage structure unchanged"""
        msg = ToolMessage(
            id="call_1",
            role="tool",
            content="Tool result",
            requestor="assistant"
        )

        assert msg.role == "tool"
        assert msg.id == "call_1"
        assert msg.content == "Tool result"
        assert msg.requestor == "assistant"


@pytest.mark.unit
class TestAgentInterfaceRegressionBehavior:
    """Test BaseAgent interface unchanged"""

    def test_base_agent_interface_methods_exist(self):
        """Test BaseAgent interface has required methods"""
        from tau2.agent.base import BaseAgent

        # Check abstract methods exist
        assert hasattr(BaseAgent, "generate_next_message")
        assert hasattr(BaseAgent, "stop")
        assert hasattr(BaseAgent, "get_init_state")
        assert hasattr(BaseAgent, "is_stop")
        assert hasattr(BaseAgent, "set_seed")

    def test_llm_agent_implements_interface(self, mock_tools):
        """Test LLMAgent implements BaseAgent interface"""
        from tau2.agent.base import BaseAgent

        agent = LLMAgent(
            tools=mock_tools,
            domain_policy="Policy",
            llm="gpt-4o",
            llm_args={}
        )

        # Verify interface compliance
        assert isinstance(agent, BaseAgent)
        assert callable(agent.generate_next_message)
        assert callable(agent.stop)
        assert callable(agent.get_init_state)
        assert callable(agent.is_stop)
        assert callable(agent.set_seed)


@pytest.mark.unit
class TestImportRegressionBehavior:
    """Test imports unchanged"""

    def test_core_imports_unchanged(self):
        """Test core imports still work"""
        # These imports should work without errors
        from tau2.agent.llm_agent import LLMAgent, LLMAgentState
        from tau2.agent.base import BaseAgent, LocalAgent, ValidAgentInputMessage
        from tau2.data_model.message import (
            UserMessage,
            AssistantMessage,
            ToolMessage,
            MultiToolMessage,
        )
        from tau2.registry import registry
        from tau2.run import run_domain, get_options

        # Verify imports are not None
        assert LLMAgent is not None
        assert BaseAgent is not None
        assert registry is not None
        assert run_domain is not None

    def test_agent_imports_from_registry(self):
        """Test agents can be imported from registry module"""
        from tau2.registry import registry

        # Should not raise ImportError
        assert registry is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
