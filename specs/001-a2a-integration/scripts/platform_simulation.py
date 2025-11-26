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
    """Print a formatted header."""
    print(f"\n{color}{'═' * 65}{Colors.NC}")
    print(f"{color}  {title}{Colors.NC}")
    print(f"{color}{'═' * 65}{Colors.NC}\n")


def print_success(msg: str):
    print(f"{Colors.GREEN}✓{Colors.NC} {msg}")


def print_error(msg: str):
    print(f"{Colors.RED}✗{Colors.NC} {msg}")


def print_info(msg: str):
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
        self.agents: dict[str, AgentRegistration] = {}

    def register(self, agent: AgentRegistration):
        self.agents[agent.name] = agent
        print_success(f"Registered agent: {agent.name} ({agent.role})")

    def get_evaluator(self) -> AgentRegistration | None:
        for agent in self.agents.values():
            if agent.role == "evaluator":
                return agent
        return None

    def get_evaluatee(self) -> AgentRegistration | None:
        for agent in self.agents.values():
            if agent.role == "evaluatee":
                return agent
        return None

    def display(self):
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
        self.timeout = timeout
        self.client = httpx.AsyncClient(timeout=timeout)

    async def close(self):
        await self.client.aclose()

    async def discover_agent(self, base_url: str, agent_name: str) -> dict | None:
        """Fetch agent card for discovery."""
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
        """Send A2A JSON-RPC message."""
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
    """Extract text content from A2A response."""
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
    """Main platform simulation flow."""
    print(f"""
{Colors.CYAN}╔═══════════════════════════════════════════════════════════════╗
║                                                               ║
║              🏢 Agent Evaluation Platform                     ║
║                                                               ║
║    Simulating platform-mediated agent evaluation via A2A     ║
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
    print(f"\n  Message: {evaluation_message[:100]}...")
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
            print(json.dumps(response, indent=2)[:1000])

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
