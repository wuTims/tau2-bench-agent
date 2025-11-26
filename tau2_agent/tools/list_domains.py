"""
ListDomains tool for ADK agent.

This tool enables external agents to discover available evaluation domains.
"""

from typing import Any

from google.adk.tools import BaseTool
from google.adk.tools.tool_context import ToolContext
from google.genai import types
from loguru import logger


# Domain descriptions (tau2 doesn't store these in registry)
DOMAIN_DESCRIPTIONS = {
    "airline": "Airline customer service (flights, bookings, cancellations)",
    "retail": "Retail e-commerce (orders, returns, exchanges)",
    "telecom": "Telecommunications support (technical issues, billing)",
    "telecom-workflow": "Telecommunications with workflow-based policy",
    "mock": "Simple test domain for development",
}


class ListDomains(BaseTool):
    """List available tau2-bench evaluation domains"""

    name = "list_domains"
    description = (
        "List all available tau2-bench evaluation domains and their descriptions"
    )

    def _get_declaration(self) -> types.FunctionDeclaration | None:
        """Generate the function declaration for this tool."""
        return types.FunctionDeclaration(
            name=self.name,
            description=self.description,
            parameters=types.Schema(
                type=types.Type.OBJECT,
                properties={},
            ),
        )

    async def run_async(
        self, *, args: dict[str, Any], tool_context: ToolContext
    ) -> Any:
        """Run the tool using tau2's registry."""
        from tau2.registry import registry
        from tau2.run import load_tasks

        domains_info = []
        for domain_name in registry.get_domains():
            try:
                # Get task count from tau2's task loader
                tasks = load_tasks(domain_name)
                num_tasks = len(tasks)
            except Exception as e:
                logger.warning(
                    f"Could not load tasks for domain {domain_name}: {e}"
                )
                num_tasks = None

            domains_info.append({
                "name": domain_name,
                "description": DOMAIN_DESCRIPTIONS.get(
                    domain_name, f"{domain_name} domain"
                ),
                "num_tasks": num_tasks,
            })

        return {"domains": domains_info}
