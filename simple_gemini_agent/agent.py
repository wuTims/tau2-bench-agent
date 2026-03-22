"""
Simple ADK agent that wraps Google Gemini Flash 2.0 API.

This is a minimal example for local testing of A2A protocol integration.
Uses ADK's native Gemini model for optimal Google Cloud integration.

Authentication is handled automatically by ADK:
- GCP: Uses Application Default Credentials (ADC) via metadata server
- Local: Reads GEMINI_API_KEY or GOOGLE_API_KEY from environment
"""

import os

from google.adk.agents import LlmAgent
from google.adk.models import Gemini


def create_agent() -> LlmAgent:
    """
    Create a simple ADK agent configured with Gemini Flash 2.0.

    Authentication is handled automatically by ADK:
    - GCP: Uses Application Default Credentials (ADC) via metadata server
    - Local: Reads GEMINI_API_KEY or GOOGLE_API_KEY from environment

    Returns:
        LlmAgent configured to use Gemini API
    """
    # Use ADK's native Gemini model
    model = os.getenv("SIMPLE_AGENT_MODEL", "gemini-2.0-flash")

    # Strip 'gemini/' prefix if present - native Gemini uses bare model name
    if model.startswith("gemini/"):
        model = model[7:]

    llm_model = Gemini(model=model)

    instruction = """You are a helpful customer service assistant.

You have access to tools described in <available_tools> tags. You may ONLY call tools that are listed there. Do not invent or guess tool names.

To call a tool, respond with ONLY a JSON object in this exact format:
{"tool_call": {"name": "tool_name", "arguments": {"param1": "value1"}}}

If a tool call fails, re-read the available tools list and either try a different tool or help the customer directly with a text response.

Rules:
1. Only use tools listed in <available_tools> — no other tool names are valid
2. After receiving tool results, provide helpful guidance to the customer
3. If you cannot resolve an issue with the available tools, guide the customer through steps they can take on their end
4. Be polite and professional
5. If no tools are needed, respond with helpful text directly

Always respond with either a tool call JSON or a helpful text message — never leave your response empty."""

    agent = LlmAgent(
        model=llm_model,
        name="simple_gemini_agent",
        description="A customer service agent powered by Gemini",
        instruction=instruction,
    )

    return agent


# Create the agent instance (used by ADK CLI)
# ADK looks for 'root_agent' by default
root_agent = create_agent()
agent = root_agent  # Alias for backward compatibility


if __name__ == "__main__":
    print("Simple Gemini Agent")
    print(f"Name: {agent.name}")
    print(f"Description: {agent.description}")
    print(f"Model: {agent.model}")
    print("\nTo start the A2A server, run:")
    print("  adk web --a2a simple_gemini_agent/")
