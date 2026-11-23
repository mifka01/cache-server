#!/usr/bin/env python3.12
"""
base

Base command class for all commands.

Author: Marek Križan, Radim Mifka
Date: 30.3.2025
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Any, Callable

from cache_server_app.src.database import CacheServerDatabase


class BaseCommand(ABC):
    """Base class for all commands."""

    name = "command"

    def __init__(self, database: CacheServerDatabase | None = None):
        self.database = database or CacheServerDatabase()

    def save_pid(self, filename: str) -> None:
        """Save process ID to a file."""
        try:
            with open(filename, "w") as f:
                f.write(str(os.getpid()))
        except PermissionError:
            print(f"ERROR: Can't create file {filename}. Permission denied.")
            sys.exit(1)

    def get_pid(self, filename: str) -> int | None:
        """Get process ID from a file."""
        try:
            with open(filename, "r") as f:
                return int(f.read().strip())
        except FileNotFoundError:
            return None
        except PermissionError:
            print(f"ERROR: Can't read file {filename}. Permission denied.")
            sys.exit(1)

    def remove_pid(self, filename: str) -> None:
        """Remove process ID file."""
        try:
            os.remove(filename)
        except FileNotFoundError:
            pass
        except PermissionError:
            print(f"ERROR: Can't remove file {filename}. Permission denied.")
            sys.exit(1)

    @abstractmethod
    def handlers(self) -> dict[str, Callable[..., None]]:
        """Subcommand names mapped to the methods that run them."""

    def handler(self, command: str) -> Callable[..., None]:
        """The method running a subcommand; raises ValueError for unknown ones."""
        handlers = self.handlers()
        if command not in handlers:
            raise ValueError(f"Unknown {self.name} command: {command}")
        return handlers[command]

    def execute(self, command: str, *args: Any, **kwargs: Any) -> None:
        """Execute the specified subcommand."""
        self.handler(command)(*args, **kwargs)
