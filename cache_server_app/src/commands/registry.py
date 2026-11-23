#!/usr/bin/env python3.12
"""
registry

Command registry for routing commands to appropriate handlers.

Author: Marek Križan, Radim Mifka
Date: 30.3.2025
"""

from typing import Any, Callable

from cache_server_app.src.commands.agent import AgentCommands
from cache_server_app.src.commands.base import BaseCommand
from cache_server_app.src.commands.cache import CacheCommands
from cache_server_app.src.commands.server import ServerCommands
from cache_server_app.src.commands.store_path import StorePathCommands
from cache_server_app.src.commands.workspace import WorkspaceCommands


class CommandRegistry:
    """Registry for routing commands to appropriate handlers."""

    def __init__(self) -> None:
        self.commands: dict[str, BaseCommand] = {
            "server": ServerCommands(),
            "cache": CacheCommands(),
            "agent": AgentCommands(),
            "workspace": WorkspaceCommands(),
            "store-path": StorePathCommands(),
        }

    def handler(self, command: str, subcommand: str) -> Callable[..., None]:
        """The method running `command subcommand`; raises ValueError for unknown ones."""
        if command not in self.commands:
            raise ValueError(f"Unknown command: {command}")
        return self.commands[command].handler(subcommand)

    def execute(self, command: str, subcommand: str, *args: Any, **kwargs: Any) -> None:
        """Execute a command by routing it to the appropriate handler."""
        self.handler(command, subcommand)(*args, **kwargs)
