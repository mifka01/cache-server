#!/usr/bin/env python3.12
"""
agent

Agent command handlers.

Author: Marek Križan, Radim Mifka
Date: 30.3.2025
"""

import sys
import uuid
from typing import Callable

from cache_server_app.src.agent import Agent
from cache_server_app.src.auth import generate_token
from cache_server_app.src.commands.base import BaseCommand
from cache_server_app.src.workspace import Workspace


class AgentCommands(BaseCommand):
    """Handles all agent-related commands."""

    name = "agent"

    def add(self, name: str, workspace_name: str) -> None:
        """Add a new agent to a workspace."""
        if Agent.get(name=name):
            print(f"ERROR: Agent {name} already exists.")
            sys.exit(1)

        workspace = Workspace.get(name=workspace_name)
        if not workspace:
            print(f"ERROR: Workspace {workspace_name} does not exist.")
            sys.exit(1)

        agent_id = str(uuid.uuid1())
        Agent(agent_id, name, generate_token(), workspace).save()

    def delete(self, name: str) -> None:
        """Delete an agent."""
        agent = Agent.get(name=name)
        if not agent:
            print(f"ERROR: Agent {name} does not exist.")
            sys.exit(1)

        agent.delete()

    def list(self, workspace_name: str) -> None:
        """List all agents in a workspace."""
        workspace = Workspace.get(name=workspace_name)
        if not workspace:
            print(f"ERROR: Workspace {workspace_name} does not exist.")
            sys.exit(1)

        for row in workspace.get_agents():
            print(row[1])

    def workspace(self, agent_name: str, workspace_name: str) -> None:
        """Change the workspace of an agent."""
        agent = Agent.get(name=agent_name)
        if not agent:
            print(f"ERROR: Agent {agent_name} does not exist.")
            sys.exit(1)

        workspace = Workspace.get(name=workspace_name)
        if not workspace:
            print(f"ERROR: Workspace {workspace_name} does not exist.")
            sys.exit(1)

        agent.workspace = workspace
        agent.update()

    def info(self, name: str) -> None:
        """Get information about an agent."""
        agent = Agent.get(name=name)
        if not agent:
            print(f"ERROR: Agent {name} does not exist.")
            sys.exit(1)

        output = f"Id: {agent.id}\nName: {agent.name}\nToken: {agent.token}\nWorkspace: {agent.workspace.name}\n"
        print(output)

    def handlers(self) -> dict[str, Callable[..., None]]:
        return {
            "add": self.add,
            "delete": self.delete,
            "list": self.list,
            "info": self.info,
            "workspace": self.workspace,
        }
