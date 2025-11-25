"""
Simple ADK agent that wraps Nebius Llama 3.1 8B API.

This is a minimal example for local testing of A2A protocol integration.
"""

import os
from google.adk.agents import LlmAgent
from google.adk.models.lite_llm import LiteLlm


def create_agent() -> LlmAgent:
    """
    Create a simple ADK agent configured with Nebius Llama 3.1 8B.

    Returns:
        LlmAgent configured to use Nebius API

    Raises:
        ValueError: If NEBIUS_API_KEY is not set
    """
    nebius_key = os.getenv("NEBIUS_API_KEY")
    if not nebius_key:
        raise ValueError(
            "NEBIUS_API_KEY environment variable is required. "
            "Get your key from https://tokenfactory.nebius.com/"
        )

    api_base = os.getenv("NEBIUS_API_BASE", "https://api.tokenfactory.nebius.com/v1/")

    # Create LiteLlm wrapper for Nebius API (OpenAI-compatible)
    llm_model = LiteLlm(
        model="openai/meta-llama/Meta-Llama-3.1-8B-Instruct",
        api_base=api_base,
        api_key=nebius_key,
    )

    # Instruction for tau2-bench compatibility
    # The agent must understand how to read tool descriptions and respond with tool calls
    instruction = """You are a helpful customer service assistant for a telecom company.

When helping customers, you have access to tools that are described in the user's message within <available_tools> tags.

IMPORTANT: To use a tool, you MUST respond with ONLY a JSON object in this exact format:
{"tool_call": {"name": "tool_name", "arguments": {"param1": "value1"}}}

For example, to check network status:
{"tool_call": {"name": "check_network_status", "arguments": {}}}

Rules:
1. Read the available tools carefully from the user's message
2. When you need information, call the appropriate tool using the JSON format above
3. After receiving tool results, provide helpful guidance to the customer
4. Be polite and professional
5. If no tools are needed, respond with helpful text directly

Always respond with either a tool call JSON or a helpful text message - never leave your response empty."""

    # Create agent with Nebius Llama configuration
    agent = LlmAgent(
        model=llm_model,
        name="simple_nebius_agent",
        description="A customer service agent using Nebius Llama 3.1 8B for tau2-bench evaluation",
        instruction=instruction,
    )

    return agent


# Create the agent instance (used by ADK CLI)
# ADK looks for 'root_agent' by default
root_agent = create_agent()
agent = root_agent  # Alias for backward compatibility


if __name__ == "__main__":
    print("Simple Nebius Agent")
    print(f"Name: {agent.name}")
    print(f"Description: {agent.description}")
    print(f"Model: {agent.model}")
    print("\nTo start the A2A server, run:")
    print("  adk web --a2a simple_nebius_agent/")
