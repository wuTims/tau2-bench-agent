# Quickstart: A2A Protocol Integration

**Feature**: A2A Protocol Integration for tau2-bench
**Branch**: `001-a2a-integration`
**Status**: Implementation Guide

This guide shows how to use the A2A protocol integration to evaluate remote agents with tau2-bench.

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Quick Start: Local Testing](#quick-start-local-testing) - Test A2A integration locally with Nebius
3. [Quick Start: Remote Agent](#quick-start-remote-agent) - Evaluate a remote A2A agent
4. [CLI Reference](#cli-options-reference)
5. [Understanding A2A Evaluation](#understanding-a2a-agent-evaluation)
6. [Troubleshooting](#troubleshooting)
7. [FAQ](#faq)

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

## Quick Start: Local Testing

This section shows how to test the A2A integration locally using the **simple Nebius agent** - a minimal ADK agent that wraps the Nebius Llama 3.1 8B API.

### Step 1: Get a Nebius API Key

1. Sign up at https://tokenfactory.nebius.com/
2. Get your API key
3. Set the environment variable:
   ```bash
   export NEBIUS_API_KEY="your-api-key-here"
   ```

### Step 2: Choose Your Testing Method

#### Option A: One-Command Test (Recommended for Quick Validation)

Run the complete test (starts agent + runs evaluation on mock domain):

```bash
./specs/001-a2a-integration/scripts/test_simple_agent.sh
```

This will:
1. Start the simple agent on localhost:8001
2. Wait for it to be ready
3. Run a tau2-bench evaluation (mock domain, 1 trial)
4. Display results
5. Clean up automatically

> **Note**: This uses the `mock` domain which is designed for quick validation and doesn't require a user simulator.

#### Option B: Full Domain Evaluation (Recommended for Real Testing)

For proper evaluation on real domains (airline, retail, telecom), use the evaluation script:

```bash
# Telecom domain (default) - 1 trial, 5 tasks
./specs/001-a2a-integration/scripts/eval_domain.sh telecom 1 5

# Airline domain - 1 trial, 5 tasks
./specs/001-a2a-integration/scripts/eval_domain.sh airline 1 5

# All tasks with multiple trials (takes longer)
./specs/001-a2a-integration/scripts/eval_domain.sh retail 3
```

This script:
- Starts the Nebius agent automatically
- Uses Nebius gpt-oss-120b for user simulation (uses same API key)
- Runs tau2-bench evaluation
- Cleans up after completion

#### Option C: Manual Step-by-Step Testing

**Terminal 1** - Start the agent:
```bash
export NEBIUS_API_KEY="your-api-key-here"
./specs/001-a2a-integration/scripts/run_simple_agent.sh
```

**Terminal 2** - Verify agent is running:
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
  }
}
```

**Terminal 2** - Run evaluation:

For **mock domain** (no user LLM needed):
```bash
tau2 run mock \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8001/a2a/simple_nebius_agent \
  --num-trials 1
```

For **real domains** (user LLM required):
```bash
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8001/a2a/simple_nebius_agent \
  --user-llm "openai/openai/gpt-oss-120b" \
  --user-llm-args '{"base_url": "https://api.tokenfactory.nebius.com/v1/", "api_key": "'"$NEBIUS_API_KEY"'"}' \
  --num-trials 1 \
  --num-tasks 5
```

**Terminal 1** - Stop agent: Press `Ctrl+C`

#### Option D: Automated Pytest Tests

Run the complete test suite with automated server management:

```bash
# Run all local agent tests
pytest tests/test_local_eval/ -v

# Run with detailed logging
pytest tests/test_local_eval/ -v -s --log-cli-level=DEBUG

# Run specific test
pytest tests/test_local_eval/test_simple_agent_e2e.py::TestAgentDiscovery::test_agent_card_accessible -v
```

### Troubleshooting Local Setup

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

**Agent logs:**
```bash
# View agent server logs (if running in background)
tail -f /tmp/simple_agent.log

# Or check /tmp/eval_agent.log if using eval_domain.sh
```

---

## Quick Start: Remote Agent

This section shows how to evaluate a remote A2A agent (not running on localhost).

### Understanding the Architecture

tau2-bench has **two independent LLM configurations**:

```
+---------------------------------------------+
|  Agent (what you're testing)                |
+---------------------------------------------+
|  --agent llm_agent                          |
|    --> --agent-llm <model>                  |  <-- Local LLM
|                                             |
|  --agent a2a_agent                          |
|    --> --agent-a2a-endpoint <url>           |  <-- Remote A2A agent
+---------------------------------------------+

+---------------------------------------------+
|  User Simulator (always runs locally)       |
+---------------------------------------------+
|  --user-llm <model>                         |  <-- Independent of agent type
+---------------------------------------------+
```

**Key Point:** When using `a2a_agent`, your remote agent handles reasoning while tau2-bench still runs the user simulator locally using `--user-llm`. This means you **always need to configure a user LLM** for real domains, regardless of agent type.

### Basic A2A Evaluation

```bash
# Evaluate remote A2A agent with Claude Haiku user simulator
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint https://your-agent.example.com \
  --user-llm claude-3-haiku-20240307
```

### With Authentication

```bash
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint https://secure-agent.example.com \
  --agent-a2a-auth-token YOUR_TOKEN_HERE \
  --user-llm claude-3-haiku-20240307
```

Or use environment variable:
```bash
export A2A_AUTH_TOKEN="your-token-here"
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint https://secure-agent.example.com \
  --agent-a2a-auth-token $A2A_AUTH_TOKEN \
  --user-llm claude-3-haiku-20240307
```

### Configure Timeout for Slow Agents

```bash
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint https://your-agent.example.com \
  --agent-a2a-timeout 600 \
  --user-llm claude-3-haiku-20240307
```

### Choosing Your User LLM

| Model | Cost | Best For |
|-------|------|----------|
| `claude-3-haiku-20240307` | $ | **Recommended**: Reliable, cost-effective baseline |
| `openai/openai/gpt-oss-120b` | $ | Cost-effective with Nebius (requires API key) |
| `claude-3-5-sonnet-20241022` | $$$ | More sophisticated user behavior testing |

### Complete Example: Full Evaluation

```bash
# Run complete evaluation on all domains with A2A agent
tau2 run retail \
  --agent a2a_agent \
  --agent-a2a-endpoint https://your-agent.example.com \
  --user-llm claude-3-haiku-20240307 \
  --num-trials 4

tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint https://your-agent.example.com \
  --user-llm claude-3-haiku-20240307 \
  --num-trials 4

tau2 run telecom \
  --agent a2a_agent \
  --agent-a2a-endpoint https://your-agent.example.com \
  --user-llm claude-3-haiku-20240307 \
  --num-trials 4
```

---

## CLI Options Reference

### Required Flags

| Flag | Description | Example |
|------|-------------|---------|
| `--agent a2a_agent` | Select A2A agent type | `--agent a2a_agent` |
| `--agent-a2a-endpoint URL` | A2A agent base URL | `--agent-a2a-endpoint http://localhost:8080` |
| `--user-llm MODEL` | User simulator model (for real domains) | `--user-llm claude-3-haiku-20240307` |

### Optional Flags

| Flag | Description | Default | Example |
|------|-------------|---------|---------|
| `--agent-a2a-auth-token TOKEN` | Bearer token for authentication | None | `--agent-a2a-auth-token eyJhbG...` |
| `--agent-a2a-timeout SECONDS` | Response timeout in seconds | 300 | `--agent-a2a-timeout 600` |
| `--a2a-debug` | Enable A2A debug logging | False | `--a2a-debug` |
| `--num-trials N` | Trials per task | 1 | `--num-trials 3` |
| `--num-tasks N` | Limit number of tasks | All | `--num-tasks 5` |

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEBIUS_API_KEY` | Nebius API key (for local testing) | `export NEBIUS_API_KEY=your-key` |
| `A2A_ENDPOINT` | Default agent endpoint | `export A2A_ENDPOINT=http://localhost:8080` |
| `A2A_AUTH_TOKEN` | Default bearer token | `export A2A_AUTH_TOKEN=eyJhbG...` |

---

## Understanding A2A Agent Evaluation

### How It Works

1. **Agent Discovery**
   - tau2-bench fetches `/.well-known/agent-card.json` from agent endpoint
   - Validates capabilities and authentication requirements

2. **Message Translation**
   - tau2 internal messages -> A2A protocol messages (JSON-RPC)
   - Tool descriptions sent as text in system instructions
   - Agent responses -> tau2 AssistantMessage format

3. **Tool Execution**
   - **Critical**: Tools execute locally in tau2-bench, NOT on remote agent
   - Agent only decides which tools to call (reasoning engine)
   - Tool results sent back to agent for next reasoning step

4. **Session Management**
   - Server-generated `context_id` maintains conversation context
   - Each task evaluation gets fresh session (no state leakage)

### Architecture Diagram

```
+--------------+                      +--------------+
|  tau2-bench  |                      |  A2A Agent   |
|              |                      |  (Remote)    |
| +----------+ |                      |              |
| |Orchestr- | |  1. Discover Agent   |              |
| |  ator    | +--------------------->|  Agent Card  |
| +----+-----+ |                      |              |
|      |       |  2. Send Message     |              |
| +----v-----+ |     (user + tools)   |  +--------+  |
| | A2AAgent | +--------------------->|  |Reasoning|  |
| |          | |                      |  +----+---+  |
| | +------+ | |  3. Tool Call Req    |       |      |
| | |Trans-| | |<---------------------+   ToolCall   |
| | |lator | | |                      |   Decision   |
| | +------+ | |                      |              |
| +----+-----+ |                      +--------------+
|      |       |
| +----v-----+ |
| |Tool Exec-| |  4. Execute Locally
| |  (Local) | |     (NOT on agent!)
| +----+-----+ |
|      |       |
| +----v-----+ |  5. Send Tool Result
| | A2AAgent | +--------------------->|
| +----------+ |                      |
+--------------+                      +--------------+
```

---

## Example: Comparing A2A vs LLM Agent

### Run Both Agents on Same Task

```bash
# Run LLM agent (baseline)
tau2 run airline \
  --agent llm_agent \
  --agent-llm claude-3-5-sonnet-20241022 \
  --user-llm claude-3-haiku-20240307 \
  --save-to results/llm-airline

# Run A2A agent
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8080 \
  --user-llm claude-3-haiku-20240307 \
  --save-to results/a2a-airline
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
  --agent-a2a-auth-token YOUR_TOKEN_HERE \
  --user-llm claude-3-haiku-20240307
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
# List available domains
tau2 domain --list

# Run correct domain
tau2 run airline \
  --agent a2a_agent \
  --agent-a2a-endpoint http://localhost:8080 \
  --user-llm claude-3-haiku-20240307
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

## FAQ

### Q: Can I use A2A agents for all domains?
**A**: Yes! A2A agents work with all tau2-bench domains (airline, retail, telecom, etc.). The agent receives tool descriptions via the message protocol.

### Q: Do tools execute on the remote agent?
**A**: No! Tools always execute locally in tau2-bench. The A2A agent only decides which tools to call (reasoning). This ensures evaluation reproducibility and security.

### Q: Why do I need a user LLM for A2A agents?
**A**: The user simulator runs independently of the agent. It simulates customer behavior in conversations. The `mock` domain is an exception - it's designed for quick validation and doesn't require user simulation.

### Q: Can I run A2A agents offline?
**A**: No, A2A requires network connectivity to the remote agent. For offline evaluation, use local LLM agents (`llm_agent`, `llm_solo_agent`).

### Q: How do I estimate costs for A2A agents?
**A**: Check `metrics.json` -> `a2a_protocol_metrics.total_tokens`. Multiply by your agent's pricing:
```
cost = (input_tokens * $input_price) + (output_tokens * $output_price)
```

### Q: Can I use multiple A2A agents in one evaluation?
**A**: Not directly. Each benchmark run evaluates one agent. To compare multiple A2A agents, run separate evaluations and compare results.

### Q: Does backward compatibility mean existing agents still work?
**A**: Yes! All existing tau2-bench agents (LLM agents, gym agents) continue working unchanged. A2A is purely additive.

---

## Next Steps

### 1. Read Implementation Details
- [Data Model](data-model.md) - Entity definitions and relationships
- [Research](research.md) - A2A protocol patterns and best practices
- [Local Test Architecture](testing/local-test-architecture.md) - Detailed architecture diagrams
- [Domain Evaluation Guide](testing/local-test-eval-guide.md) - Full domain evaluation workflows

### 2. Explore Test Suite
```bash
# Run A2A integration tests
pytest tests/test_a2a/ -v

# Run local agent tests
pytest tests/test_local_eval/ -v
```

### 3. Implement Custom A2A Agent

See [A2A Protocol Documentation](https://a2a-protocol.org/latest/specification/) for:
- Agent card format
- Message protocol
- Tool calling conventions

### 4. Contribute

Found a bug or want to improve A2A support?
1. Open an issue: https://github.com/sierra-research/tau2-bench/issues
2. Submit a PR: Follow CONTRIBUTING.md guidelines

---

## Resources

### Documentation
- [A2A Protocol Specification](https://a2a-protocol.org/latest/specification/)
- [tau2-bench Documentation](https://github.com/sierra-research/tau2-bench)
- [Feature Specification](spec.md)

### Examples
- [Simple Nebius Agent](../../simple_nebius_agent/README.md) - Minimal ADK agent for local testing
- [Integration Tests](../../tests/test_a2a/)

### Support
- GitHub Issues: https://github.com/sierra-research/tau2-bench/issues
