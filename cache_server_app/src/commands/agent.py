#!/usr/bin/env python3.12
"""
agent

Agent command handlers.

Author: Marek Križan, Radim Mifka
Date: 30.3.2025
"""

import sys
import uuid
from typing import Any, Callable

import jwt

import cache_server_app.src.config.base as config
from cache_server_app.src.agent import Agent
from cache_server_app.src.commands.base import BaseCommand
from cache_server_app.src.workspace import Workspace


class AgentCommands(BaseCommand):
    """Handles all agent-related commands."""

    def add(self, name: str, workspace_name: str) -> None:
        """Add a new agent to a workspace."""
        if Agent.get(name):
            print(f"ERROR: Agent {name} already exists.")
            sys.exit(1)

        workspace = Workspace.get(name=workspace_name)
        if not workspace:
            print(f"ERROR: Workspace {workspace_name} does not exist.")
            sys.exit(1)

        agent_id = str(uuid.uuid1())
        encoded_jwt = jwt.encode({"name": name}, config.key, algorithm="HS256")
        Agent(agent_id, name, encoded_jwt, workspace).save()

    def remove(self, name: str) -> None:
        """Remove an agent."""
        agent = Agent.get(name)
        if not agent:
            print(f"ERROR: Agent {name} does not exist.")
            sys.exit(1)

        agent.delete()

    def list(self, workspace_name: str) -> None:
        """List all agents in a workspace."""
        workspace = Workspace.get(workspace_name)
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
        agent = Agent.get(name)
        if not agent:
            print(f"ERROR: Agent {name} does not exist.")
            sys.exit(1)

        output = f"Id: {agent.id}\nName: {agent.name}\nToken: {agent.token}\nWorkspace: {agent.workspace.name}"
        print(output)

    def execute(self, command: str, *args: Any, **kwargs: Any) -> None:
        """Execute the specified agent command."""
        commands: dict[str, Callable[..., None]] = {
            "add": self.add,
            "remove": self.remove,
            "list": self.list,
            "info": self.info,
            "workspace": self.workspace,
        }

        if command not in commands:
            raise ValueError(f"Unknown agent command: {command}")

        commands[command](*args, **kwargs) 
