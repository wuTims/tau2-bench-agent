"""
ListDomains tool for ADK agent.

This tool enables external agents to discover available evaluation domains.
"""

from typing import Any

from google.adk.tools import BaseTool


class ListDomains(BaseTool):
    """List available tau2-bench evaluation domains"""

    name = "list_domains"
    description = (
        "List all available tau2-bench evaluation domains and their descriptions"
    )

    async def __call__(self, tool_context) -> dict[str, Any]:
        """Return available domains"""
        return {
            "domains": [
                {
                    "name": "airline",
                    "description": "Airline customer service (flights, bookings, cancellations)",
                    "num_tasks": 45,
                },
                {
                    "name": "retail",
                    "description": "Retail e-commerce (orders, returns, exchanges)",
                    "num_tasks": 39,
                },
                {
                    "name": "telecom",
                    "description": "Telecommunications support (technical issues, billing)",
                    "num_tasks": 50,
                },
                {
                    "name": "mock",
                    "description": "Simple test domain for development",
                    "num_tasks": 5,
                },
            ]
        }
