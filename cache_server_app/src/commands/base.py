#!/usr/bin/env python3.12
"""
base

Base command class for all commands.

Author: Radim Mifka
Date: 1.5.2024
"""

import os
import sys
from abc import ABC, abstractmethod
from typing import Any

from cache_server_app.src.database import CacheServerDatabase


class BaseCommand(ABC):
    """Base class for all commands."""

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
    def execute(self, *args: Any, **kwargs: Any) -> None:
        """Execute the command."""
        pass 