# Quickstart: A2A Protocol Integration

**Feature**: A2A Protocol Integration for tau2-bench
**Branch**: `001-a2a-integration`
**Status**: Implementation Guide

This guide shows how to use the A2A protocol integration to evaluate remote agents with tau2-bench.

---

## Prerequisites

### Python Environment
```bash
# Python 3.10+ required
python --version  # Should be >= 3.10

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### Install Dependencies
```bash
# Install tau2-bench with A2A support
pip install -e .

# Verify installation
tau2 --version
```

**New Dependencies** (automatically installed):
- `httpx>=0.28.0` - Async HTTP client
- `a2a-sdk[http-server]>=0.3.12` - A2A protocol SDK

---

## Quick Start: Running Your First A2A Benchmark

### 1. Start an A2A Agent (Example)

For testing, you can use a mock A2A agent:

```bash
# Option A: Use Prism mock server (requires npm)
npm install -g @stoplight/prism-cli
prism mock specs/001-a2a-integration/contracts/a2a-message-protocol.yaml --port 8080

# Option B: Use a real A2A agent (if you have one)
# Follow your agent's setup instructions
```

### 2. Run Benchmark with A2A Agent

```bash
# Basic usage: Run airline domain benchmark with A2A agent
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8080

# Expected output:
# [INFO] Discovering A2A agent at http://localhost:8080
# [INFO] Agent card retrieved: Customer Service Agent v1.0.0
# [INFO] Running benchmark tasks...
# [INFO] Task airline_001: PASS (3 tool calls, 2.34s)
# [INFO] Results: 85% pass rate, avg 2.1s per task
```

### 3. With Authentication

```bash
# If your agent requires authentication
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint https://secure-agent.example.com \
  --agent-a2a-auth-token eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Or use environment variable
export A2A_AUTH_TOKEN="your-token-here"
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint https://secure-agent.example.com \
  --agent-a2a-auth-token $A2A_AUTH_TOKEN
```

### 4. Configure Timeout

```bash
# Increase timeout for slow agents (default: 300s)
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8080 \
  --agent-a2a-timeout 600  # 10 minutes
```

---

## Quick Start: Local Agent Test

For quick local testing and development, use the **Nebius agent** - a minimal ADK agent that wraps the Nebius Llama 3.1 8B API.

### Prerequisites

1. **Nebius API Key**: Sign up at https://tokenfactory.nebius.com/
2. **Set Environment Variable**:
   ```bash
   export NEBIUS_API_KEY="your-api-key-here"
   ```

### Option 1: One-Command Test

Run the complete test (starts agent + runs evaluation):

```bash
./specs/001-a2a-integration/scripts/test_simple_agent.sh
```

This will:
1. Start the simple agent on localhost:8001
2. Wait for it to be ready
3. Run a tau2-bench evaluation (mock domain)
4. Display results
5. Clean up automatically

### Option 2: Manual Testing

**Step 1**: Start the agent:
```bash
./specs/001-a2a-integration/scripts/run_simple_agent.sh
```

**Step 2**: In another terminal, run evaluation:
```bash
python -m tau2.cli run \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8001/a2a/simple_nebius_agent \
  --domain mock \
  --num-trials 1
```

**Step 3**: Stop the agent (Ctrl+C in first terminal)

### Option 3: Automated Pytest Tests

Run the complete test suite with automated server management:

```bash
# Run all local agent tests
pytest tests/test_local_eval/ -v

# Run with detailed logging
pytest tests/test_local_eval/ -v -s --log-cli-level=DEBUG

# Run specific test
pytest tests/test_local_eval/test_simple_agent_e2e.py::TestAgentDiscovery::test_agent_card_accessible -v
```

### Verify Agent is Working

Check the agent card:
```bash
curl http://localhost:8001/a2a/simple_nebius_agent/.well-known/agent-card.json | jq
```

Expected output:
```json
{
  "name": "simple_nebius_agent",
  "description": "A simple agent using Nebius Llama 3.1 8B for testing A2A protocol",
  "url": "http://localhost:8001/a2a/simple_nebius_agent",
  "version": "1.0.0",
  "capabilities": {
    "streaming": false
  },
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain"],
  "skills": [...]
}
```

### Test Different Domains

Once the agent is running, test with different tau2-bench domains:

```bash
# Airline domain (more complex)
python -m tau2.cli run \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8001/a2a/simple_nebius_agent \
  --domain airline \
  --num-trials 3

# Retail domain
python -m tau2.cli run \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8001/a2a/simple_nebius_agent \
  --domain retail \
  --num-trials 3
```

### Troubleshooting

**Port already in use:**
```bash
# Check what's using port 8001
lsof -i :8001

# Kill the process
kill $(lsof -t -i:8001)
```

**API key issues:**
```bash
# Verify API key is set
echo $NEBIUS_API_KEY

# Test API key directly
curl https://api.tokenfactory.nebius.com/v1/models \
  -H "Authorization: Bearer $NEBIUS_API_KEY"
```

### Architecture Details

See [Local Test Architecture](testing/local-test-architecture.md) for detailed information about:
- Architecture diagrams
- Component descriptions
- Extension points
- Performance baselines

---

## CLI Options Reference

### Required Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--agent a2a_agent` | Select A2A agent type | `--agent a2a_agent` |
| `--agent-a2a-endpoint URL` | A2A agent base URL | `--agent-a2a-endpoint http://localhost:8080` |

### Optional Flags

| Flag | Description | Default | Example |
|------|-------------|---------|---------|
| `--agent-a2a-auth-token TOKEN` | Bearer token for authentication | None | `--agent-a2a-auth-token eyJhbG...` |
| `--agent-a2a-timeout SECONDS` | Response timeout in seconds | 300 | `--agent-a2a-timeout 600` |

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `A2A_ENDPOINT` | Default agent endpoint | `export A2A_ENDPOINT=http://localhost:8080` |
| `A2A_AUTH_TOKEN` | Default bearer token | `export A2A_AUTH_TOKEN=eyJhbG...` |

---

## Understanding A2A Agent Evaluation

### How It Works

1. **Agent Discovery**
   - tau2-bench fetches `/.well-known/agent-card.json` from agent endpoint
   - Validates capabilities and authentication requirements

2. **Message Translation**
   - tau2 internal messages → A2A protocol messages (JSON-RPC)
   - Tool descriptions sent as text in system instructions
   - Agent responses → tau2 AssistantMessage format

3. **Tool Execution**
   - **Critical**: Tools execute locally in tau2-bench, NOT on remote agent
   - Agent only decides which tools to call (reasoning engine)
   - Tool results sent back to agent for next reasoning step

4. **Session Management**
   - Server-generated `context_id` maintains conversation context
   - Each task evaluation gets fresh session (no state leakage)

### Architecture Diagram

```
┌──────────────┐                      ┌──────────────┐
│  tau2-bench  │                      │  A2A Agent   │
│              │                      │  (Remote)    │
│ ┌──────────┐ │                      │              │
│ │Orchestr- │ │  1. Discover Agent   │              │
│ │  ator    │ ├─────────────────────>│  Agent Card  │
│ └────┬─────┘ │                      │              │
│      │       │  2. Send Message     │              │
│ ┌────▼─────┐ │     (user + tools)   │  ┌────────┐  │
│ │ A2AAgent │ ├─────────────────────>│  │Reasoning│ │
│ │          │ │                      │  └────┬───┘  │
│ │ ┌──────┐ │ │  3. Tool Call Req    │       │      │
│ │ │Trans-│ │ │<─────────────────────┤   ToolCall   │
│ │ │lator │ │ │                      │   Decision   │
│ │ └──────┘ │ │                      │              │
│ └────┬─────┘ │                      └──────────────┘
│      │       │
│ ┌────▼─────┐ │
│ │Tool Exec-│ │  4. Execute Locally
│ │  (Local) │ │     (NOT on agent!)
│ └────┬─────┘ │
│      │       │
│ ┌────▼─────┐ │  5. Send Tool Result
│ │ A2AAgent │ ├─────────────────────>│
│ └──────────┘ │                      │
└──────────────┘                      └──────────────┘
```

---

## Example: Running Airline Domain Benchmark

### Full Example with Metrics

```bash
# Run airline benchmark with detailed metrics
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8080 \
  --agent-a2a-timeout 300 \
  --output-dir results/a2a-airline \
  --verbose

# Output directory structure:
# results/a2a-airline/
# ├── trajectories/       # Task execution traces
# ├── metrics.json        # Evaluation metrics + A2A protocol metrics
# └── summary.txt         # Human-readable summary
```

### Metrics Output

`metrics.json` includes A2A-specific metrics:

```json
{
  "agent_type": "a2a_agent",
  "domain": "airline",
  "pass_rate": 0.85,
  "avg_task_time_s": 2.34,
  "a2a_protocol_metrics": {
    "total_requests": 15,
    "total_tokens": 12450,
    "total_latency_ms": 4567.89,
    "avg_latency_ms": 304.53,
    "error_count": 0,
    "requests": [
      {
        "request_id": "req-uuid-1",
        "endpoint": "http://localhost:8080",
        "status_code": 200,
        "latency_ms": 345.67,
        "input_tokens": 523,
        "output_tokens": 178,
        "context_id": "ctx-abc123",
        "timestamp": "2025-11-23T10:30:45.123Z"
      }
    ]
  }
}
```

---

## Example: Comparing A2A vs LLM Agent

### Run Both Agents on Same Task

```bash
# Run LLM agent (baseline)
tau2 run airline \
  --agent llm_agent \
  --agent-llm claude-3-5-sonnet-20241022 \
  --output-dir results/llm-airline

# Run A2A agent
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8080 \
  --output-dir results/a2a-airline

# Compare results
python -m tau2.scripts.compare_results \
  results/llm-airline/metrics.json \
  results/a2a-airline/metrics.json
```

### Expected Comparison Output

```
Comparison: llm_agent vs a2a_agent
==================================

Pass Rate:
  llm_agent:  87.5%
  a2a_agent:  85.0%
  Difference: -2.5%

Avg Task Time:
  llm_agent:  2.1s
  a2a_agent:  2.3s
  Overhead:   +9.5%

Token Usage:
  llm_agent:  11,200 tokens
  a2a_agent:  12,450 tokens (+11.2%)

Protocol Overhead:
  a2a_agent:  304ms avg latency per request
  Network:    ~4.5s total overhead (15 requests)
```

---

## Troubleshooting

### Agent Discovery Fails

**Error**: `A2AError: Agent discovery failed: 404 Not Found`

**Solution**: Verify agent exposes `/.well-known/agent-card.json`:
```bash
curl http://localhost:8080/.well-known/agent-card.json
# Should return JSON with agent metadata
```

### Authentication Error

**Error**: `A2AError: Unauthorized (401)`

**Solution**: Provide bearer token:
```bash
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint https://agent.example.com \
  --agent-a2a-auth-token YOUR_TOKEN_HERE
```

### Timeout Error

**Error**: `A2AError: Agent response timeout after 300s`

**Solutions**:
1. Increase timeout: `--agent-a2a-timeout 600`
2. Check agent health: `curl http://localhost:8080/.well-known/agent-card.json`
3. Check network connectivity: `ping agent.example.com`

### Connection Refused

**Error**: `A2AError: Cannot reach A2A agent: Connection refused`

**Solutions**:
1. Verify agent is running: `curl http://localhost:8080`
2. Check endpoint URL: ensure `http://` or `https://` prefix
3. Check firewall/network access

### Tool Execution Error

**Error**: `Tool 'search_flights' not found`

**Cause**: Agent requested tool that doesn't exist in domain

**Solution**: Verify task domain matches agent capabilities:
```bash
# List available domains and their tools
tau2 list domains

# Run correct domain
tau2 run airline --agent a2a_agent --agent-a2a-endpoint http://localhost:8080
```

---

## Advanced Usage

### Custom Agent Card Validation

```python
from tau2.a2a.client import A2AClient
from tau2.a2a.models import A2AConfig

# Create client
config = A2AConfig(
    endpoint="http://localhost:8080",
    timeout=300
)
client = A2AClient(config)

# Discover agent
agent_card = await client.discover_agent()

# Validate capabilities
if not agent_card.capabilities.streaming:
    print("Warning: Agent does not support streaming")

if agent_card.security:
    print(f"Authentication required: {agent_card.security}")
```

### Custom Metrics Collection

```python
from tau2.a2a.agent import A2AAgent
from tau2.a2a.models import A2AConfig

# Create agent with custom config
config = A2AConfig(
    endpoint="http://localhost:8080",
    auth_token="your-token",
    timeout=600
)
agent = A2AAgent(config)

# Access metrics after evaluation
metrics = agent.get_protocol_metrics()
print(f"Total requests: {metrics.total_requests}")
print(f"Avg latency: {metrics.avg_latency_ms}ms")
print(f"Total tokens: {metrics.total_tokens}")
```

---

## Next Steps

### 1. Read Implementation Details
- [Data Model](data-model.md) - Entity definitions and relationships
- [Research](research.md) - A2A protocol patterns and best practices
- [Contracts](contracts/) - API specifications

### 2. Explore Test Suite
```bash
# Run A2A integration tests
pytest tests/test_a2a/ -v

# Run with coverage
pytest tests/test_a2a/ --cov=tau2.a2a --cov-report=html
```

### 3. Implement Custom A2A Agent

See [A2A Protocol Documentation](https://a2a-protocol.org/latest/specification/) for:
- Agent card format
- Message protocol
- Tool calling conventions

### 4. Contribute

Found a bug or want to improve A2A support?
1. Open an issue: https://github.com/tau2-bench/tau2-bench/issues
2. Submit a PR: Follow CONTRIBUTING.md guidelines
3. Join discussions: https://github.com/tau2-bench/tau2-bench/discussions

---

## FAQ

### Q: Can I use A2A agents for all domains?
**A**: Yes! A2A agents work with all tau2-bench domains (airline, retail, telecom, etc.). The agent receives tool descriptions via the message protocol.

### Q: Do tools execute on the remote agent?
**A**: No! Tools always execute locally in tau2-bench. The A2A agent only decides which tools to call (reasoning). This ensures evaluation reproducibility and security.

### Q: Can I run A2A agents offline?
**A**: No, A2A requires network connectivity to the remote agent. For offline evaluation, use local LLM agents (`llm_agent`, `llm_solo_agent`).

### Q: How do I estimate costs for A2A agents?
**A**: Check `metrics.json` → `a2a_protocol_metrics.total_tokens`. Multiply by your agent's pricing:
```
cost = (input_tokens * $input_price) + (output_tokens * $output_price)
```

### Q: Can I use multiple A2A agents in one evaluation?
**A**: Not directly in Phase 1. Each benchmark run evaluates one agent. To compare multiple A2A agents, run separate evaluations and compare results.

### Q: Does backward compatibility mean existing agents still work?
**A**: Yes! All existing tau2-bench agents (LLM agents, gym agents) continue working unchanged. A2A is purely additive.

---

## Resources

### Documentation
- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [tau2-bench Documentation](https://github.com/tau2-bench/tau2-bench)
- [Feature Specification](spec.md)

### Examples
- [Mock A2A Agent Setup](contracts/README.md#mock-server-setup)
- [Integration Tests](../../tests/test_a2a/)
- [Sample Agent Cards](contracts/agent-discovery.yaml#examples)

### Support
- GitHub Issues: https://github.com/tau2-bench/tau2-bench/issues
- Discussions: https://github.com/tau2-bench/tau2-bench/discussions
- A2A Protocol Discord: https://discord.gg/a2a-protocol
