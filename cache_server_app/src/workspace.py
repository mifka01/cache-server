#!/usr/bin/env python3.12
"""
workspace

Module containing the Workspace class.

Author: Marek Križan
Date: 1.5.2024
"""

from typing import Optional
from cache_server_app.src.binary_cache import BinaryCache
from cache_server_app.src.database import CacheServerDatabase


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

    def __init__(self, id: str, name: str, token: str, cache: BinaryCache):
        self.database = CacheServerDatabase()
        self.id = id
        self.name = name
        self.token = token
        self.cache = cache

    @staticmethod
    def get(name: str) -> Optional['Workspace']:
        row = CacheServerDatabase().get_workspace_row(name=name)
        if not row:
            return None

        cache = BinaryCache.get(row[3])
        if not cache:
            return None

        return Workspace(row[0], row[1], row[2], cache)

    def save(self) -> None:
        self.database.insert_workspace(self.id, self.name, self.token, self.cache.name)

    def update(self) -> None:
        self.database.update_workspace(self.id, self.name, self.token, self.cache.name)

    def delete(self) -> None:
        self.database.delete_all_workspace_agents(self.name)
        self.database.delete_workspace(self.name)

    def get_agents(self) -> list:
        return self.database.get_workspace_agents(self.name)
