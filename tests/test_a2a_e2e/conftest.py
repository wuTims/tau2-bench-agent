"""
Fixtures for A2A end-to-end tests.

These fixtures provide real server instances and clients for E2E testing.
"""

import asyncio
import subprocess
import time
from pathlib import Path

import httpx
import pytest

from tau2.a2a.client import A2AClient
from tau2.a2a.models import A2AConfig

# Test configuration
ADK_SERVER_HOST = "localhost"
ADK_SERVER_PORT = 8000
ADK_SERVER_BASE_URL = f"http://{ADK_SERVER_HOST}:{ADK_SERVER_PORT}"
ADK_AGENT_DIR = "./tau2_agent"
SERVER_STARTUP_TIMEOUT = 30  # seconds
SERVER_HEALTH_CHECK_INTERVAL = 0.5  # seconds


@pytest.fixture(scope="session")
def adk_server():
    """
    Start ADK server as subprocess for the test session.

    This fixture starts the ADK dev server and waits for it to be ready.
    The server is automatically stopped when tests complete.

    Yields:
        str: The base URL of the running server
    """
    # Check if server is already running
    try:
        response = httpx.get(
            f"{ADK_SERVER_BASE_URL}/.well-known/agent-card.json", timeout=2
        )
        if response.status_code == 200:
            pytest.skip(
                f"ADK server already running on {ADK_SERVER_BASE_URL}. "
                "Using existing server."
            )
            yield ADK_SERVER_BASE_URL
            return
    except (httpx.ConnectError, httpx.TimeoutException):
        pass  # Server not running, we'll start it

    # Ensure agent directory exists
    agent_dir = Path(ADK_AGENT_DIR)
    if not agent_dir.exists():
        pytest.fail(f"Agent directory not found: {agent_dir.absolute()}")

    # Start ADK server
    cmd = [
        "python",
        "-m",
        "google.adk.dev_server",
        f"--agents-dir={ADK_AGENT_DIR}",
        f"--port={ADK_SERVER_PORT}",
        "--host=localhost",
    ]

    try:
        # Start server process
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        # Wait for server to be ready
        start_time = time.time()
        server_ready = False

        while time.time() - start_time < SERVER_STARTUP_TIMEOUT:
            try:
                response = httpx.get(
                    f"{ADK_SERVER_BASE_URL}/.well-known/agent-card.json", timeout=2
                )
                if response.status_code == 200:
                    server_ready = True
                    break
            except (httpx.ConnectError, httpx.TimeoutException):
                pass

            # Check if process crashed
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                pytest.fail(
                    f"ADK server process terminated unexpectedly.\n"
                    f"STDOUT: {stdout}\n"
                    f"STDERR: {stderr}"
                )

            time.sleep(SERVER_HEALTH_CHECK_INTERVAL)

        if not server_ready:
            process.terminate()
            stdout, stderr = process.communicate(timeout=5)
            pytest.fail(
                f"ADK server did not become ready within {SERVER_STARTUP_TIMEOUT}s.\n"
                f"STDOUT: {stdout}\n"
                f"STDERR: {stderr}"
            )

        yield ADK_SERVER_BASE_URL

    finally:
        # Cleanup: stop server
        if process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait()


@pytest.fixture
async def a2a_client_to_local(adk_server):
    """
    Create A2AClient connected to local ADK server.

    This fixture provides a real A2AClient that communicates with
    the local ADK server over HTTP.

    Args:
        adk_server: Base URL of running ADK server

    Yields:
        A2AClient: Client connected to local server
    """
    config = A2AConfig(
        endpoint=adk_server,
        timeout=30,
    )

    # Create httpx client
    async with httpx.AsyncClient(timeout=30.0) as http_client:
        client = A2AClient(config, http_client=http_client)

        # Verify connection by discovering agent
        try:
            await client.discover_agent()
        except Exception as e:
            pytest.fail(f"Failed to connect to ADK server at {adk_server}: {e}")

        yield client


@pytest.fixture
def sample_test_tools():
    """
    Create sample tools for testing E2E flows.

    These tools match the structure expected by tau2-bench domains
    but are simpler for testing purposes.

    Returns:
        list[Tool]: Sample tool instances
    """
    from tau2.environment.tool import Tool

    def search_flights(origin: str, destination: str, date: str) -> dict:
        """Search for available flights."""
        return {
            "flights": [
                {
                    "id": "TEST123",
                    "origin": origin,
                    "destination": destination,
                    "date": date,
                    "price": 350.0,
                    "departure": "10:00",
                    "arrival": "14:00",
                }
            ]
        }

    def book_flight(flight_id: str, passenger_name: str, passenger_email: str) -> dict:
        """Book a specific flight."""
        return {
            "booking_id": f"BK-{flight_id}-001",
            "confirmation": f"Booked flight {flight_id} for {passenger_name}",
            "status": "confirmed",
        }

    def cancel_booking(booking_id: str) -> dict:
        """Cancel a flight booking."""
        return {"status": "cancelled", "booking_id": booking_id, "refund_amount": 350.0}

    return [
        Tool(search_flights),
        Tool(book_flight),
        Tool(cancel_booking),
    ]


@pytest.fixture
async def verify_server_health(adk_server):
    """
    Verify ADK server health before each test.

    This fixture ensures the server is responding correctly
    before running each E2E test.

    Args:
        adk_server: Base URL of running ADK server
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        try:
            # Check agent card endpoint
            response = await client.get(
                f"{adk_server}/.well-known/agent-card.json"
            )
            assert response.status_code == 200, (
                f"Server health check failed: {response.status_code}"
            )

            # Verify agent card structure
            card = response.json()
            assert "name" in card, "Agent card missing required 'name' field"
            assert "url" in card, "Agent card missing required 'url' field"

        except Exception as e:
            pytest.fail(f"Server health check failed: {e}")

    return


@pytest.fixture
def mock_evaluation_agent_endpoint():
    """
    Provide a mock agent endpoint for evaluation testing.

    For E2E tests that involve running evaluations, we need an agent
    endpoint to evaluate against. This can be:
    1. A mock endpoint (for faster tests)
    2. The local ADK server itself (for full circular flow testing)

    Returns:
        str: Agent endpoint URL
    """
    # Option 1: Return local server (circular flow)
    return f"{ADK_SERVER_BASE_URL}"

    # Option 2: Return a mock endpoint (would need separate mock server)
    # return "http://localhost:8001"


@pytest.fixture
async def wait_for_async():
    """
    Helper fixture for waiting on async operations in tests.

    Provides utilities for async test operations.
    """

    async def wait_with_timeout(coro, timeout=30):
        """Wait for coroutine with timeout."""
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except asyncio.TimeoutError:
            pytest.fail(f"Operation timed out after {timeout}s")

    return wait_with_timeout
