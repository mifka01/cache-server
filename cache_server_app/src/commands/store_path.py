#!/usr/bin/env python3.12
"""
store_path

Store path command handlers.

Author: Marek Križan, Radim Mifka
Date: 30.3.2025
"""

import os
import sys
from typing import Any, Callable

from cache_server_app.src.cache.base import BinaryCache
from cache_server_app.src.commands.base import BaseCommand
from cache_server_app.src.store_path import StorePath


class StorePathCommands(BaseCommand):
    """Handles all store path-related commands."""

    def list(self, cache_name: str) -> None:
        """List all store paths in a cache."""
        cache = BinaryCache.get(name=cache_name)
        if not cache:
            print(f"ERROR: Binary cache {cache_name} does not exist.")
            sys.exit(1)

        for path in cache.get_paths():
            print(path[1])

    def delete(self, cache_name: str, store_hash: str) -> None:
        """Delete a store path."""
        cache = BinaryCache.get(name=cache_name)
        if not cache:
            print(f"ERROR: Binary cache {cache_name} does not exist.")
            sys.exit(1)

        path = StorePath.get(cache_name, store_hash=store_hash)
        if not path:
            print("ERROR: Store path not found")
            sys.exit(1)

        for file in os.listdir(cache.cache_dir):
            if path.file_hash in file:
                os.remove(os.path.join(cache.cache_dir, file))
        path.delete()

    def info(self, store_hash: str, cache_name: str) -> None:
        """Get information about a store path."""
        cache = BinaryCache.get(name=cache_name)
        if not cache:
            print(f"ERROR: Binary cache {cache_name} does not exist.")
            sys.exit(1)

        path = StorePath.get(cache_name, store_hash=store_hash)
        if not path:
            print("ERROR: Store path not found")
            sys.exit(1)

        output = f"Store hash: {path.store_hash}\nStore suffix: {path.store_suffix}\nFile hash: {path.file_hash}"
        print(output)

    def execute(self, command: str, *args: Any, **kwargs: Any) -> None:
        """Execute the specified store path command."""
        commands: dict[str, Callable[..., None]] = {
            "list": self.list,
            "delete": self.delete,
            "info": self.info,
        }

        if command not in commands:
            raise ValueError(f"Unknown store path command: {command}")

        commands[command](*args, **kwargs) 
