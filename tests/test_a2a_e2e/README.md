# A2A End-to-End Tests

## Purpose

These tests verify the complete A2A integration by testing real network communication between components. Unlike the mock-based tests in `test_a2a_client/` and `test_adk_server/`, these tests require actual running services.

**These tests are NOT run by default** - they are opt-in only and require explicit execution.

## What E2E Tests Cover

1. **Real HTTP Communication**: Tests actual network calls between A2AAgent (client) and ADK agent (server)
2. **Protocol Compliance**: Verifies A2A protocol implementation over real HTTP
3. **Full Integration Flow**: Tests complete request/response cycles including:
   - Agent discovery (`.well-known/agent-card.json`)
   - Message sending (JSON-RPC 2.0 `message/send`)
   - Tool execution flow
   - Context persistence across turns
4. **Real tau2-bench Integration**: Tests actual evaluation flow with `tau2.run.run_domain()`

## Prerequisites

### 1. Install Dependencies

Ensure all A2A dependencies are installed:

```bash
# Install the project with all dependencies
pip install -e .

# Or specifically install A2A dependencies
pip install "httpx>=0.28.0" "a2a-sdk[http-server]>=0.3.12" "google-adk[a2a]"
```

### 2. ADK Agent Implementation

The E2E tests require the ADK agent in `tau2_agent/` to be properly configured with:
- Agent definition (`tau2_agent/agent.py`)
- Tools (ListDomains, RunTau2Evaluation, etc.)
- Valid agent card configuration

## Running E2E Tests

### Option 1: Manual Server (Recommended for Development)

Start the ADK server manually in one terminal and run tests in another:

```bash
# Terminal 1: Start ADK server
cd /workspaces/agent-beats/tau2-bench-agent
python -m google.adk.dev_server --agents-dir=./tau2_agent --port=8000

# Terminal 2: Run E2E tests
pytest -m a2a_e2e -v
```

**Benefits**:
- Better control over server lifecycle
- Easier debugging with server logs visible
- Can inspect server state between test runs

### Option 2: Automatic Server (Fixture-Managed)

Let the test fixtures automatically start and stop the server:

```bash
pytest -m a2a_e2e -v
```

The `adk_server` fixture in `conftest.py` will:
1. Start the ADK server as a subprocess on port 8000
2. Wait for the server to be ready
3. Run the tests
4. Clean up and stop the server

**Note**: This option requires proper subprocess management and may be less reliable for debugging.

## Test Files

### `test_client_to_server.py`

Tests the full client-to-server communication flow:

- `test_e2e_agent_discovery_real`: Real agent card discovery over HTTP
- `test_e2e_message_send_real`: Real message/send JSON-RPC calls
- `test_e2e_full_conversation_flow`: Multi-turn conversation with context persistence
- `test_e2e_tool_call_execution`: Complete tool call cycle (request → execute → result)

### `test_evaluation_flow.py`

Tests the real tau2-bench evaluation integration:

- `test_e2e_run_evaluation_minimal`: Minimal real evaluation with `tau2.run.run_domain()`
- `test_e2e_evaluation_request_via_a2a_client`: Tests requesting evaluation through A2AClient
- `test_complete_a2a_loop`: Tests complete A2A loop (tau2 as both service and client)

## Test Markers

All tests in this directory are marked with `@pytest.mark.a2a_e2e`:

```python
@pytest.mark.a2a_e2e
async def test_e2e_agent_discovery_real(a2a_client_to_local):
    """Test real agent discovery over HTTP"""
    ...
```

## Test Commands Cheat Sheet

```bash
# Run only E2E tests (explicit opt-in)
pytest -m a2a_e2e

# Run E2E tests with verbose output
pytest -m a2a_e2e -v

# Run E2E tests with detailed output
pytest -m a2a_e2e -vv

# Run specific E2E test file
pytest tests/test_a2a_e2e/test_client_to_server.py -m a2a_e2e

# Run specific E2E test
pytest tests/test_a2a_e2e/test_client_to_server.py::test_e2e_agent_discovery_real -m a2a_e2e

# Run all tests including E2E (override default exclusion)
pytest -m ""

# Run default tests (excludes E2E automatically)
pytest
```

## Troubleshooting

### Port Already in Use

If you get "Address already in use" errors:

```bash
# Find process using port 8000
lsof -i :8000

# Kill the process
kill -9 <PID>
```

### Server Not Starting

Check that ADK is properly installed:

```bash
python -c "from google.adk.cli.fast_api import get_fast_api_app; print('ADK installed')"
```

### Tests Timing Out

If tests timeout waiting for the server:

1. Check server logs for errors
2. Verify port 8000 is accessible: `curl http://localhost:8000/.well-known/agent-card.json`
3. Increase timeout in fixtures (see `conftest.py`)

### Import Errors

Ensure the project is installed in editable mode:

```bash
pip install -e .
```

## CI/CD Integration

### GitHub Actions Example

```yaml
# .github/workflows/test-e2e.yml
name: E2E Tests

on:
  workflow_dispatch:  # Manual trigger only
  schedule:
    - cron: '0 2 * * *'  # Nightly at 2 AM

jobs:
  e2e:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: pip install -e .

      - name: Start ADK server
        run: |
          python -m google.adk.dev_server \
            --agents-dir=./tau2_agent \
            --port=8000 &
          sleep 5  # Wait for server startup

      - name: Run E2E tests
        run: pytest -m a2a_e2e -v
```

### Makefile Integration

See the main `Makefile` for convenience targets:

```bash
make test-e2e    # Run E2E tests only
make test-all    # Run all tests including E2E
```

## Best Practices

1. **Always run mock tests first**: E2E tests are slower, so validate with mock tests first
2. **Keep E2E tests focused**: Test end-to-end flows, not individual unit behaviors
3. **Use realistic scenarios**: E2E tests should reflect real-world usage
4. **Clean state between tests**: Use fixtures to ensure test isolation
5. **Document assumptions**: Clearly document what services must be running

## Development Workflow

Typical workflow when developing A2A features:

```bash
# 1. Run fast mock tests during development
pytest tests/test_a2a_client/ tests/test_adk_server/ -v

# 2. Once mock tests pass, start server for E2E validation
python -m google.adk.dev_server --agents-dir=./tau2_agent --port=8000

# 3. Run E2E tests in another terminal
pytest -m a2a_e2e -v

# 4. Before committing, run full test suite
pytest -m ""
```

## Contributing

When adding new E2E tests:

1. Mark the test with `@pytest.mark.a2a_e2e`
2. Use fixtures from `conftest.py` for server/client setup
3. Document what the test validates
4. Ensure the test cleans up resources (use async context managers)
5. Add the test to this README's test file descriptions
