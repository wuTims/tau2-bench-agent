# A2A Protocol Contracts

This directory contains API contract specifications for the A2A (Agent-to-Agent) protocol integration in tau2-bench.

## Contracts

### 1. a2a-message-protocol.yaml

**Purpose**: Defines the JSON-RPC 2.0 message exchange protocol.

**Endpoint**: `POST /message/send`

**Key Operations**:
- Send user messages to A2A agent
- Receive agent responses (text or tool call requests)
- Maintain session context via context_id
- Handle tool result messages

**Message Flow**:
```
tau2-bench                          A2A Agent
    │                                   │
    │  POST /message/send (role=user)  │
    ├──────────────────────────────────>│
    │                                   │
    │  Response (role=agent)            │
    │<──────────────────────────────────┤
    │                                   │
    │  POST /message/send (tool result) │
    ├──────────────────────────────────>│
    │                                   │
```

**Authentication**: Bearer token (optional, agent-dependent)

**Content Types**:
- Request: `application/json` (JSON-RPC 2.0)
- Response: `application/json` (JSON-RPC 2.0)

---

### 2. agent-discovery.yaml

**Purpose**: Defines the agent capability discovery endpoint.

**Endpoint**: `GET /.well-known/agent-card.json`

**Key Information**:
- Agent name, description, version
- Capabilities (streaming, push notifications)
- Authentication requirements (security schemes)
- Skills metadata (informational)

**Discovery Flow**:
```
tau2-bench                          A2A Agent
    │                                   │
    │  GET /.well-known/agent-card.json │
    ├──────────────────────────────────>│
    │                                   │
    │  Agent Card (JSON)                │
    │<──────────────────────────────────┤
    │                                   │
    │  [Extract capabilities, auth]     │
    │                                   │
    │  POST /message/send               │
    ├──────────────────────────────────>│
    │                                   │
```

**Authentication**: Typically unauthenticated per spec, but may require auth

**Content Type**: `application/json`

---

## Usage in tau2-bench

### Contract Validation

These contracts serve as:
1. **Documentation**: Reference for A2A protocol implementation
2. **Testing**: Test cases can be derived from examples
3. **Validation**: Response schemas for integration testing

### Code Generation (Optional)

While these contracts are primarily for documentation, they could be used for:
- **Mock server generation** (e.g., Prism) for testing
- **Client code generation** (e.g., OpenAPI Generator)
- **Request/response validation** (e.g., openapi-core)

For tau2-bench Phase 1, manual implementation is preferred to minimize dependencies, but these contracts provide the specification.

---

## Contract Compliance

### A2A Protocol Specification

These contracts follow the A2A protocol specification (DRAFT v1.0):
- Message structure (messageId, role, parts, contextId)
- JSON-RPC 2.0 transport layer
- Agent card format (/.well-known/agent-card.json)

### Deviations from Spec

**None** - Full compliance with A2A protocol specification.

**Phase 1 Limitations**:
- Streaming responses not implemented (capabilities.streaming ignored)
- FilePart not supported (only TextPart and DataPart)
- OAuth2 flows not supported (only bearer token auth)

---

## Testing with Contracts

### Mock Server Setup

Use Prism to run mock A2A agent:

```bash
# Install Prism
npm install -g @stoplight/prism-cli

# Run mock server for message protocol
prism mock contracts/a2a-message-protocol.yaml --port 8080

# Test discovery endpoint
curl http://localhost:8080/.well-known/agent-card.json

# Test message send
curl -X POST http://localhost:8080/message/send \
  -H "Content-Type: application/json" \
  -d @examples/user-message-request.json
```

### Integration Testing

Use contracts in integration tests:

```python
import httpx
import yaml

# Load contract examples
with open("contracts/a2a-message-protocol.yaml") as f:
    contract = yaml.safe_load(f)
    examples = contract["paths"]["/message/send"]["post"]["responses"]["200"]["content"]["application/json"]["examples"]

# Use examples in tests
def test_agent_text_response(mock_transport):
    expected_response = examples["agentTextResponse"]["value"]
    # ... test implementation
```

---

## References

- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [JSON-RPC 2.0 Specification](https://www.jsonrpc.org/specification)
- [RFC 8615 - Well-Known URIs](https://datatracker.ietf.org/doc/html/rfc8615)
- [OpenAPI 3.0 Specification](https://swagger.io/specification/)
