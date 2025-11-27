#!/usr/bin/env python3
"""
Platform Simulation Script

Simulates a platform that:
1. Maintains a registry of agents
2. Communicates with tau2_agent (evaluator) via A2A
3. tau2_agent executes evaluations and returns results
4. Platform displays results

Architecture:
    ┌─────────────────────────────────────────────────────────────────┐
    │                        Platform (this script)                    │
    │  ┌──────────────────────────────────────────────────────────┐  │
    │  │                   Agent Registry                          │  │
    │  │  ┌──────────────────┐  ┌──────────────────────────────┐  │  │
    │  │  │   tau2_agent     │  │   simple_nebius_agent        │  │  │
    │  │  │   (evaluator)    │  │   (evaluatee)                │  │  │
    │  │  │   Port: 8001     │  │   Port: 8001                 │  │  │
    │  │  └──────────────────┘  └──────────────────────────────┘  │  │
    │  └──────────────────────────────────────────────────────────┘  │
    │                                                                  │
    │  1. Platform sends A2A message to tau2_agent                    │
    │  2. tau2_agent executes tool internally (model-agnostic)        │
    │  3. tau2_agent returns evaluation results via A2A               │
    │  4. Platform displays results                                   │
    └─────────────────────────────────────────────────────────────────┘

tau2_agent is model-agnostic - it handles both:
- Native function calling (Gemini, GPT-4, Claude)
- Text-based tool calls (Qwen, Llama, etc.)

Usage:
    python platform_simulation.py [--domain DOMAIN] [--num-tasks N]

Environment Variables:
    NEBIUS_API_KEY - Required for both agents (Qwen model)
"""

import argparse
import asyncio
import json
import os
import sys
import uuid
from dataclasses import dataclass
from dotenv import load_dotenv

import httpx


# Load .env file early so all fixtures and tests have access to env vars
load_dotenv()

# Colors for terminal output
class Colors:
    RED = "\033[0;31m"
    GREEN = "\033[0;32m"
    YELLOW = "\033[1;33m"
    BLUE = "\033[0;34m"
    CYAN = "\033[0;36m"
    NC = "\033[0m"  # No Color


def print_header(title: str, color: str = Colors.BLUE):
    """
    Prints a colored, framed header block with the given title.
    
    Parameters:
        title (str): Text to display in the header.
        color (str): ANSI color code string used for the header frame and title (use values from Colors). Defaults to Colors.BLUE.
    """
    print(f"\n{color}{'═' * 65}{Colors.NC}")
    print(f"{color}  {title}{Colors.NC}")
    print(f"{color}{'═' * 65}{Colors.NC}\n")


def print_success(msg: str):
    """
    Prints a green checkmark-styled success message to standard output.
    """
    print(f"{Colors.GREEN}✓{Colors.NC} {msg}")


def print_error(msg: str):
    """
    Prints an error message to stdout prefixed with a red cross symbol.
    
    Parameters:
        msg (str): The error text to display; printed in red with ANSI color reset after the message.
    """
    print(f"{Colors.RED}✗{Colors.NC} {msg}")


def print_info(msg: str):
    """
    Prints an informational message to stdout prefixed with a cyan arrow.
    
    Parameters:
        msg (str): The message text to display.
    """
    print(f"{Colors.CYAN}→{Colors.NC} {msg}")


@dataclass
class AgentRegistration:
    """Agent registration in the platform registry."""

    name: str
    role: str  # "evaluator" or "evaluatee"
    endpoint: str
    model: str
    capabilities: list[str]


class AgentRegistry:
    """Platform's agent registry."""

    def __init__(self):
        """
        Initialize the AgentRegistry with an empty mapping of agent names to registrations.
        
        The registry stores agents in `self.agents`, a dictionary mapping agent name (str) to AgentRegistration.
        """
        self.agents: dict[str, AgentRegistration] = {}

    def register(self, agent: AgentRegistration):
        """
        Register an agent in the registry and report the registration.
        
        Parameters:
            agent (AgentRegistration): Agent metadata to store; if an agent with the same name exists it will be overwritten.
        """
        self.agents[agent.name] = agent
        print_success(f"Registered agent: {agent.name} ({agent.role})")

    def get_evaluator(self) -> AgentRegistration | None:
        """
        Finds the first registered agent with role "evaluator".
        
        Returns:
            AgentRegistration or None: The first registered evaluator agent, or `None` if no evaluator is registered.
        """
        for agent in self.agents.values():
            if agent.role == "evaluator":
                return agent
        return None

    def get_evaluatee(self) -> AgentRegistration | None:
        """
        Get the first registered agent whose role is "evaluatee".
        
        Returns:
            AgentRegistration | None: The evaluatee agent if present, `None` otherwise.
        """
        for agent in self.agents.values():
            if agent.role == "evaluatee":
                return agent
        return None

    def display(self):
        """
        Print a human-readable list of all registered agents showing each agent's name, role, model, endpoint, and capabilities.
        
        Each registered agent is displayed as a formatted block containing the agent's name, role, model identifier, A2A endpoint, and a comma-separated list of capabilities. Intended for human-readable terminal output; does not return a value.
        """
        print("\nRegistered Agents:")
        for agent in self.agents.values():
            print(f"""
  ┌─────────────────────────────────────────────────────────────┐
  │  Agent: {agent.name:<52}│
  │  Role: {agent.role:<53}│
  │  Model: {agent.model:<52}│
  │  Endpoint: {agent.endpoint:<49}│
  │  Capabilities: {', '.join(agent.capabilities):<44}│
  └─────────────────────────────────────────────────────────────┘""")


class A2AClient:
    """Simple A2A client for platform communication."""

    def __init__(self, timeout: float = 600.0):
        """
        Initialize the A2A client and its underlying HTTP client.
        
        Parameters:
            timeout (float): Request timeout in seconds for the internal HTTP client; defaults to 600.0. The value is applied to the created httpx.AsyncClient used for A2A requests.
        """
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        """
        Close the underlying HTTP client and release associated network resources.
        
        Awaits the internal httpx.AsyncClient to finish and free its connections.
        """
        await self.client.aclose()

    async def discover_agent(self, base_url: str, agent_name: str) -> dict | None:
        """
        Retrieve an agent's discovery card from the platform A2A endpoint.
        
        Parameters:
            base_url (str): Base URL of the platform (e.g., "http://localhost:8001").
            agent_name (str): Agent identifier used in the A2A discovery path.
        
        Returns:
            dict: Parsed JSON agent card when HTTP 200 is returned.
            None: If the request fails or a non-200 response is received.
        """
        url = f"{base_url}/a2a/{agent_name}/.well-known/agent-card.json"
        try:
            response = await self.client.get(url)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print_error(f"Discovery failed: {e}")
        return None

    async def send_message(
        self, endpoint: str, message: str, context_id: str | None = None
    ) -> dict:
        """
        Send a JSON-RPC 2.0 A2A message to the specified endpoint.
        
        Parameters:
        	endpoint (str): URL of the agent A2A endpoint to POST the message to.
        	message (str): Text content to include as the single message part.
        	context_id (str | None): Optional context identifier to include on the message.
        
        Returns:
        	response (dict): Parsed JSON response from the endpoint.
        """
        request_id = str(uuid.uuid4())
        message_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "message/send",
            "params": {
                "message": {
                    "messageId": message_id,
                    "role": "user",
                    "parts": [{"text": message}],
                }
            },
        }

        if context_id:
            payload["params"]["message"]["contextId"] = context_id

        response = await self.client.post(
            endpoint, json=payload, headers={"Content-Type": "application/json"}
        )
        return response.json()


def extract_response_text(response: dict) -> str:
    """
    Extract the first text artifact from an A2A response.
    
    Parameters:
        response (dict): Parsed A2A JSON response potentially containing `"result" -> "artifacts"`,
            where each artifact has `"parts"` entries with `"kind"` and `"text"` fields.
    
    Returns:
        str: The `text` value of the first artifact part with `"kind" == "text"`, or an empty
        string if no such part is found or the response lacks the expected structure.
    """
    try:
        result = response.get("result", {})
        artifacts = result.get("artifacts", [])

        for artifact in artifacts:
            parts = artifact.get("parts", [])
            for part in parts:
                if part.get("kind") == "text":
                    return part.get("text", "")
    except Exception:
        pass
    return ""


async def run_platform_simulation(domain: str, num_tasks: int):
    """
    Simulate the platform workflow that registers agents, discovers them via A2A, requests an evaluation, and displays results.
    
    This coroutine boots a mock agent evaluation platform: verifies required environment variables, registers an evaluator and an evaluatee in an AgentRegistry, discovers both agents using the A2A protocol, sends an evaluation request to the evaluator for the given domain and number of tasks, extracts and prints the evaluator's textual response (or error/raw output), and cleans up network resources.
    
    Parameters:
        domain (str): Evaluation domain to request (e.g., "airline", "retail", "telecom", "mock").
        num_tasks (int): Number of tasks to request the evaluator to run.
    
    """
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║              🏢 Agent Evaluation Platform                     ║
║                                                               ║
║    Simulating platform-mediated agent evaluation via A2A      ║
║                                                               ║
╚═══════════════════════════════════════════════════════════════╝{Colors.NC}
""")

    # Step 1: Verify prerequisites
    print_header("STEP 1: Verifying Prerequisites")

    if not os.getenv("NEBIUS_API_KEY"):
        print_error("NEBIUS_API_KEY environment variable is not set")
        sys.exit(1)
    print_success("NEBIUS_API_KEY is set")

    # Step 2: Initialize agent registry
    print_header("STEP 2: Initializing Agent Registry")

    registry = AgentRegistry()

    # Register tau2_agent as evaluator
    registry.register(
        AgentRegistration(
            name="tau2_agent",
            role="evaluator",
            endpoint="http://localhost:8001/a2a/tau2_agent",
            model="model-agnostic",
            capabilities=["run_tau2_evaluation", "list_domains", "get_evaluation_results"],
        )
    )

    # Register simple_nebius_agent as evaluatee
    registry.register(
        AgentRegistration(
            name="simple_nebius_agent",
            role="evaluatee",
            endpoint="http://localhost:8001/a2a/simple_nebius_agent",
            model="nebius/Qwen/Qwen3-30B-A3B-Thinking-2507",
            capabilities=["conversational_agent"],
        )
    )

    registry.display()

    # Step 3: Discover agents via A2A
    print_header("STEP 3: Discovering Agents via A2A Protocol")

    client = A2AClient()

    evaluator = registry.get_evaluator()
    evaluatee = registry.get_evaluatee()

    evaluator_card = await client.discover_agent("http://localhost:8001", evaluator.name)
    if evaluator_card:
        print_success(f"Discovered {evaluator.name}: {evaluator_card.get('name')}")
    else:
        print_error(f"Failed to discover {evaluator.name}")
        await client.close()
        sys.exit(1)

    evaluatee_card = await client.discover_agent("http://localhost:8001", evaluatee.name)
    if evaluatee_card:
        print_success(f"Discovered {evaluatee.name}: {evaluatee_card.get('name')}")
    else:
        print_error(f"Failed to discover {evaluatee.name}")
        await client.close()
        sys.exit(1)

    # Step 4: Send evaluation request to tau2_agent
    print_header("STEP 4: Platform Sends Evaluation Request via A2A")

    evaluation_message = f"""Please evaluate the agent at endpoint {evaluatee.endpoint} using the {domain} domain. Run the evaluation with {num_tasks} tasks and 1 trial per task. Use the run_tau2_evaluation tool to execute this evaluation."""

    print(f"Platform → tau2_agent (A2A JSON-RPC 2.0)")
    print(f"\n  Message: {evaluation_message}")
    print()

    print_info("Sending evaluation request to tau2_agent...")
    print_info("(tau2_agent will execute the evaluation - this may take several minutes)")
    print()

    response = await client.send_message(evaluator.endpoint, evaluation_message)

    # Step 5: Display response from tau2_agent
    print_header("STEP 5: Evaluation Results from tau2_agent", Colors.GREEN)

    response_text = extract_response_text(response)

    if response_text:
        print(f"tau2_agent response:\n")
        print(response_text)
    else:
        # Check for errors
        if "error" in response:
            print_error(f"A2A Error: {response['error']}")
        else:
            print_info("Raw response:")
            print(json.dumps(response, indent=2))

    # Cleanup
    await client.close()

    print_header("Platform Summary", Colors.BLUE)
    print(f"  Domain: {domain}")
    print(f"  Tasks Requested: {num_tasks}")
    print(f"  Evaluator: {evaluator.name}")
    print(f"  Evaluatee: {evaluatee.name}")
    print(f"  Protocol: A2A (JSON-RPC 2.0)")
    print()
    print(f"{Colors.GREEN}Platform simulation completed{Colors.NC}")


def main():
    """
    Parse command-line arguments for the simulation and execute the asynchronous platform workflow.
    
    Accepts two flags:
    - --domain: evaluation domain; one of "airline", "retail", "telecom", or "mock" (default: "mock").
    - --num-tasks: number of tasks to evaluate (integer, default: 2).
    
    Starts the event loop and runs run_platform_simulation with the parsed arguments.
    """
    parser = argparse.ArgumentParser(
        description="Platform simulation for A2A-based agent evaluation"
    )
    parser.add_argument(
        "--domain",
        default="mock",
        choices=["airline", "retail", "telecom", "mock"],
        help="Evaluation domain (default: mock)",
    )
    parser.add_argument(
        "--num-tasks",
        type=int,
        default=2,
        help="Number of tasks to evaluate (default: 2)",
    )

    args = parser.parse_args()

    asyncio.run(run_platform_simulation(args.domain, args.num_tasks))


if __name__ == "__main__":
    main()