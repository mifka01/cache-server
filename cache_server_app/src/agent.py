#!/usr/bin/env python3.12
"""
agent

Modul containing the Agent class.

Author: Marek Križan
Date: 1.5.2024
"""

from typing import Optional

from cache_server_app.src.database import CacheServerDatabase
from cache_server_app.src.workspace import Workspace


class Agent:
    """
    Class to represent deployment agent.

    Attributes:
        database: object to handle database connection
        id: agent id
        name: agent name
        token: agent JWT authentication token
        workspace: object representing workspace to which agent belongs
    """

    def __init__(self, id: str, name: str, token: str, workspace: Workspace) -> None:
        self.database = CacheServerDatabase()
        self.id = id
        self.name = name
        self.token = token
        self.workspace = workspace

    @staticmethod
    def get(name: str) -> Optional['Agent']:
        row = CacheServerDatabase().get_agent_row(name)
        if not row:
            return None

        workspace = Workspace.get(row[3])
        if not workspace:
            return None

        return Agent(row[0], row[1], row[2], workspace)

    def save(self) -> None:
        self.database.insert_agent(self.id, self.name, self.token, self.workspace.name)

    def delete(self) -> None:
        self.database.delete_agent(self.name)
