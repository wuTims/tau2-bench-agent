# Data Model: A2A Protocol Integration

**Feature**: A2A Protocol Integration
**Branch**: `001-a2a-integration`
**Date**: 2025-11-23

## Overview

This document defines the data entities for A2A protocol integration in tau2-bench. Entities are organized by domain: configuration, protocol messages, agent state, discovery metadata, and observability metrics.

---

## Entity Diagram

```
┌─────────────┐          ┌──────────────┐
│  A2AConfig  │─────────>│  A2AClient   │
└─────────────┘          └──────────────┘
                                │
                                │ sends/receives
                                ▼
                         ┌─────────────┐
                         │ A2AMessage  │
                         └─────────────┘
                                │
                    ┌───────────┴───────────┐
                    ▼                       ▼
            ┌──────────────┐        ┌──────────────┐
            │ MessagePart  │        │  AgentCard   │
            └──────────────┘        └──────────────┘
                    │
        ┌───────────┼───────────┐
        ▼           ▼           ▼
    TextPart    DataPart    FilePart


┌──────────────┐          ┌─────────────────┐
│  A2AAgent    │─────────>│  A2AAgentState  │
└──────────────┘          └─────────────────┘
       │                          │
       │                          │ contains
       ▼                          ▼
┌──────────────────┐      ┌──────────────┐
│ ProtocolMetrics  │      │ context_id   │
└──────────────────┘      └──────────────┘
```

---

## 1. Configuration Domain

### A2AConfig

**Purpose**: Configuration bundle for A2A agent connection and behavior.

**Fields**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `endpoint` | `str` | Yes | - | Base URL of A2A agent (e.g., "https://agent.example.com") |
| `auth_token` | `Optional[str]` | No | `None` | Bearer token for authentication |
| `timeout` | `int` | No | `300` | Read timeout in seconds for agent responses |
| `verify_ssl` | `bool` | No | `True` | Whether to verify SSL certificates |

**Validation Rules**:
- `endpoint` must be valid HTTP/HTTPS URL
- `endpoint` must NOT end with trailing slash (normalized during initialization)
- `timeout` must be positive integer (> 0)
- `auth_token` if provided must be non-empty string

**Example**:
```python
from dataclasses import dataclass
from typing import Optional

@dataclass
class A2AConfig:
    endpoint: str
    auth_token: Optional[str] = None
    timeout: int = 300
    verify_ssl: bool = True

    def __post_init__(self):
        # Normalize endpoint (remove trailing slash)
        self.endpoint = self.endpoint.rstrip('/')

        # Validate timeout
        if self.timeout <= 0:
            raise ValueError(f"timeout must be positive, got {self.timeout}")

        # Validate URL scheme
        if not self.endpoint.startswith(('http://', 'https://')):
            raise ValueError(f"endpoint must start with http:// or https://, got {self.endpoint}")
```

**CLI Mapping**:
- `--agent-a2a-endpoint` → `endpoint`
- `--agent-a2a-auth-token` → `auth_token`
- `--agent-a2a-timeout` → `timeout`

**Relationships**:
- **Used by**: A2AClient for HTTP client configuration
- **Created from**: CLI arguments in A2AAgent constructor

---

## 2. Protocol Message Domain

### A2AMessage

**Purpose**: Protocol message exchanged between tau2-bench and A2A agent.

**Fields**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `message_id` | `str` | Yes | - | Unique message identifier (UUID) |
| `role` | `Literal["user", "agent"]` | Yes | - | Message sender role |
| `parts` | `list[MessagePart]` | Yes | - | Message content as list of parts |
| `context_id` | `Optional[str]` | No | `None` | Session context identifier |
| `task_id` | `Optional[str]` | No | `None` | Task identifier (A2A server-managed) |
| `metadata` | `Optional[dict]` | No | `None` | Additional structured metadata |

**Validation Rules**:
- `message_id` must be valid UUID string
- `role` must be exactly "user" or "agent"
- `parts` must contain at least one MessagePart
- `context_id` if provided must be non-empty string

**Example**:
```python
from pydantic import BaseModel, Field
from typing import Literal, Optional
from uuid import uuid4

class A2AMessage(BaseModel):
    message_id: str = Field(default_factory=lambda: str(uuid4()))
    role: Literal["user", "agent"]
    parts: list[MessagePart] = Field(min_items=1)
    context_id: Optional[str] = None
    task_id: Optional[str] = None
    metadata: Optional[dict] = None

    class Config:
        # Allow validation to coerce types
        use_enum_values = True
```

**Relationships**:
- **Contains**: MessagePart (one-to-many)
- **Created by**: tau2_to_a2a() translation function
- **Parsed by**: a2a_to_tau2() translation function

**State Transitions**:
1. **Outgoing (tau2 → A2A)**: role="user", context_id from state
2. **Incoming (A2A → tau2)**: role="agent", context_id updated in state

---

### MessagePart

**Purpose**: Content component of A2A message (polymorphic type).

**Part Types**:

#### TextPart
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `text` | `str` | Yes | Plain text content |
| `metadata` | `Optional[dict]` | No | Part-specific metadata |

**Usage**: User messages, system instructions, tool descriptions, tool results

#### DataPart
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `data` | `dict` | Yes | Structured JSON data |
| `metadata` | `Optional[dict]` | No | Part-specific metadata |

**Usage**: Tool call requests, structured responses

#### FilePart (Phase 2+)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `file` | `FileReference` | Yes | File metadata and location |
| `metadata` | `Optional[dict]` | No | Part-specific metadata |

**Usage**: File attachments (out of scope for Phase 1)

**Example**:
```python
from pydantic import BaseModel
from typing import Optional, Union

class TextPart(BaseModel):
    text: str
    metadata: Optional[dict] = None

class DataPart(BaseModel):
    data: dict
    metadata: Optional[dict] = None

class FilePart(BaseModel):
    # Phase 2+
    file: dict  # FileReference structure
    metadata: Optional[dict] = None

# Union type for polymorphic parts
MessagePart = Union[TextPart, DataPart, FilePart]
```

**Validation Rules**:
- Exactly one of {text, data, file} must be present
- `text` if present must be non-empty
- `data` if present must be valid JSON-serializable dict

**Relationships**:
- **Contained by**: A2AMessage (many-to-one)
- **Created from**: tau2 Message content (UserMessage → TextPart, ToolMessage → TextPart)
- **Parsed to**: tau2 AssistantMessage (TextPart → content, DataPart → tool_calls)

---

## 3. Agent State Domain

### A2AAgentState

**Purpose**: Agent execution state for single task evaluation.

**Fields**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `context_id` | `Optional[str]` | No | `None` | Session context identifier from A2A agent |
| `conversation_history` | `list[Message]` | No | `[]` | Full conversation history (tau2 format) |
| `agent_card` | `Optional[AgentCard]` | No | `None` | Cached agent discovery metadata |
| `request_count` | `int` | No | `0` | Number of messages sent in this task |

**Validation Rules**:
- `context_id` initially None, updated from first A2A response
- `conversation_history` includes all messages (user, assistant, tool)
- `request_count` increments on each message send

**Example**:
```python
from dataclasses import dataclass, field
from typing import Optional

@dataclass
class A2AAgentState:
    """State for A2A agent during task evaluation"""
    context_id: Optional[str] = None
    conversation_history: list[Message] = field(default_factory=list)
    agent_card: Optional[AgentCard] = None
    request_count: int = 0
```

**Relationships**:
- **Used by**: A2AAgent (implements BaseAgent[A2AAgentState])
- **Contains**: AgentCard (one-to-one, optional)
- **Updated by**: generate_next_message() method

**State Lifecycle**:
1. **Initialization**: `get_init_state()` returns fresh state (context_id=None)
2. **First message**: Agent response includes context_id → state updated
3. **Subsequent messages**: context_id persisted across turns
4. **Task completion**: State discarded, new task gets fresh state

**Isolation**:
- Each task evaluation gets independent A2AAgentState instance
- No state sharing across concurrent evaluations
- Context IDs scoped to single task

---

## 4. Discovery Metadata Domain

### AgentCard

**Purpose**: Agent capability metadata from /.well-known/agent-card.json.

**Fields**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `name` | `str` | Yes | - | Agent display name |
| `description` | `Optional[str]` | No | `None` | Agent description |
| `url` | `str` | Yes | - | Agent base URL |
| `version` | `Optional[str]` | No | `None` | Agent version string |
| `capabilities` | `AgentCapabilities` | No | `{}` | Agent capabilities (streaming, etc.) |
| `security_schemes` | `Optional[dict]` | No | `None` | Authentication schemes (OpenAPI 3.2 format) |
| `security` | `Optional[list[str]]` | No | `None` | Required security schemes |
| `skills` | `Optional[list[AgentSkill]]` | No | `None` | Agent skills metadata |

**Nested Types**:

#### AgentCapabilities
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `streaming` | `bool` | No | `False` | Supports streaming responses |
| `push_notifications` | `bool` | No | `False` | Supports push notifications |

#### AgentSkill (informational only)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `id` | `str` | Yes | Skill identifier |
| `name` | `str` | Yes | Skill display name |
| `description` | `Optional[str]` | No | Skill description |
| `tags` | `Optional[list[str]]` | No | Skill categorization tags |

**Example**:
```python
from pydantic import BaseModel
from typing import Optional

class AgentCapabilities(BaseModel):
    streaming: bool = False
    push_notifications: bool = False

class AgentSkill(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    tags: Optional[list[str]] = None

class AgentCard(BaseModel):
    name: str
    url: str
    description: Optional[str] = None
    version: Optional[str] = None
    capabilities: AgentCapabilities = AgentCapabilities()
    security_schemes: Optional[dict] = None
    security: Optional[list[str]] = None
    skills: Optional[list[AgentSkill]] = None
```

**Validation Rules**:
- `name` must be non-empty string
- `url` must be valid HTTP/HTTPS URL
- `capabilities.streaming` used to select SendMessage vs SendStreamingMessage (Phase 2+)

**Relationships**:
- **Fetched by**: A2AClient.discover_agent()
- **Cached in**: A2AAgentState.agent_card
- **Used for**: Capability detection, auth requirements

---

## 5. Observability Domain

### ProtocolMetrics

**Purpose**: Performance measurements for A2A protocol interactions.

**Fields**:
| Field | Type | Required | Default | Description |
|-------|------|----------|---------|-------------|
| `request_id` | `str` | Yes | - | Unique request identifier |
| `endpoint` | `str` | Yes | - | A2A agent endpoint |
| `method` | `str` | Yes | - | HTTP method (POST) |
| `status_code` | `Optional[int]` | No | `None` | HTTP status code (None if request failed) |
| `latency_ms` | `float` | Yes | - | Total request latency in milliseconds |
| `input_tokens` | `Optional[int]` | No | `None` | Tokens in request message |
| `output_tokens` | `Optional[int]` | No | `None` | Tokens in response message |
| `context_id` | `Optional[str]` | No | `None` | Session context identifier |
| `error` | `Optional[str]` | No | `None` | Error message if request failed |
| `timestamp` | `str` | Yes | - | ISO 8601 timestamp |

**Aggregated Metrics** (computed post-run):
| Metric | Type | Description |
|--------|------|-------------|
| `total_requests` | `int` | Total A2A requests in evaluation |
| `total_tokens` | `int` | Sum of input + output tokens |
| `total_latency_ms` | `float` | Sum of all request latencies |
| `avg_latency_ms` | `float` | Mean request latency |
| `error_count` | `int` | Number of failed requests |
| `estimated_cost_usd` | `float` | Token cost estimate (if pricing available) |

**Example**:
```python
from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProtocolMetrics(BaseModel):
    request_id: str
    endpoint: str
    method: str
    status_code: Optional[int] = None
    latency_ms: float
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    context_id: Optional[str] = None
    error: Optional[str] = None
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())

    def to_dict(self) -> dict:
        """JSON-serializable dict for export"""
        return self.dict(exclude_none=True)
```

**Validation Rules**:
- `latency_ms` must be non-negative
- `status_code` if present must be valid HTTP status (100-599)
- `input_tokens`, `output_tokens` if present must be non-negative
- `error` should only be present if request failed

**Relationships**:
- **Created by**: A2AClient after each request
- **Logged via**: loguru structured logging
- **Exported to**: JSON metrics file post-evaluation

**Collection Points**:
1. **Before request**: Start timer, count input tokens
2. **After response**: Stop timer, count output tokens, record status
3. **On error**: Record error message, partial metrics

**Export Format**:
```json
{
  "task_id": "airline_001",
  "agent_type": "a2a_agent",
  "protocol_metrics": [
    {
      "request_id": "req-uuid-1",
      "endpoint": "https://agent.example.com",
      "method": "POST",
      "status_code": 200,
      "latency_ms": 1234.56,
      "input_tokens": 456,
      "output_tokens": 123,
      "context_id": "ctx-abc123",
      "timestamp": "2025-11-23T10:30:45.123Z"
    }
  ],
  "summary": {
    "total_requests": 5,
    "total_tokens": 2890,
    "total_latency_ms": 6789.12,
    "avg_latency_ms": 1357.82,
    "error_count": 0
  }
}
```

---

## 6. Tool Calling Domain

### ToolDescriptor

**Purpose**: Text representation of tau2 Tool for A2A agent consumption.

**Fields**:
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | `str` | Yes | Tool function name |
| `description` | `str` | Yes | What the tool does |
| `parameters` | `dict` | Yes | Parameter schema (JSON Schema format) |

**Text Format** (sent as TextPart):
```
<available_tools>
- tool_name(param1: string, param2: number)
  Description: What this tool does
  Parameters:
    - param1 (string, required): Parameter description
    - param2 (number, optional): Parameter description
</available_tools>

To use a tool, respond with JSON: {"tool_call": {"name": "tool_name", "arguments": {"param1": "value"}}}
```

**Example**:
```python
def format_tool_as_text(tool: Tool) -> str:
    """Convert tau2 Tool to text description"""
    lines = [f"- {tool.name}("]

    # Extract parameter signatures
    params = []
    if "properties" in tool.parameters:
        for param_name, param_schema in tool.parameters["properties"].items():
            param_type = param_schema.get("type", "any")
            required = param_name in tool.parameters.get("required", [])
            params.append(f"{param_name}: {param_type}")

    lines[0] += ", ".join(params) + ")"
    lines.append(f"  Description: {tool.description}")

    return "\n".join(lines)
```

**Relationships**:
- **Derived from**: tau2 Tool schema
- **Sent as**: TextPart in A2AMessage
- **Parsed by**: A2A agent (external)

---

### ToolCallRequest (DataPart format)

**Purpose**: Structured format for A2A agent to request tool execution.

**DataPart Structure**:
```json
{
  "tool_call": {
    "name": "tool_name",
    "arguments": {
      "param1": "value1",
      "param2": 123
    }
  }
}
```

**TextPart Embedded Format** (fallback):
```
{"tool_call": {"name": "tool_name", "arguments": {"param1": "value"}}}
```

**Validation Rules**:
- `tool_call.name` must match an available tool
- `tool_call.arguments` must be valid JSON dict
- Arguments must match tool parameter schema (validated by orchestrator)

**Translation to tau2 ToolCall**:
```python
from tau2.data_model import ToolCall

def parse_tool_call(data_part: DataPart) -> ToolCall:
    """Convert A2A DataPart to tau2 ToolCall"""
    tool_data = data_part.data.get("tool_call", {})

    return ToolCall(
        id=str(uuid4()),  # Generate unique ID
        name=tool_data["name"],
        arguments=tool_data["arguments"]
    )
```

---

## Entity Persistence & Lifecycle

### Storage
- **A2AConfig**: In-memory, lifetime = A2AAgent instance
- **A2AMessage**: Transient, created per request/response
- **A2AAgentState**: In-memory, lifetime = single task evaluation
- **AgentCard**: Cached in state after discovery, revalidate on new evaluation
- **ProtocolMetrics**: Logged to file system (JSON), aggregated post-run

### Serialization
- **Pydantic models**: Auto-serialization to/from JSON
- **Metrics export**: JSON Lines format for streaming, JSON array for batch

### Thread Safety
- **A2AClient**: Single-threaded (BaseAgent enforces sequential execution)
- **A2AAgentState**: Task-isolated, no shared state across concurrent evaluations
- **ProtocolMetrics**: Logged synchronously, no race conditions

---

## Data Flow Summary

```
CLI Args
   ↓
A2AConfig → A2AClient
   ↓
discover_agent() → AgentCard → A2AAgentState
   ↓
tau2 Message → tau2_to_a2a() → A2AMessage (role=user)
   ↓
HTTP POST → A2A Agent
   ↓
A2AMessage (role=agent) → a2a_to_tau2() → AssistantMessage
   ↓
Update A2AAgentState (context_id, history)
   ↓
Log ProtocolMetrics → JSON export
```

---

## Implementation Notes

### Dependencies
- **pydantic**: Data validation and serialization
- **uuid**: Message ID generation
- **datetime**: Timestamp generation
- **a2a-sdk**: A2A protocol models (may reuse or wrap)

### Validation Strategy
- **Pydantic validators**: Field-level validation (type, required, format)
- **Custom validators**: Business logic (URL schemes, positive integers)
- **Post-init checks**: Cross-field validation

### Error Handling
- **ValidationError**: Raise on invalid data (catch at agent boundary)
- **A2AError**: Domain exception for protocol errors
- **Logging**: Log all validation failures with context

---

## Open Questions

**Resolved**:
- ✅ Token counting method → Use a2a-sdk built-in or estimate via tokenizer
- ✅ MessagePart polymorphism → Use Pydantic Union types
- ✅ Context ID uniqueness → Server-generated, client persists

**Deferred to Implementation**:
- Token counting implementation (a2a-sdk may provide, otherwise estimate)
- Streaming response handling (Phase 2+)
- FilePart support (Phase 2+)
