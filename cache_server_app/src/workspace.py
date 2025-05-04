#!/usr/bin/env python3.12
"""
workspace

Module containing the Workspace class.

Author: Marek Križan

Date: 1.5.2024
"""

from typing import List, Optional
from cache_server_app.src.cache.base import BinaryCache
from cache_server_app.src.database import CacheServerDatabase
from cache_server_app.src.types import AgentRow, WorkspaceRow


class Workspace:
    """
    Class to represent deployment workspace.

    Attributes:
        database: object to handle database connection
        id: workspace id
        name: workspace name
        token: workspace JWT activation token
        workspace: object representing binary cache which workspace uses
    """

    def __init__(self, id: str, name: str, token: str, cache: BinaryCache) -> None:
        self.database = CacheServerDatabase()
        self.id = id
        self.name = name
        self.token = token
        self.cache = cache

    @staticmethod
    def get_rows() -> List[WorkspaceRow]:
        return CacheServerDatabase().get_workspaces()

    @staticmethod
    def get(id: str | None = None, name: str | None = None) -> Optional['Workspace']:
        row = CacheServerDatabase().get_workspace_row(id=id, name=name)
        if not row:
            return None

        cache = BinaryCache.get(id=row[3])
        if not cache:
            return None

        return Workspace(row[0], row[1], row[2], cache)

    def save(self) -> None:
        self.database.insert_workspace(self.id, self.name, self.token, self.cache.id)

    def update(self) -> None:
        self.database.update_workspace(self.id, self.name, self.token, self.cache.id)

    def delete(self) -> None:
        self.database.delete_all_workspace_agents(self.id)
        self.database.delete_workspace(self.name)

    def get_agents(self) -> List[AgentRow]:
        return self.database.get_workspace_agents(self.name)

