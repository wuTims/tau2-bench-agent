"""Message translation utilities between tau2-bench and A2A protocol formats."""

import json
import uuid

from loguru import logger

from tau2.a2a.exceptions import A2AMessageError
from tau2.data_model.message import (
    AssistantMessage,
    ToolCall,
    ToolMessage,
    UserMessage,
)
from tau2.environment.tool import Tool


def format_tools_as_text(tools: list[Tool]) -> str:
    """
    Convert tau2 Tools to text description for A2A agent consumption.

    Args:
        tools: List of tau2 Tool objects

    Returns:
        Text representation of tools in a format A2A agents can understand
    """
    if not tools:
        logger.trace("No tools to format for A2A message")
        return ""

    logger.trace(
        "Formatting tools as text for A2A agent",
        num_tools=len(tools),
        tool_names=[tool.name for tool in tools],
    )

    lines = ["<available_tools>"]

    for tool in tools:
        # Get OpenAI schema format
        schema = tool.openai_schema
        func_schema = schema.get("function", {})
        name = func_schema.get("name", tool.name)
        description = func_schema.get("description", "No description available")
        parameters = func_schema.get("parameters", {})

        # Build parameter signature
        param_parts = []
        properties = parameters.get("properties", {})
        required = parameters.get("required", [])

        for param_name, param_schema in properties.items():
            param_type = param_schema.get("type", "any")
            is_required = param_name in required
            param_parts.append(f"{param_name}: {param_type}")

        # Format tool signature
        signature = f"{name}({', '.join(param_parts)})"
        lines.append(f"- {signature}")
        lines.append(f"  Description: {description}")

        # Add parameter details
        if properties:
            lines.append("  Parameters:")
            for param_name, param_schema in properties.items():
                param_type = param_schema.get("type", "any")
                param_desc = param_schema.get("description", "No description")
                is_required = param_name in required
                required_str = "required" if is_required else "optional"
                lines.append(
                    f"    - {param_name} ({param_type}, {required_str}): {param_desc}"
                )

        lines.append("")  # Empty line between tools

    lines.append("</available_tools>")
    lines.append("")
    lines.append(
        'To use a tool, respond with JSON: {"tool_call": {"name": "tool_name", "arguments": {"param1": "value"}}}'
    )

    tool_text = "\n".join(lines)

    # Debug: Log full tool description sent to A2A agent
    logger.trace(
        "Tool descriptions formatted for A2A agent",
        tool_text_length=len(tool_text),
        tool_text=tool_text,
    )

    return tool_text


def tau2_to_a2a_message_content(
    message: UserMessage | AssistantMessage | ToolMessage,
    tools: list[Tool] | None = None,
) -> str:
    """
    Convert tau2 message to A2A text content.

    Args:
        message: tau2 message object
        tools: Optional list of tools to include in user messages

    Returns:
        Text content for A2A message
    """
    if isinstance(message, UserMessage):
        # User messages: include content and optionally tool descriptions
        content_parts = []
        if message.content:
            content_parts.append(message.content)

        # Add tool descriptions for user messages (system context)
        if tools:
            logger.debug(
                "Including tool descriptions in user message",
                num_tools=len(tools),
            )
            tool_text = format_tools_as_text(tools)
            if tool_text:
                content_parts.append("\n" + tool_text)

        return "\n\n".join(content_parts)

    if isinstance(message, AssistantMessage):
        # Assistant messages: either text content or tool calls
        if message.has_text_content():
            return message.content or ""
        if message.is_tool_call() and message.tool_calls:
            # Convert tool calls to JSON format for A2A
            tool_calls_data = []
            for tool_call in message.tool_calls:
                tool_calls_data.append(
                    {
                        "tool_call": {
                            "id": tool_call.id,
                            "name": tool_call.name,
                            "arguments": tool_call.arguments,
                        }
                    }
                )
            # Return as JSON string
            if len(tool_calls_data) == 1:
                return json.dumps(tool_calls_data[0])
            return json.dumps({"tool_calls": tool_calls_data})
        return ""

    # Tool messages: return the tool output
    prefix = f"Tool result (id={message.id}):"
    if message.error:
        return f"{prefix} ERROR: {message.content or 'Unknown error'}"
    return f"{prefix} {message.content or ''}"


def parse_a2a_tool_calls(content: str) -> list[ToolCall] | None:
    """
    Parse tool calls from A2A agent response content.

    Looks for JSON-formatted tool calls in the response:
    - Single: {"tool_call": {"name": "...", "arguments": {...}}}
    - Multiple: {"tool_calls": [{...}, {...}]}

    Args:
        content: A2A agent response content

    Returns:
        List of ToolCall objects if found, None otherwise
    """
    if not content or not content.strip():
        return None

    try:
        # Try to parse as JSON
        data = json.loads(content.strip())

        # Handle single tool call format
        if "tool_call" in data:
            tool_data = data["tool_call"]
            tool_call = ToolCall(
                id=tool_data.get("id", str(uuid.uuid4())),
                name=tool_data["name"],
                arguments=tool_data["arguments"],
                requestor="assistant",
            )
            return [tool_call]

        # Handle multiple tool calls format
        if "tool_calls" in data:
            tool_calls = []
            for tool_data in data["tool_calls"]:
                if "tool_call" in tool_data:
                    tc = tool_data["tool_call"]
                    tool_call = ToolCall(
                        id=tc.get("id", str(uuid.uuid4())),
                        name=tc["name"],
                        arguments=tc["arguments"],
                        requestor="assistant",
                    )
                    tool_calls.append(tool_call)
            return tool_calls if tool_calls else None

        # Not a tool call, just regular content
        return None

    except json.JSONDecodeError:
        # Not JSON, treat as regular content
        return None
    except (KeyError, TypeError) as e:
        logger.warning(f"Failed to parse tool call from A2A response: {e}")
        msg = f"Invalid tool call format: {e}"
        raise A2AMessageError(msg) from e


def a2a_to_tau2_assistant_message(content: str) -> AssistantMessage:
    """
    Convert A2A agent response content to tau2 AssistantMessage.

    Args:
        content: A2A agent response content

    Returns:
        tau2 AssistantMessage with either text content or tool calls
    """
    # Try to parse tool calls first
    tool_calls = parse_a2a_tool_calls(content)

    if tool_calls:
        # Return AssistantMessage with tool calls
        return AssistantMessage(role="assistant", content=None, tool_calls=tool_calls)

    # Handle empty responses - agent may have returned no content
    if not content or not content.strip():
        logger.warning(
            "A2A agent returned empty content, using fallback message",
            original_content=repr(content),
        )
        content = "I apologize, but I was unable to generate a response. Could you please rephrase your request?"

    # Return AssistantMessage with text content
    return AssistantMessage(role="assistant", content=content, tool_calls=None)
