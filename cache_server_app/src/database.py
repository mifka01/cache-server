#!/usr/bin/env python3.12
"""
database

Module to handle SQL queries.

Author: Marek Križan, Radim Mifka

Date: 17.4.2025
"""

import os
import sqlite3
from typing import Dict, Any, List, Optional, Tuple

from cache_server_app.src.cache.access import CacheAccess
import cache_server_app.src.config.base as config
from cache_server_app.src.types import BinaryCacheRow, StorageRow, StorePathRow, WorkspaceRow, AgentRow


class CacheServerDatabase:
    """
    Class to handle SQLite database queires.

    Attributes:
        database_file: database file specified in the cache-server configuration
    """

    def __init__(self) -> None:
        self.database_file = config.database

    def create_database(self) -> None:
        if not os.path.exists(self.database_file):
            with open(self.database_file, "w"):
                pass

        if os.stat(self.database_file).st_size == 0:
            binary_cache_table = """ CREATE TABLE binary_cache (
                                    id VARCHAR UNIQUE PRIMARY KEY NOT NULL,
                                    name VARCHAR UNIQUE NOT NULL,
                                    url VARCHAR UNIQUE NOT NULL,
                                    token VARCHAR NOT NULL,
                                    access VARCHAR NOT NULL,
                                    port INT UNIQUE NOT NULL,
                                    retention INT NOT NULL,
                                    strategy VARCHAR NOT NULL,
                                    strategy_state VARCHAR NOT NULL
                                ); """

            storage_table = """ CREATE TABLE storage (
                                    id VARCHAR UNIQUE PRIMARY KEY,
                                    name VARCHAR NOT NULL,
                                    type VARCHAR NOT NULL,
                                    root VARCHAR NOT NULL,
                                    cache_id VARCHAR,
                                    FOREIGN KEY(cache_id) REFERENCES binary_cache(id)
                                ); """

            storage_config_table = """ CREATE TABLE storage_config (
                                    config_key VARCHAR NOT NULL,
                                    config_value TEXT,
                                    storage_id VARCHAR,
                                    FOREIGN KEY(storage_id) REFERENCES storage(id)
                                    ); """

            store_path_table = """ CREATE TABLE store_path (
                                    id VARCHAR UNIQUE PRIMARY KEY,
                                    store_hash VARCHAR,
                                    store_suffix VARCHAR,
                                    file_hash VARCHAR,
                                    file_size INT,
                                    nar_hash VARCHAR,
                                    nar_size INT,
                                    deriver VARCHAR,
                                    refs VARCHAR,
                                    storage_id VARCHAR,
                                    FOREIGN KEY(storage_id) REFERENCES storage(id)
                                ); """

            workspace_table = """ CREATE TABLE workspace (
                                    id VARCHAR UNIQUE PRIMARY KEY,
                                    name VARCHAR,
                                    token VARCHAR,
                                    cache_id VARCHAR,
                                    FOREIGN KEY(cache_id) REFERENCES binary_cache(id)
                                ); """

            agent_table = """ CREATE TABLE agent (
                                    id VARCHAR UNIQUE PRIMARY KEY,
                                    name VARCHAR,
                                    token VARCHAR,
                                    workspace_id VARCHAR,
                                    FOREIGN KEY(workspace_id) REFERENCES workspace(id)
                                ); """

            with sqlite3.connect(self.database_file) as db_connection:
                db_cursor = db_connection.cursor()
                db_cursor.execute(binary_cache_table)
                db_cursor.execute(storage_table)
                db_cursor.execute(storage_config_table)
                db_cursor.execute(store_path_table)
                db_cursor.execute(workspace_table)
                db_cursor.execute(agent_table)
                db_connection.commit()

    # execute statements without returning any value
    def execute_statement(self, statement: str, params: Optional[Tuple[Any, ...]] = None) -> None:
        try:
            with sqlite3.connect(self.database_file) as db_connection:
                db_cursor = db_connection.cursor()
                if params:
                    db_cursor.execute(statement, params)
                else:
                    db_cursor.execute(statement)
                db_connection.commit()
        except sqlite3.Error as e:
            print("ERROR: ", e)

    # execute SQL selects with list of results
    def execute_select(self, statement: str, params: Optional[Tuple[Any, ...]] = None) -> list[Any]:
        try:
            with sqlite3.connect(self.database_file) as db_connection:
                db_cursor = db_connection.cursor()
                if params:
                    result = db_cursor.execute(statement, params).fetchall()
                else:
                    result = db_cursor.execute(statement).fetchall()
                db_connection.commit()
            return result
        except sqlite3.Error as e:
            print("ERROR: ", e)
            return []

    def insert_binary_cache(
        self,
        id: str,
        name: str,
        url: str,
        token: str,
        access: str,
        port: int,
        retention: int,
        strategy: str,
        strategy_state: str,
    ) -> None:
        statement = """
            INSERT INTO binary_cache (id, name, url, token, access, port, retention, strategy, strategy_state)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ;"""
        params = (id, name, url, token, access, port, retention, strategy, strategy_state)
        self.execute_statement(statement, params)

    def update_storage_strategy_state(self, id: str, strategy: str, strategy_state: str) -> None:
        statement = """
            UPDATE binary_cache
            SET strategy=?, strategy_state=?
            WHERE id=?
            ;"""
        params = (strategy, strategy_state, id)
        self.execute_statement(statement, params)

    def insert_cache_storage(self, id: str, name:str, type: str, root: str, cache_id: str) -> None:
        statement = """
            INSERT INTO storage (id, name, type, root, cache_id)
            VALUES (?, ?, ?, ?, ?)
            ;"""
        params = (id, name, type, root, cache_id)
        self.execute_statement(statement, params)

    def insert_storage_config(self, id: str, config_key: str, config_value: str) -> None:
        statement = """
            INSERT INTO storage_config(storage_id, config_key, config_value)
            VALUES (?, ?, ?)
            ;"""
        params = (id, config_key, config_value)
        self.execute_statement(statement, params)

    def delete_storage_config(self, id: str) -> None:
        statement = """
            DELETE FROM storage_config
            WHERE storage_id=?
            ;"""
        self.execute_statement(statement, (id,))

    def delete_binary_cache(self, id: str) -> None:
        statement = """
            DELETE FROM binary_cache
            WHERE id=?
            ;"""
        self.execute_statement(statement, (id,))

    def update_storage(self, id: str, type: str, root: str) -> None:
        statement = """
            UPDATE storage
            SET type=?, root=?
            WHERE id=?
            ;"""
        self.execute_statement(statement, (type, root, id))

    def delete_storage(self, id: str) -> None:
        statement = """
            DELETE FROM storage
            WHERE id=?
            ;"""
        self.execute_statement(statement, (id,))

    def update_binary_cache(
        self,
        id: str,
        name: str,
        url: str,
        token: str,
        access: str,
        port: int,
        retention: int,
        strategy: str,
        strategy_state: str
    ) -> None:
        statement = """
            UPDATE binary_cache
            SET name=?, url=?, token=?, access=?, port=?, retention=?, strategy=?, strategy_state=?
            WHERE id=?
            ;"""
        params = (name, url, token, access, port, retention, strategy, strategy_state, id)
        self.execute_statement(statement, params)

    def get_binary_cache_row(self, id: str | None = None, name: str | None = None, port: int | None = None) -> Optional[BinaryCacheRow]:
        statement = None
        params = None

        if id:
            statement = "SELECT * FROM binary_cache WHERE id=?;"
            params = (id,)
        elif name:
            statement = "SELECT * FROM binary_cache WHERE name=?;"
            params = (name,)
        elif port:
            statement = "SELECT * FROM binary_cache WHERE port=?;"
            params = (str(port),)
        else:
            return None

        db_result = self.execute_select(statement, params)

        if not db_result:
            return None

        row: BinaryCacheRow = db_result[0]

        return row

    def get_cache_storages(self, id: str) -> List[StorageRow]:
        statement = """
            SELECT * FROM storage
            WHERE cache_id=?
            ;"""
        return self.execute_select(statement, (id,))

    def get_storage_row(self, storage_id: str) -> Optional[StorageRow]:
        statement = """
            SELECT * FROM storage
            WHERE id=?
            ;"""
        db_result = self.execute_select(statement, (storage_id,))

        if not db_result:
            return None

        row: StorageRow = db_result[0]

        return row

    def get_storage_config(self, storage_id: str) -> Dict[str, str]:
        statement = """
            SELECT * FROM storage_config
            WHERE storage_id=?
            ;"""
        db_result = self.execute_select(statement, (storage_id,))

        if not db_result:
            return {}

        return {row[0]: row[1] for row in db_result}

    def get_private_cache_list(self) -> List[BinaryCacheRow]:
        statement = """
            SELECT * FROM binary_cache
            WHERE access=?
            ;"""
        return self.execute_select(statement, (CacheAccess.PRIVATE.value,))

    def get_public_cache_list(self) -> List[BinaryCacheRow]:
        statement = """
            SELECT * FROM binary_cache
            WHERE access=?
            ;"""
        return self.execute_select(statement, (CacheAccess.PUBLIC.value,))

    def get_cache_list(self) -> List[BinaryCacheRow]:
        statement = """
            SELECT * FROM binary_cache
            ;"""
        return self.execute_select(statement)

    def get_storages_store_paths(self, storage_ids: List[str]) -> List[StorePathRow]:
        if not storage_ids:
            return []

        placeholders = ', '.join('?' for _ in storage_ids)
        statement = f"""
            SELECT * FROM store_path
            WHERE storage_id IN ({placeholders})
            ;"""
        return self.execute_select(statement, tuple(storage_ids))

    def get_storage_store_paths(self, storage_id: str) -> List[StorePathRow]:
        statement = """
            SELECT * FROM store_path
            WHERE storage_id=?
            ;"""
        return self.execute_select(statement, (storage_id,))

    def insert_agent(
        self, agent_id: str, name: str, token: str, workspace_name: str
    ) -> None:
        statement = """
            INSERT INTO agent (id, name, token, workspace_name)
            VALUES (?, ?, ?, ?)
            ;"""
        params = (agent_id, name, token, workspace_name)
        self.execute_statement(statement, params)

    def delete_agent(self, name: str) -> None:
        statement = """
            DELETE FROM agent
            WHERE name=?
            ;"""
        self.execute_statement(statement, (name,))

    def get_agent_row(self, name: str) -> Optional[AgentRow]:
        statement = """
            SELECT * FROM agent
            WHERE name=?
            ;"""
        db_result = self.execute_select(statement, (name,))

        if not db_result:
            return None

        row: AgentRow = db_result[0]

        return row

    def get_workspace_agents(self, workspace_name: str) -> List[AgentRow]:
        statement = """
            SELECT * FROM agent
            WHERE workspace_name=?
            ;"""
        return self.execute_select(statement, (workspace_name,))

    def get_store_paths(self, storage_ids: List[str]) -> List[StorePathRow]:
        if not storage_ids:
            return []

        placeholders = ', '.join('?' for _ in storage_ids)
        statement = f"""
            SELECT * FROM store_path
            WHERE storage_id IN ({placeholders})
            ;"""
        return self.execute_select(statement, tuple(storage_ids))

    def get_store_path_row(
        self, storage_ids: List[str], store_hash: str = "", file_hash: str = ""
    ) -> Optional[StorePathRow]:
        if not storage_ids:
            return None

        placeholders = ', '.join('?' for _ in storage_ids)
        params = list(storage_ids)

        if store_hash:
            statement = f"""
                SELECT * FROM store_path
                WHERE store_hash=?
                AND storage_id IN ({placeholders})
                ;"""
            params.insert(0, store_hash)
        else:
            statement = f"""
                SELECT * FROM store_path
                WHERE file_hash=?
                AND storage_id IN ({placeholders})
                ;"""
            params.insert(0, file_hash)

        db_result = self.execute_select(statement, tuple(params))

        if not db_result:
            return None

        row: StorePathRow = db_result[0]

        return row

    def find_store_paths(self, store_hash: str = "", file_hash: str = "") -> List[StorePathRow]:
        if not store_hash and not file_hash:
            return []

        if store_hash:
            statement = """
                SELECT * FROM store_path
                WHERE store_hash=?
                ;"""
            params = (store_hash,)

        else:
            statement = """
                SELECT * FROM store_path
                WHERE file_hash=?
                ;"""
            params = (file_hash,)

        return self.execute_select(statement, params)

    def insert_store_path(
        self,
        id: str,
        store_hash: str,
        store_suffix: str,
        file_hash: str,
        file_size: int,
        nar_hash: str,
        nar_size: int,
        deriver: str,
        references: list[str],
        storage_id: str,
    ) -> None:
        statement = """
            INSERT INTO store_path (id, store_hash, store_suffix, file_hash, file_size, nar_hash,
            nar_size, deriver, refs, storage_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ;"""
        params = (
            id,
            store_hash,
            store_suffix,
            file_hash,
            file_size,
            nar_hash,
            nar_size,
            deriver,
            " ".join(references),
            storage_id,
        )
        self.execute_statement(statement, params)

    def delete_store_path(self, store_hash: str, storage_id: str) -> None:
        statement = """
            DELETE FROM store_path
            WHERE store_hash=?
            AND storage_id=?
            ;"""
        self.execute_statement(statement, (store_hash, storage_id))

    def insert_workspace(
        self, workspace_id: str, name: str, token: str, cache_name: str
    ) -> None:
        statement = """
            INSERT INTO workspace (id, name, token, cache_name)
            VALUES (?, ?, ?, ?)
            ;"""
        params = (workspace_id, name, token, cache_name)
        self.execute_statement(statement, params)

    def delete_workspace(self, name: str) -> None:
        statement = """
            DELETE FROM workspace
            WHERE name=?
            ;"""
        self.execute_statement(statement, (name,))

    def get_workspace_row(self, id: str | None = None, name: str | None = None, token : str | None = None) -> Optional[WorkspaceRow]:
        statement = None
        params = None

        if id:
            statement = "SELECT * FROM workspace WHERE id=?;"
            params = (id,)
        elif name:
            statement = "SELECT * FROM workspace WHERE name=?;"
            params = (name,)
        elif token:
            statement = "SELECT * FROM workspace WHERE token=?;"
            params = (token,)
        else:
            return None

        db_result = self.execute_select(statement, params)

        if not db_result:
            return None

        row: WorkspaceRow = db_result[0]

        return row

    def get_workspace_row_by_token(self, token: str) -> Optional[WorkspaceRow]:
        statement = """
            SELECT * FROM workspace
            WHERE token=?
            ;"""
        db_result = self.execute_select(statement, (token,))

        if not db_result:
            return None

        row: WorkspaceRow = db_result[0]

        return row

    def delete_all_workspace_agents(self, workspace_name: str) -> None:
        statement = """
            DELETE FROM agent
            WHERE workspace_name=?
            ;"""
        self.execute_statement(statement, (workspace_name,))

    def get_workspace_list(self) -> List[WorkspaceRow]:
        statement = """
            SELECT * FROM workspace
            ;"""
        return self.execute_select(statement)

    def update_workspace(self, id: str, name: str, token: str, cache_name: str) -> None:
        statement = """
            UPDATE workspace
            SET name=?, token=?, cache_name=?
            WHERE id=?
            ;"""
        params = (name, token, cache_name, id)
        self.execute_statement(statement, params)

    def update_cache_in_workspaces(self, cache_name: str, new_name: str) -> None:
        statement = """
            UPDATE workspace
            SET cache_name=?
            WHERE cache_name=?
            ;"""
        self.execute_statement(statement, (new_name, cache_name))

    def update_cache_in_paths(self, cache_name: str, new_name: str) -> None:
        statement = """
            UPDATE store_path
            SET cache_name=?
            WHERE cache_name=?
            ;"""
        self.execute_statement(statement, (new_name, cache_name))
