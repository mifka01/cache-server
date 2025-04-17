#!/usr/bin/env python3.12
"""
registry

Command registry for routing commands to appropriate handlers.

Author: Marek Križan, Radim Mifka
Date: 30.3.2025
"""

from typing import Any

from cache_server_app.src.commands.agent import AgentCommands
from cache_server_app.src.commands.cache import CacheCommands
from cache_server_app.src.commands.server import ServerCommands
from cache_server_app.src.commands.store_path import StorePathCommands
from cache_server_app.src.commands.workspace import WorkspaceCommands


class CommandRegistry:
    """Registry for routing commands to appropriate handlers."""

    def __init__(self):
        self.commands = {
            "server": ServerCommands(),
            "cache": CacheCommands(),
            "agent": AgentCommands(),
            "workspace": WorkspaceCommands(),
            "store-path": StorePathCommands(),
        }

    def execute(self, command: str, subcommand: str, *args: Any, **kwargs: Any) -> None:
        """Execute a command by routing it to the appropriate handler."""
        if command not in self.commands:
            raise ValueError(f"Unknown command: {command}")

        handler = self.commands[command]
        handler.execute(subcommand, *args, **kwargs)
