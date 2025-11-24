# τ-Bench ADK Agent Design

## Overview

This document specifies the architecture for an agentic τ-bench evaluator built with Google ADK that evaluates agents via the A2A protocol.

**Goal**: Create a τ-bench evaluation agent that:
- Accepts evaluation requests from a hosting platform
- Communicates with target agents via A2A protocol
- Executes τ-bench benchmarks and returns results
- Combines deterministic workflow execution with intelligent task routing

## Architecture

### System Topology

```
Platform
   ↓
τ-Bench ADK Agent (Google ADK Workflow Agent)
   ├─→ LLM Sub-agent: TaskSelector
   ├─→ Deterministic: EvaluationRunner (wraps τ-bench CLI)
   └─→ LLM Sub-agent: ResultsInterpreter
         ↓
   A2A Client → Purple Agent (target)
         ↓
   τ-bench Orchestrator
         ↓
   Environment + Evaluator
```

### Component Roles

**Platform**: External system hosting the ADK agent (out of scope for this design)

**τ-Bench ADK Agent**: Google ADK Workflow Agent providing tools for evaluation orchestration

**TaskSelector**: LlmAgent interpreting natural language task selection requests

**EvaluationRunner**: Deterministic wrapper around τ-bench CLI with A2A integration

**ResultsInterpreter**: LlmAgent analyzing results and generating summaries

**A2A Client**: Communication layer for purple agent interaction

**Purple Agent**: Target agent being evaluated (external, A2A-compliant)

## Technology Stack Validation

### Google ADK (Validated)

**BaseAgent** (`google.adk.agents.BaseAgent`)
- Foundation class for all agents
- Extensible via custom `_run_async_impl(ctx: InvocationContext) -> AsyncGenerator[Event, None]` method
- Async generator pattern: yields events from sub-agents or own logic
- State management via `InvocationContext.session.state` (dict-like access)
- InvocationContext provides runtime information including session, state, and conversation history

**LlmAgent** (`google.adk.agents.LlmAgent`)
- Non-deterministic reasoning agent
- Tool integration via `tools` parameter supporting:
  - Plain Python functions (automatically wrapped as FunctionTool)
  - BaseTool instances (custom tool classes)
  - AgentTool instances (for agent delegation)
- Dynamic decision-making based on `instruction` parameter (string or InstructionProvider)
- Agent delegation via `AgentTool` wrapping other BaseAgent instances
- Optional `description` for multi-agent task routing

**Workflow Agents**
- `SequentialAgent`: Execute sub-agents in order
- `ParallelAgent`: Execute sub-agents concurrently
- `LoopAgent`: Repeat sub-agents up to max iterations
- Custom agents: Conditional logic via BaseAgent extension

**Source**: https://google.github.io/adk-docs/agents/

### A2A Protocol (Validated)

**Message Structure**
- **Message**: Communication turn with `role` ("user" or "agent") containing Parts
- **Parts**: TextPart (text content), FilePart (file reference), DataPart (structured data)
- **Context**: Optional server-generated identifier for grouping related tasks
- **Task**: Fundamental unit of work with lifecycle management

**AgentCard Discovery**
- JSON metadata document at `/.well-known/agent-card.json`
- Contains: AgentProvider (identity), AgentCapabilities, SecurityScheme (auth), AgentInterface (transport)
- Enables dynamic discovery without pre-established agreements

**Transport**
- JSON-RPC over HTTP (primary)
- gRPC with Protocol Buffers
- REST-style HTTP+JSON
- Agents must implement at least one transport

**Source**: https://github.com/a2aproject/A2A/blob/main/docs/specification.md

**IMPORTANT: Tool Handling in A2A**
- A2A protocol focuses on **agent-to-agent communication**, NOT agent-to-tool interaction
- Tool calling is handled by MCP (Model Context Protocol), which is complementary to A2A
- A2A agents expose capabilities via **AgentSkill** in AgentCard (not tool definitions)
  - AgentSkill describes what the agent can do (e.g., "route optimization", "flight search")
  - AgentSkill specifies inputModes and outputModes (MIME types like application/json)
  - AgentSkill does NOT provide executable tool definitions
- When an A2A agent needs structured data, it uses **DataPart** with JSON content
- **Critical**: τ-bench tools are executed **locally** by the orchestrator, not by the remote A2A agent
- The A2A agent acts as a reasoning engine that:
  1. Receives context about available tools (as text descriptions in messages)
  2. Decides which tools to call based on the task
  3. Returns tool call requests (via DataPart or embedded JSON in text)
- Tool calls in τ-bench are extracted from agent responses and executed by the local environment
- Tool results are sent back to the A2A agent as ToolMessage for continued reasoning

### τ-Bench (Validated)

**BaseAgent Interface** ([src/tau2/agent/base.py:37-101](src/tau2/agent/base.py#L37-L101))
```python
class BaseAgent(ABC, Generic[AgentState]):
    def generate_next_message(
        self, message: ValidAgentInputMessage, state: AgentState
    ) -> tuple[AssistantMessage, AgentState]:
        """Generate next message from user/tool input"""

    def get_init_state(
        self, message_history: Optional[list[Message]] = None
    ) -> AgentState:
        """Initialize agent state from conversation history"""

    def stop(self, message, state) -> None:
        """Cleanup when simulation ends"""

    @classmethod
    def is_stop(cls, message: AssistantMessage) -> bool:
        """Check if message signals termination"""
```

**Registry System** ([src/tau2/registry.py:83-94](src/tau2/registry.py#L83-L94))
```python
def register_agent(agent_constructor: type[BaseAgent], name: str):
    """Register agent implementation for use in CLI"""
```

**RunConfig Extension** ([src/tau2/data_model/simulation.py:29](src/tau2/data_model/simulation.py#L29))
- Pydantic BaseModel with domain, agent type, task configuration
- Extensible for new agent types via additional fields

**Message Protocol** ([src/tau2/data_model/message.py](src/tau2/data_model/message.py))
- `AssistantMessage`: Agent responses (text or tool_calls, not both)
- `UserMessage`: User inputs
- `ToolMessage`: Tool execution results
- `SystemMessage`: System prompts

**Orchestrator** ([src/tau2/orchestrator/orchestrator.py](src/tau2/orchestrator/orchestrator.py))
- Manages agent ↔ user ↔ environment message loop
- Captures full conversation history in `Simulation` object
- Validates message format (text XOR tool_calls)
- Handles termination conditions

**Evaluator** ([src/tau2/evaluator/](src/tau2/evaluator/))
- Action evaluation: Tool call matching
- Environment evaluation: DB state assertions
- Communication evaluation: Information conveyed to user
- NL assertions: LLM-as-judge criteria checking

## Implementation Design

### Phase 1: A2A Integration Layer

Extend τ-bench to support A2A agents via new `A2AAgent` class.

#### 1.1 A2A Client

**File**: `src/tau2/utils/a2a_client.py`

```python
from dataclasses import dataclass
from typing import Optional, List, Dict, Any
import httpx
from a2a_sdk import A2ACardResolver, A2AClient as A2ASDKClient, Message as A2AMessage

@dataclass
class A2AConfig:
    endpoint: str
    auth_token: Optional[str] = None
    timeout: int = 300

class A2AClient:
    """
    Client for A2A protocol communication.

    Note: Tools are executed LOCALLY by τ-bench orchestrator, not by the remote A2A agent.
    The A2A agent acts as a reasoning engine that decides which tools to call based on
    text descriptions of available tools sent in the context.
    """

    def __init__(self, config: A2AConfig):
        self.config = config
        self.agent_card: Optional[Dict[str, Any]] = None
        self.a2a_client: Optional[A2ASDKClient] = None
        self.context_id: Optional[str] = None
        self.http_client: Optional[httpx.AsyncClient] = None

    async def discover_agent(self) -> Dict[str, Any]:
        """Fetch agent card from /.well-known/agent-card.json"""
        if not self.http_client:
            self.http_client = httpx.AsyncClient(timeout=self.config.timeout)
            if self.config.auth_token:
                self.http_client.headers["Authorization"] = f"Bearer {self.config.auth_token}"

        resolver = A2ACardResolver(
            httpx_client=self.http_client,
            base_url=self.config.endpoint
        )
        self.agent_card = await resolver.get_agent_card()

        # Create A2A client from agent card
        # Note: Verify exact API with a2a-sdk documentation
        self.a2a_client = A2ASDKClient(self.agent_card, httpx_client=self.http_client)

        return self.agent_card

    async def send_message(
        self,
        messages: List[Message],
        tools: Optional[List[Tool]] = None
    ) -> AssistantMessage:
        """
        Send message to A2A agent and return response.

        Args:
            messages: Conversation history from τ-bench
            tools: Available tools (sent as text descriptions, not executable code)

        Returns:
            AssistantMessage with either text content or parsed tool_calls
        """
        if not self.a2a_client:
            await self.discover_agent()

        # Convert τ-bench → A2A (includes tool descriptions as text)
        a2a_message = self._to_a2a(messages, tools, self.context_id)

        # Send and collect response
        last_event = None
        async for event in self.a2a_client.send_message(a2a_message):
            last_event = event

        # Convert A2A → τ-bench (parse tool calls from response)
        return self._from_a2a(last_event)

    def _to_a2a(self, messages, tools, context_id) -> A2AMessage:
        """Convert τ-bench messages to A2A Message with Parts"""
        from tau2.utils.a2a_utils import tau2_to_a2a
        return tau2_to_a2a(messages, tools, context_id)

    def _from_a2a(self, event) -> AssistantMessage:
        """
        Convert A2A response to τ-bench AssistantMessage.

        Parses tool calls from DataPart or text content.
        """
        from tau2.utils.a2a_utils import a2a_to_tau2
        if hasattr(event, 'context_id'):
            self.context_id = event.context_id
        return a2a_to_tau2(event, self.context_id)

    async def close(self):
        """Close HTTP client"""
        if self.http_client:
            await self.http_client.aclose()
```

**Dependencies**: `a2a-sdk[http-server]>=0.3.12`, `httpx>=0.28.0`

#### 1.2 Message Translation

**File**: `src/tau2/utils/a2a_utils.py`

```python
import uuid
from typing import List, Optional
from a2a_sdk import Message as A2AMessage, TextPart, DataPart
from tau2.data_model.message import Message, AssistantMessage, SystemMessage, UserMessage, ToolMessage, ToolCall
from tau2.data_model.tool import Tool

def tau2_to_a2a(
    messages: List[Message],
    tools: Optional[List[Tool]] = None,
    context_id: Optional[str] = None
) -> A2AMessage:
    """
    Convert τ-bench messages to A2A Message format.

    Strategy:
    - System messages prepended to content in <system> tags
    - User/Assistant messages combined as text
    - Tool results included as text
    - Tools included as TEXT descriptions (not executable code)
    - Tool calling convention explained in system instructions

    Note: A2A protocol is for agent-to-agent communication. The remote agent
    doesn't execute tools - it decides which tools to call. Actual execution
    happens locally in τ-bench environment.
    """
    parts = []
    text_parts = []

    # Build conversation history
    for msg in messages:
        if isinstance(msg, SystemMessage):
            text_parts.insert(0, f"<system>\n{msg.content}\n</system>\n")
        elif isinstance(msg, UserMessage):
            text_parts.append(f"User: {msg.content}")
        elif isinstance(msg, AssistantMessage) and msg.content:
            text_parts.append(f"Assistant: {msg.content}")
        elif isinstance(msg, ToolMessage):
            text_parts.append(f"Tool Result ({msg.tool_name}): {msg.content}")

    # Add tool descriptions as text (if first message or tools changed)
    if tools:
        tool_descriptions = ["<available_tools>"]
        for tool in tools:
            tool_descriptions.append(f"- {tool.name}({', '.join(f'{k}: {v.get('type', 'any')}' for k, v in tool.input_schema.get('properties', {}).items())})")
            tool_descriptions.append(f"  {tool.description}")
        tool_descriptions.append("</available_tools>")
        tool_descriptions.append("\nTo use a tool, respond with a JSON object in this format:")
        tool_descriptions.append('{"tool_call": {"name": "tool_name", "arguments": {...}}}')

        text_parts.insert(1 if text_parts and text_parts[0].startswith("<system>") else 0,
                         "\n".join(tool_descriptions))

    # Combine into single TextPart
    if text_parts:
        parts.append(TextPart(text="\n\n".join(text_parts)))

    return A2AMessage(
        message_id=str(uuid.uuid4()),
        role="user",
        parts=parts,
        context_id=context_id,
    )

def a2a_to_tau2(event, context_id: Optional[str]) -> AssistantMessage:
    """
    Convert A2A response to τ-bench AssistantMessage.

    Extracts:
    - TextParts → content (may contain tool call JSON)
    - DataParts with tool_call → structured tool_calls
    - Context ID for session continuity

    Note: Supports two approaches:
    1. Structured: DataPart contains {"tool_call": {"name": "...", "arguments": {...}}}
    2. Embedded JSON: TextPart contains JSON tool call that we parse out
    """
    import json
    import re

    content_parts = []
    tool_calls = []
    raw_data = {"context_id": context_id}
    full_text = ""

    if isinstance(event, A2AMessage):
        raw_data["message_id"] = event.message_id

        for part in event.parts:
            if isinstance(part, TextPart):
                content_parts.append(part.text)
                full_text += part.text + " "
            elif isinstance(part, DataPart):
                data = part.data
                # Check for structured tool call in DataPart
                if isinstance(data, dict) and "tool_call" in data:
                    tc = data["tool_call"]
                    tool_calls.append(ToolCall(
                        id=tc.get("id", f"call_{uuid.uuid4().hex[:24]}"),
                        name=tc["name"],
                        arguments=tc.get("arguments", {}),
                        requestor="assistant"
                    ))

    # If no structured tool calls, try to parse from text
    if not tool_calls and full_text:
        # Look for JSON tool call pattern in text
        json_pattern = r'\{["\']tool_call["\']\s*:\s*\{["\']name["\']\s*:\s*["\']([^"\']+)["\']\s*,\s*["\']arguments["\']\s*:\s*(\{[^}]*\})\s*\}\s*\}'
        matches = re.finditer(json_pattern, full_text, re.DOTALL)

        for match in matches:
            try:
                tool_name = match.group(1)
                args_json = match.group(2)
                arguments = json.loads(args_json)

                tool_calls.append(ToolCall(
                    id=f"call_{uuid.uuid4().hex[:24]}",
                    name=tool_name,
                    arguments=arguments,
                    requestor="assistant"
                ))
                # Remove the tool call JSON from content
                full_text = full_text.replace(match.group(0), "").strip()
            except (json.JSONDecodeError, KeyError):
                # If parsing fails, leave as content
                pass

    # Use cleaned text if we extracted tool calls
    final_content = full_text.strip() if tool_calls else " ".join(content_parts)

    return AssistantMessage(
        role="assistant",
        content=final_content if final_content else None,
        tool_calls=tool_calls if tool_calls else None,
        cost=None,
        usage=None,
        raw_data=raw_data
    )
```

#### 1.3 A2AAgent Implementation

**File**: `src/tau2/agent/a2a_agent.py`

```python
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from tau2.agent.base import BaseAgent, AgentState
from tau2.data_model.message import Message, AssistantMessage, SystemMessage, MultiToolMessage, ValidAgentInputMessage
from tau2.data_model.tool import Tool
from tau2.utils.a2a_client import A2AClient, A2AConfig

@dataclass
class A2AAgentState(AgentState):
    messages: List[Message] = field(default_factory=list)
    system_messages: List[SystemMessage] = field(default_factory=list)
    context_id: Optional[str] = None

class A2AAgent(BaseAgent[A2AAgentState]):
    """
    τ-bench agent implementation using A2A protocol.

    Maintains BaseAgent interface for orchestrator compatibility.
    Wraps async A2A calls in sync interface.
    """

    def __init__(
        self,
        tools: List[Tool],
        domain_policy: str,
        a2a_config: A2AConfig,
    ):
        super().__init__()
        self.tools = tools
        self.domain_policy = domain_policy
        self.client = A2AClient(a2a_config)
        self.system_prompt = self._build_system_prompt(domain_policy)
        self.agent_card = asyncio.run(self.client.discover_agent())

    def _build_system_prompt(self, domain_policy: str) -> str:
        return f"""<instructions>
You are a customer service agent that helps the user according to the <policy>.
In each turn you can either:
- Send a message to the user.
- Make a tool call.
You cannot do both at the same time.
</instructions>
<policy>
{domain_policy}
</policy>"""

    def get_init_state(
        self, message_history: Optional[List[Message]] = None
    ) -> A2AAgentState:
        state = A2AAgentState()
        state.system_messages = [SystemMessage(role="system", content=self.system_prompt)]
        if message_history:
            state.messages = message_history.copy()
        return state

    def generate_next_message(
        self,
        message: ValidAgentInputMessage,
        state: A2AAgentState
    ) -> Tuple[AssistantMessage, A2AAgentState]:
        """Sync wrapper for orchestrator compatibility"""
        return asyncio.run(self._generate_async(message, state))

    async def _generate_async(
        self,
        message: ValidAgentInputMessage,
        state: A2AAgentState
    ) -> Tuple[AssistantMessage, A2AAgentState]:
        """Async A2A communication"""
        if isinstance(message, MultiToolMessage):
            state.messages.extend(message.tool_messages)
        else:
            state.messages.append(message)

        messages = state.system_messages + state.messages
        assistant_message = await self.client.send_message(messages, self.tools)

        if self.client.context_id:
            state.context_id = self.client.context_id

        state.messages.append(assistant_message)
        return assistant_message, state

    def stop(self, message=None, state=None) -> None:
        """Cleanup (no-op for A2A)"""
        pass
```

**Implementation Notes**:

1. **Tool Calling Approaches**: The A2AAgent design supports multiple tool calling patterns:
   - **Structured DataPart**: A2A agent returns `DataPart` with `{"tool_call": {...}}` (cleanest, requires agent cooperation)
   - **Embedded JSON**: Agent embeds tool call JSON in text response (parsed via regex)
   - **Agent-Specific Protocol**: Custom parsing based on specific A2A agent implementation

2. **SDK API Verification**: The exact `a2a-sdk` API should be verified against [google/A2A](https://github.com/google/A2A) repository, as the design assumes `A2AClient` class structure that should be confirmed.

3. **Context ID Management**: The `context_id` is server-generated on first response and must be included in subsequent messages for session continuity.

4. **Synchronous Wrapper**: The `generate_next_message` method wraps async A2A calls with `asyncio.run()` for compatibility with τ-bench's synchronous orchestrator. Consider using `asyncio` event loop management for production.

#### 1.4 CLI Integration

**File**: `src/tau2/cli.py` (additions)

```python
# Add arguments to run_parser (around line 90)
run_parser.add_argument(
    "--agent-a2a-endpoint",
    type=str,
    help="A2A agent endpoint (e.g., http://127.0.0.1:9019)",
)
run_parser.add_argument(
    "--agent-a2a-auth-token",
    type=str,
    help="Bearer token for A2A authentication",
)
run_parser.add_argument(
    "--agent-a2a-timeout",
    type=int,
    default=300,
    help="A2A request timeout in seconds",
)
```

**File**: `src/tau2/run.py` (modifications)

```python
# In run_task() function (around line 440)
if run_config.agent == "a2a_agent":
    from tau2.utils.a2a_client import A2AConfig
    from tau2.agent.a2a_agent import A2AAgent

    a2a_config = A2AConfig(
        endpoint=run_config.a2a_endpoint,
        auth_token=run_config.a2a_auth_token,
        timeout=run_config.a2a_timeout,
    )

    agent = A2AAgent(
        tools=environment.get_tools(),
        domain_policy=environment.get_policy(),
        a2a_config=a2a_config,
    )
else:
    # Existing LLM agent path (unchanged)
    ...
```

**File**: `src/tau2/registry.py` (registration)

```python
from tau2.agent.a2a_agent import A2AAgent

registry.register_agent(A2AAgent, "a2a_agent")
```

#### 1.5 RunConfig Extension

**File**: `src/tau2/data_model/simulation.py` (additions)

```python
@dataclass
class RunConfig(BaseModel):
    # ... existing fields ...

    # A2A Agent Fields
    a2a_endpoint: Optional[str] = None
    a2a_auth_token: Optional[str] = None
    a2a_timeout: int = 300
```

### Phase 2: Google ADK Wrapper Agent

Build ADK agent that wraps τ-bench CLI for platform integration.

#### 2.1 Tool Suite

**File**: `adk_agent/tools.py`

```python
import json
import subprocess
import uuid
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

@dataclass
class EvaluationRun:
    run_id: str
    status: str  # "running", "completed", "failed"
    domain: str
    task_ids: List[str]
    results_path: Optional[str] = None
    error: Optional[str] = None

# In-memory run tracking
_active_runs: Dict[str, EvaluationRun] = {}

def register_agent(endpoint: str, auth_token: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate A2A agent endpoint and fetch agent card.

    Args:
        endpoint: A2A agent HTTP endpoint
        auth_token: Optional bearer token for authentication

    Returns:
        Agent card information
    """
    import httpx
    from a2a_sdk import A2ACardResolver

    async def _discover():
        async with httpx.AsyncClient(timeout=30) as client:
            resolver = A2ACardResolver(httpx_client=client, base_url=endpoint)
            return await resolver.get_agent_card()

    import asyncio
    card = asyncio.run(_discover())

    return {
        "endpoint": endpoint,
        "name": card.get("name", "Unknown"),
        "capabilities": card.get("capabilities", []),
        "validated": True,
    }

def list_tasks(domain: str, split: Optional[str] = "base") -> List[Dict[str, str]]:
    """
    List available tasks for a domain.

    Args:
        domain: Domain name (airline, retail, telecom)
        split: Task split name (default: "base")

    Returns:
        List of task metadata
    """
    from tau2.registry import registry

    task_loader = registry.get_tasks_loader(domain)
    tasks = task_loader(split)

    return [
        {
            "id": task.id,
            "description": str(task.user_scenario.instructions)[:100],
            "domain": domain,
        }
        for task in tasks
    ]

def run_evaluation(
    domain: str,
    a2a_endpoint: str,
    task_ids: Optional[List[str]] = None,
    auth_token: Optional[str] = None,
    max_steps: int = 30,
) -> Dict[str, Any]:
    """
    Execute τ-bench evaluation on A2A agent.

    Args:
        domain: Domain to evaluate (airline, retail, telecom)
        a2a_endpoint: A2A agent endpoint
        task_ids: Optional list of task IDs (default: all tasks)
        auth_token: Optional bearer token
        max_steps: Max conversation turns per task

    Returns:
        Run metadata with run_id for status tracking
    """
    run_id = f"run_{uuid.uuid4().hex[:12]}"
    results_dir = Path(f"results/{run_id}")
    results_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        "tau2", "run", domain,
        "--agent", "a2a_agent",
        "--agent-a2a-endpoint", a2a_endpoint,
        "--max-steps", str(max_steps),
        "--results-dir", str(results_dir),
        "--output-format", "json",
    ]

    if auth_token:
        cmd.extend(["--agent-a2a-auth-token", auth_token])

    if task_ids:
        cmd.extend(["--task-ids", ",".join(task_ids)])

    # Track run
    _active_runs[run_id] = EvaluationRun(
        run_id=run_id,
        status="running",
        domain=domain,
        task_ids=task_ids or [],
    )

    # Execute in background
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)

        if result.returncode == 0:
            _active_runs[run_id].status = "completed"
            _active_runs[run_id].results_path = str(results_dir / "results.json")
        else:
            _active_runs[run_id].status = "failed"
            _active_runs[run_id].error = result.stderr
    except Exception as e:
        _active_runs[run_id].status = "failed"
        _active_runs[run_id].error = str(e)

    return {
        "run_id": run_id,
        "status": _active_runs[run_id].status,
        "results_path": _active_runs[run_id].results_path,
    }

def get_evaluation_status(run_id: str) -> Dict[str, Any]:
    """
    Get status of evaluation run.

    Args:
        run_id: Run identifier from run_evaluation

    Returns:
        Run status and metadata
    """
    if run_id not in _active_runs:
        return {"error": f"Run {run_id} not found"}

    run = _active_runs[run_id]
    return {
        "run_id": run.run_id,
        "status": run.status,
        "domain": run.domain,
        "task_count": len(run.task_ids),
        "results_path": run.results_path,
        "error": run.error,
    }

def get_evaluation_results(run_id: str) -> Dict[str, Any]:
    """
    Retrieve evaluation results.

    Args:
        run_id: Run identifier from run_evaluation

    Returns:
        Full evaluation results with metrics
    """
    if run_id not in _active_runs:
        return {"error": f"Run {run_id} not found"}

    run = _active_runs[run_id]

    if run.status != "completed":
        return {
            "run_id": run_id,
            "status": run.status,
            "error": run.error or "Evaluation not completed",
        }

    with open(run.results_path, 'r') as f:
        results = json.load(f)

    return results
```

#### 2.2 LLM Sub-Agents

**File**: `adk_agent/subagents.py`

```python
from google.adk.agents import LlmAgent

task_selector = LlmAgent(
    name="task_selector",
    model="gemini-2.0-flash",
    instruction="""You are a task selection expert for τ-bench evaluations.

Given:
- User request (natural language)
- Available tasks (list with IDs and descriptions)

Your job:
1. Parse user intent (specific tasks, domain focus, difficulty level, etc.)
2. Filter tasks matching the criteria
3. Return task IDs as JSON array

Output format: {"task_ids": ["task_1", "task_2", ...], "reasoning": "..."}
""",
    description="Intelligently selects τ-bench tasks based on natural language requests",
)

results_interpreter = LlmAgent(
    name="results_interpreter",
    model="gemini-2.0-flash",
    instruction="""You are an evaluation results analyst for τ-bench.

Given:
- Raw evaluation results (JSON with metrics, task outcomes, errors)

Your job:
1. Compute overall pass rate and key statistics
2. Identify failure patterns (common errors, policy violations)
3. Highlight strongest/weakest performance areas
4. Provide actionable recommendations

Output format:
## Summary
- Overall Score: X%
- Tasks Passed: Y/Z
- Domains: [...]

## Key Findings
- [Finding 1]
- [Finding 2]

## Recommendations
- [Recommendation 1]
- [Recommendation 2]
""",
    description="Analyzes τ-bench results and generates human-readable reports",
)
```

#### 2.3 Main ADK Agent

**File**: `adk_agent/agent.py`

```python
from google.adk import Agent
from google.adk.agents import SequentialAgent
from adk_agent.tools import (
    register_agent,
    list_tasks,
    run_evaluation,
    get_evaluation_status,
    get_evaluation_results,
)
from adk_agent.subagents import task_selector, results_interpreter

# Main agent with all tools
tau2_agent = Agent(
    name="tau2_evaluator",
    model="gemini-2.0-flash",
    instruction="""You are the τ-bench evaluation agent.

You help users evaluate AI agents against the τ-bench benchmark suite using the A2A protocol.

Your capabilities:
1. register_agent: Validate A2A agent endpoints
2. list_tasks: Browse available benchmark tasks
3. run_evaluation: Execute evaluations on target agents
4. get_evaluation_status: Check run progress
5. get_evaluation_results: Retrieve results

You can also delegate to:
- task_selector: For intelligent task filtering
- results_interpreter: For result analysis

Workflow:
1. Validate agent endpoint with register_agent
2. If user wants specific tasks, use task_selector or list_tasks
3. Run evaluation with run_evaluation
4. Monitor with get_evaluation_status
5. When complete, use results_interpreter for insights
6. Return formatted results to user

Always provide clear status updates and actionable information.
""",
    tools=[
        register_agent,
        list_tasks,
        run_evaluation,
        get_evaluation_status,
        get_evaluation_results,
        task_selector,  # AgentTool
        results_interpreter,  # AgentTool
    ],
    description="τ-bench evaluation agent for A2A protocol agents",
)
```

## Evaluation Flow

### Message Routing

```
1. Platform → ADK Agent
   Request: "Evaluate agent at http://purple.example.com on airline tasks"

2. ADK Agent → register_agent tool
   Validates endpoint, fetches agent card

3. ADK Agent → task_selector sub-agent
   Input: "airline tasks"
   Output: {"task_ids": ["flight_booking_1", "flight_search_2", ...]}

4. ADK Agent → run_evaluation tool
   Spawns: tau2 run airline --agent a2a_agent --agent-a2a-endpoint http://purple.example.com

5. τ-bench CLI → A2AAgent instance
   Initializes A2A client, discovers agent

6. Orchestrator loop (per task):
   ┌─────────────────────────────────────────┐
   │ A2AAgent.generate_next_message()        │
   │   ↓                                     │
   │ A2AClient.send_message()                │
   │   (converts τ-bench → A2A Message)      │
   │   ↓                                     │
   │ HTTP POST to purple agent               │
   │   (JSON-RPC: tasks/send)                │
   │   ↓                                     │
   │ Purple agent processes with tools       │
   │   (tools defined in DataPart)           │
   │   ↓                                     │
   │ Purple agent returns A2A Message        │
   │   (TextPart or DataPart[tool_calls])    │
   │   ↓                                     │
   │ A2AClient converts → AssistantMessage   │
   │   ↓                                     │
   │ Orchestrator extracts tool_calls        │
   │   ↓                                     │
   │ Environment executes tools locally      │
   │   ↓                                     │
   │ Results → ToolMessage                   │
   │   ↓                                     │
   │ Loop continues until stop condition     │
   └─────────────────────────────────────────┘

7. Evaluator processes task
   - Action matching (expected tool calls)
   - Environment assertions (DB state)
   - Communication evaluation (info conveyed)
   - NL assertions (LLM-as-judge)

8. Metrics aggregation
   Computes pass@k, success rates, costs

9. Results written to results/{run_id}/results.json

10. ADK Agent → get_evaluation_results tool
    Loads JSON results

11. ADK Agent → results_interpreter sub-agent
    Generates natural language summary

12. ADK Agent → Platform
    Returns formatted evaluation report
```

### State Management

**A2A Context Continuity**
- A2AClient stores `context_id` from purple agent responses
- Context ID passed in subsequent messages within same task
- Enables purple agent to maintain session state

**τ-bench State**
- `A2AAgentState` tracks message history per task
- System prompt injected at initialization
- State passed through orchestrator loop
- No state shared across tasks (isolated evaluations)

**ADK Session State**
- Run metadata stored in `_active_runs` dictionary
- Enables status queries during long-running evaluations
- Session state accessible via `ctx.session.state` in custom agents

### Synchronous Execution

**Per-Task Flow**
- Orchestrator runs synchronous message loop
- `A2AAgent.generate_next_message()` wraps async call with `asyncio.run()`
- Purple agent responses awaited before next step
- Evaluation computed after full conversation
- Results returned synchronously to CLI

**Cross-Task Parallelism**
- τ-bench CLI supports `--max-concurrency` flag
- Multiple tasks evaluated concurrently
- Each task runs independent orchestrator instance
- Results aggregated after all tasks complete

## Dependencies

### Python Packages

```toml
[project.dependencies]
# Existing τ-bench dependencies
tau2 = ">=0.1.0"
litellm = ">=1.0.0"
pydantic = ">=2.0.0"

# A2A Integration
a2a-sdk = {version = ">=0.3.12", extras = ["http-server"]}
httpx = ">=0.28.0"

# Google ADK
google-adk = ">=0.1.0"
```

### External Services

**Required**
- Purple agent implementing A2A protocol (target for evaluation)
- LLM API for τ-bench user simulator (e.g., OpenAI, Anthropic)
- LLM API for ADK LlmAgents (Gemini recommended, others supported)

**Optional**
- Platform hosting ADK agent (deployment target)
- A2A authentication service (if purple agent requires auth)

## Testing Strategy

### Unit Tests

```python
# tests/utils/test_a2a_client.py
async def test_discover_agent()
async def test_send_message_with_tools()
async def test_bearer_token_auth()

# tests/utils/test_a2a_utils.py
def test_tau2_to_a2a_with_system_messages()
def test_a2a_to_tau2_with_tool_calls()

# tests/agent/test_a2a_agent.py
async def test_a2a_agent_generate_message()
async def test_a2a_agent_context_persistence()
```

### Integration Tests

```python
# tests/integration/test_a2a_cli.py
def test_run_with_a2a_agent(mock_a2a_server):
    """Test full CLI execution with mock A2A server"""
    result = subprocess.run([
        "tau2", "run", "airline",
        "--agent", "a2a_agent",
        "--agent-a2a-endpoint", "http://localhost:8000",
        "--task-ids", "test_task_1",
    ])
    assert result.returncode == 0
```

### End-to-End Tests

```bash
# Terminal 1: Start purple agent
python examples/purple_agent.py --port 9019

# Terminal 2: Run ADK agent
python -m adk_agent.agent
```

Test cases:
- Basic conversation (no tools)
- Single tool call
- Multi-turn with multiple tool calls
- Error handling (network failure, auth failure)
- Policy compliance validation

## Implementation Roadmap

### Milestone 1: A2A Integration (Days 1-7)
- Implement `A2AClient` class
- Build message translation utilities
- Create `A2AAgent` extending BaseAgent
- Add CLI arguments for A2A configuration
- Register A2AAgent in registry
- Unit tests for A2A layer

**Validation**: `tau2 run airline --agent a2a_agent --agent-a2a-endpoint <url>` successfully evaluates agent

### Milestone 2: ADK Tool Suite (Days 8-10)
- Implement 5 core tools (register, list, run, status, results)
- Create run tracking system
- Integration tests with τ-bench CLI
- Error handling and validation

**Validation**: Tools can orchestrate full evaluation via Python API

### Milestone 3: LLM Sub-Agents (Days 11-13)
- Build `task_selector` LlmAgent
- Build `results_interpreter` LlmAgent
- Test delegation from main agent
- Refine prompts based on test results

**Validation**: Sub-agents correctly filter tasks and analyze results

### Milestone 4: Main ADK Agent (Days 14-15)
- Assemble main agent with all tools and sub-agents
- End-to-end testing with real purple agents
- Documentation and examples
- Deployment preparation

**Validation**: ADK agent successfully evaluates purple agent and returns formatted results

## Success Criteria

**Phase 1 (A2A Integration)**
- A2AAgent implements all BaseAgent methods
- Message conversion maintains semantic equivalence
- CLI accepts A2A parameters
- No regression in existing LLM-based evaluations

**Phase 2 (ADK Wrapper)**
- Tools successfully wrap τ-bench CLI
- Run tracking persists across tool calls
- Error handling provides actionable feedback
- Performance within 2x of direct CLI usage

**Phase 3 (Complete System)**
- End-to-end evaluation completes for all domains
- Results accuracy matches direct τ-bench CLI
- LLM sub-agents improve task selection and reporting
- Platform integration successful (if applicable)

## Architecture Validation Summary

| Component | Technology | Validation Source | Status | Notes |
|-----------|------------|-------------------|--------|-------|
| BaseAgent extension | τ-bench | DeepWiki: sierra-research/tau2-bench | ✓ Validated | Methods: generate_next_message, get_init_state, is_stop, set_seed |
| Registry system | τ-bench | [src/tau2/registry.py:83-94](src/tau2/registry.py#L83-L94) | ✓ Validated | Agent registration via registry.register_agent() |
| Orchestrator | τ-bench | [src/tau2/orchestrator/orchestrator.py](src/tau2/orchestrator/orchestrator.py) | ✓ Validated | Synchronous message loop, calls generate_next_message |
| Evaluator | τ-bench | [src/tau2/evaluator/](src/tau2/evaluator/) | ✓ Validated | Action, environment, communication, NL assertions |
| LlmAgent | Google ADK | DeepWiki: google/adk-python | ✓ Validated | Supports functions, BaseTool, AgentTool as tools |
| BaseAgent._run_async_impl | Google ADK | DeepWiki: google/adk-python | ✓ Validated | Async generator yielding Events, ctx.session.state access |
| Workflow Agents | Google ADK | DeepWiki: google/adk-python | ✓ Validated | SequentialAgent, ParallelAgent, LoopAgent confirmed |
| A2A Message & Parts | A2A Protocol | DeepWiki: google/A2A | ✓ Validated | TextPart, DataPart, FilePart; Message with role and parts |
| A2A Context ID | A2A Protocol | DeepWiki: google/A2A | ✓ Validated | Server-generated, for session continuity |
| A2ACardResolver | A2A SDK | DeepWiki: google/A2A | ✓ Validated | Fetches agent card from /.well-known/agent-card.json |
| A2A Tool Protocol | A2A Protocol | DeepWiki: google/A2A | ⚠️  Clarified | A2A is for agent communication; tools handled by MCP or custom protocol |
| A2AClient API | A2A SDK | `a2a-sdk[http-server]>=0.3.12` | ⚠️  Needs Verification | Exact class structure should be verified with SDK docs |

## Files to Create/Modify

**New Files**
- `src/tau2/utils/a2a_client.py` (A2A communication layer)
- `src/tau2/utils/a2a_utils.py` (message translation)
- `src/tau2/agent/a2a_agent.py` (A2AAgent implementation)
- `adk_agent/tools.py` (ADK tool suite)
- `adk_agent/subagents.py` (LLM sub-agents)
- `adk_agent/agent.py` (main ADK agent)
- `tests/utils/test_a2a_client.py`
- `tests/utils/test_a2a_utils.py`
- `tests/agent/test_a2a_agent.py`
- `tests/integration/test_a2a_cli.py`

**Modified Files**
- `src/tau2/cli.py` (add A2A arguments)
- `src/tau2/run.py` (add A2A agent instantiation)
- `src/tau2/registry.py` (register A2AAgent)
- `src/tau2/data_model/simulation.py` (extend RunConfig)
- `pyproject.toml` (add dependencies)

## Conclusion

This design integrates τ-bench evaluation capabilities with the A2A protocol via a hybrid Google ADK agent architecture. The approach:

1. Extends τ-bench with minimal changes (new agent type)
2. Preserves existing evaluation logic (orchestrator, evaluator unchanged)
3. Wraps τ-bench CLI for platform integration (tool-based access)
4. Leverages LLM agents for intelligent task routing and result interpretation
5. Maintains backward compatibility (existing agents continue to work)

The architecture is validated against official documentation and source code for all three technologies (τ-bench, A2A, Google ADK via DeepWiki queries), ensuring feasibility and correctness.

### Key Implementation Clarifications

Based on validation via DeepWiki MCP queries to the official repositories:

1. **Tool Execution Architecture**:
   - Tools are executed **locally** within τ-bench, not by the remote A2A agent
   - The A2A agent acts as a reasoning engine that requests tool calls
   - Tool descriptions are sent as text in the context, not as executable definitions
   - Tool calls are parsed from A2A responses (DataPart or embedded JSON)

2. **A2A SDK Usage**:
   - Use `A2ACardResolver` to fetch agent cards from `/.well-known/agent-card.json`
   - The exact `A2AClient` API should be verified against the latest `a2a-sdk` documentation
   - Context ID is server-generated and must be persisted for session continuity

3. **ADK Custom Agents**:
   - Custom agents extend `BaseAgent` with `async def _run_async_impl(ctx: InvocationContext) -> AsyncGenerator[Event, None]`
   - Access session state via `ctx.session.state` (dict-like interface)
   - Yield events from sub-agents: `async for event in sub_agent.run_async(ctx): yield event`

4. **Tool Calling Protocol**:
   - A2A protocol does NOT define a standard tool calling convention
   - Implementation should support multiple approaches: structured DataPart, embedded JSON parsing, or agent-specific protocols
   - The design includes both DataPart parsing and regex-based JSON extraction as fallback

### Recommended Implementation Sequence

1. **Phase 1a**: Implement A2A client with agent discovery and basic message sending
2. **Phase 1b**: Implement message translation with text-based tool descriptions
3. **Phase 1c**: Implement tool call parsing (start with DataPart, add JSON parsing as fallback)
4. **Phase 1d**: Integrate A2AAgent with τ-bench BaseAgent interface
5. **Phase 1e**: Test with a simple A2A agent to validate the integration
6. **Phase 2**: Build ADK wrapper agent with tool suite
7. **Phase 3**: Add LLM sub-agents for task selection and results interpretation
8. **Phase 4**: End-to-end testing and refinement
