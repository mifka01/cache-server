#!/usr/bin/env python3.12
"""
workspace

Workspace command handlers.

Author: Marek Križan, Radim Mifka
Date: 30.3.2025
"""

import sys
import uuid
from typing import Any, Callable

import jwt

import cache_server_app.src.config.base as config
from cache_server_app.src.cache.base import BinaryCache
from cache_server_app.src.commands.base import BaseCommand
from cache_server_app.src.workspace import Workspace


class WorkspaceCommands(BaseCommand):
    """Handles all workspace-related commands."""

    def create(self, name: str, cache_name: str) -> None:
        """Create a new workspace."""
        if Workspace.get(name):
            print(f"ERROR: Workspace {name} already exists.")
            sys.exit(1)

        cache = BinaryCache.get(name=cache_name)
        if not cache:
            print(f"ERROR: Binary cache {cache_name} does not exist.")
            sys.exit(1)

        encoded_jwt = jwt.encode({"name": name}, config.key, algorithm="HS256")
        workspace_id = str(uuid.uuid1())
        Workspace(workspace_id, name, encoded_jwt, cache).save()

    def delete(self, name: str) -> None:
        """Delete a workspace."""
        workspace = Workspace.get(name)
        if not workspace:
            print(f"ERROR: Workspace {name} does not exist.")
            sys.exit(1)

        workspace.delete()

    def list(self) -> None:
        """List all workspaces."""
        db_result = self.database.get_workspace_list()
        for row in db_result:
            print(row[1])

    def info(self, name: str) -> None:
        """Get information about a workspace."""
        workspace = Workspace.get(name)
        if not workspace:
            print(f"ERROR: Workspace {name} does not exist.")
            sys.exit(1)

        output = f"Id: {workspace.id}\nName: {workspace.name}\nToken: {workspace.token}\nBinary cache: {workspace.cache.name}"
        print(output)

    def cache(self, name: str, cache_name: str) -> None:
        """Change workspace's binary cache."""
        workspace = Workspace.get(name)
        if not workspace:
            print(f"ERROR: Workspace {name} does not exist.")
            sys.exit(1)

        cache = BinaryCache.get(name=cache_name)
        if not cache:
            print(f"ERROR: Binary cache {cache_name} does not exist.")
            sys.exit(1)

        workspace.cache = cache
        workspace.update()

    def execute(self, command: str, *args: Any, **kwargs: Any) -> None:
        """Execute the specified workspace command."""
        commands: dict[str, Callable[..., None]] = {
            "create": self.create,
            "delete": self.delete,
            "list": self.list,
            "info": self.info,
            "cache": self.cache,
        }

        if command not in commands:
            raise ValueError(f"Unknown workspace command: {command}")

        commands[command](*args, **kwargs)
