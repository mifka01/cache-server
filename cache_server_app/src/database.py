#!/usr/bin/env python3.12
"""
database

Module to handle SQL queries.

Author: Marek Križan, Radim Mifka
Date: 1.5.2024
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

    def __init__(self):
        self.database_file = config.database

    # create tables in case database file is empty
    def create_database(self) -> None:

        # create database file if missing
        if not os.path.exists(self.database_file):
            with open(self.database_file, "w"):
                pass

        # check if database file is empty
        if os.stat(self.database_file).st_size == 0:

            binary_cache_table = """ CREATE TABLE binary_cache (
                                    id VARCHAR UNIQUE PRIMARY KEY NOT NULL,
                                    name VARCHAR UNIQUE NOT NULL,
                                    url VARCHAR UNIQUE NOT NULL,
                                    token VARCHAR NOT NULL,
                                    access VARCHAR NOT NULL,
                                    port INT UNIQUE NOT NULL,
                                    retention INT NOT NULL
                                ); """

            storage_table = """ CREATE TABLE storage (
                                    id VARCHAR UNIQUE PRIMARY KEY,
                                    name VARCHAR NOT NULL,
                                    type VARCHAR NOT NULL,
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

            # create tables
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
    def execute_statement(self, statement: str) -> None:
        try:
            with sqlite3.connect(self.database_file) as db_connection:
                db_cursor = db_connection.cursor()
                db_cursor.execute(statement)
                db_connection.commit()
        except sqlite3.Error as e:
            print("ERROR: ", e)

    # execute SQL selects
    def execute_select(self, statement: str) -> list[Any]:
        try:
            with sqlite3.connect(self.database_file) as db_connection:
                db_cursor = db_connection.cursor()
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
    ) -> None:
        statement = """
            INSERT INTO binary_cache (id, name, url, token, access, port, retention)
            VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}')
            ; """.format(
            id,
            name,
            url,
            token,
            access,
            port,
            retention,
        )
        self.execute_statement(statement)

    def insert_cache_storage(self, id: str, name:str, type: str, cache_id: str) -> None:
        statement = """
            INSERT INTO storage (id, name, type, cache_id)
            VALUES ('{}', '{}', '{}', '{}')
            ; """.format(
            id, name, type, cache_id
        )
        self.execute_statement(statement)

    def insert_storage_config(self, id: str, config_key: str, config_value: str):
        statement = """
            INSERT INTO storage_config(storage_id, config_key, config_value)
            VALUES ('{}', '{}', '{}')
            ; """.format(
            id, config_key, config_value
        )
        self.execute_statement(statement)

    def delete_storage_config(self, id: str) -> None:
        statement = """
            DELETE FROM storage_config
            WHERE storage_id='{}'
            ; """.format(
            id
        )
        self.execute_statement(statement)

    def delete_binary_cache(self, id: str) -> None:
        statement = """
            DELETE FROM binary_cache
            WHERE id='{}'
            ; """.format(
            id
        )
        self.execute_statement(statement)

    def update_storage(self, id: str, type: str) -> None:
        statement = """
            UPDATE storage
            SET type='{}'
            WHERE id='{}'
            ; """.format(
            type, id
        )
        self.execute_statement(statement)

    def delete_storage(self, id: str) -> None:
        statement = """
            DELETE FROM storage
            WHERE id='{}'
            ; """.format(
            id
        )

        self.execute_statement(statement)

    def update_binary_cache(
        self,
        id: str,
        name: str,
        url: str,
        token: str,
        access: str,
        port: int,
        retention: int
    ) -> None:
        statement = """
            UPDATE binary_cache
            SET name='{}', url='{}', token='{}', access='{}', port='{}', retention='{}'
            WHERE id='{}'
            ; """.format(
            name, url, token, access, port, retention, id
        )
        self.execute_statement(statement)

    def get_binary_cache_row(self, id: str | None = None, name: str | None = None, port: int | None = None) -> Optional[BinaryCacheRow]:
        if id:
            statement = """
                SELECT * FROM binary_cache
                WHERE id='{}'
                ; """.format(
                id
            )
        elif name:
            statement = """
                SELECT * FROM binary_cache
                WHERE name='{}'
                ; """.format(
                name
            )
        elif port:
            statement = """
                SELECT * FROM binary_cache
                WHERE port='{}'
                ; """.format(
                port
            )
        else:
            return None

        db_result = self.execute_select(statement)

        if not db_result:
            return None

        return db_result[0]

    def get_cache_storages(self, id: str) -> List[StorageRow]:
        statement = """
            SELECT * FROM storage
            WHERE cache_id='{}'
            ; """.format(
            id
        )
        return self.execute_select(statement)

    def get_storage_config(self, storage_id: str) -> Dict[str, str]:
        statement = """
            SELECT * FROM storage_config
            WHERE storage_id='{}'
            ; """.format(
            storage_id
        )
        db_result = self.execute_select(statement)

        if not db_result:
            return {}

        return {row[0]: row[1] for row in db_result}

    def get_private_cache_list(self) -> List[BinaryCacheRow]:
        statement = """
            SELECT * FROM binary_cache
            WHERE access={}
            ; """.format(
            CacheAccess.PRIVATE.value
        )
        return self.execute_select(statement)

    def get_public_cache_list(self) -> List[BinaryCacheRow]:
        statement = """
            SELECT * FROM binary_cache
            WHERE access={}
            ; """.format(
            CacheAccess.PUBLIC.value
        )
        return self.execute_select(statement)

    def get_cache_list(self) -> List[BinaryCacheRow]:
        statement = """
            SELECT * FROM binary_cache
            ; """
        return self.execute_select(statement)

    def get_storages_store_paths(self, storage_ids: List[str]) -> List[StorePathRow]:
        statement = """
            SELECT * FROM store_path
            WHERE storage_id IN ({})
            ; """.format(
            storage_ids
        )
        return self.execute_select(statement)

    def get_storage_store_paths(self, storage_id: str) -> List[StorePathRow]:
        statement = """
            SELECT * FROM store_path
            WHERE storage_id='{}'
            ; """.format(
            storage_id
        )
        return self.execute_select(statement)

    def insert_agent(
        self, agent_id: str, name: str, token: str, workspace_name: str
    ) -> None:
        statement = """
            INSERT INTO agent (id, name, token, workspace_name)
            VALUES ('{}', '{}', '{}', '{}')
            ; """.format(
            agent_id, name, token, workspace_name
        )
        self.execute_statement(statement)

    def delete_agent(self, name: str) -> None:
        statement = """
            DELETE FROM agent
            WHERE name='{}'
            ; """.format(
            name
        )
        self.execute_statement(statement)

    def get_agent_row(self, name: str) -> Optional[AgentRow]:
        statement = """
            SELECT * FROM agent
            WHERE name='{}'
            ; """.format(
            name
        )
        db_result = self.execute_select(statement)

        if not db_result:
            return None

        return db_result[0]

    def get_workspace_agents(self, workspace_name: str) -> List[AgentRow]:
        statement = """
            SELECT * FROM agent
            WHERE workspace_name='{}'
            ; """.format(
            workspace_name
        )
        return self.execute_select(statement)

    def get_store_paths(self, storage_ids: List[str]) -> List[StorePathRow]:
        statement = """
            SELECT * FROM store_path
            WHERE storage_id IN ({})
            ; """.format(
            storage_ids
        )
        return self.execute_select(statement)

    def get_store_path_row(
        self, storage_ids: List[str], store_hash: str = "", file_hash: str = ""
    ) -> Optional[StorePathRow]:
        if store_hash:
            statement = """
                SELECT * FROM store_path
                WHERE store_hash='{}'
                AND storage_id IN ({})
                ; """.format(
                store_hash, storage_ids
            )
        else:
            statement = """
                SELECT * FROM store_path
                WHERE file_hash='{}'
                AND storage_id IN ({})
                ; """.format(
                file_hash, storage_ids
            )

        db_result = self.execute_select(statement)

        if not db_result:
            return None

        return db_result[0]

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
            VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')
            ; """.format(
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
        self.execute_statement(statement)

    def delete_store_path(self, store_hash: str, storage_id: str) -> None:
        statement = """
            DELETE FROM store_path
            WHERE store_hash='{}'
            AND storage_id='{}'
            ; """.format(
            store_hash, storage_id
        )
        self.execute_statement(statement)

    def insert_workspace(
        self, workspace_id: str, name: str, token: str, cache_name: str
    ) -> None:
        statement = """
            INSERT INTO workspace (id, name, token, cache_name)
            VALUES ('{}', '{}', '{}', '{}')
            ; """.format(
            workspace_id, name, token, cache_name
        )
        self.execute_statement(statement)

    def delete_workspace(self, name: str) -> None:
        statement = """
            DELETE FROM workspace
            WHERE name='{}'
            ; """.format(
            name
        )
        self.execute_statement(statement)

    def get_workspace_row(self, id: str | None = None, name: str | None = None, token : str | None = None) -> Optional[WorkspaceRow]:
        if id:
            statement = """
                SELECT * FROM workspace
                WHERE id='{}'
                ; """.format(
                id
            )
        if name:
            statement = """
                SELECT * FROM workspace
                WHERE name='{}'
                ; """.format(
                name
            )
        elif token:
            statement = """
                SELECT * FROM workspace
                WHERE token='{}'
                ; """.format(
                token
            )
        else:
            return None

        db_result = self.execute_select(statement)

        if not db_result:
            return None

        return db_result[0]

    def get_workspace_row_by_token(self, token: str) -> Optional[WorkspaceRow]:
        statement = """
            SELECT * FROM workspace
            WHERE token='{}'
            ; """.format(
            token
        )
        db_result = self.execute_select(statement)

        if not db_result:
            return None

        return db_result[0]

    def delete_all_workspace_agents(self, workspace_name: str) -> None:
        statement = """
            DELETE FROM agent
            WHERE workspace_name='{}'
        ; """.format(
            workspace_name
        )
        self.execute_statement(statement)

    def get_workspace_list(self) -> List[WorkspaceRow]:
        statement = """
            SELECT * FROM workspace
            ; """
        return self.execute_select(statement)

    def update_workspace(self, id: str, name: str, token: str, cache_name: str) -> None:
        statement = """
            UPDATE workspace
            SET name='{}', token='{}', cache_name='{}'
            WHERE id='{}'
            ; """.format(
            name, token, cache_name, id
        )
        self.execute_statement(statement)

    def update_cache_in_workspaces(self, cache_name: str, new_name: str) -> None:
        statement = """
            UPDATE workspace
            SET cache_name='{}'
            WHERE cache_name='{}'
            ; """.format(
            new_name, cache_name
        )
        self.execute_statement(statement)

    def update_cache_in_paths(self, cache_name: str, new_name: str) -> None:
        statement = """
            UPDATE store_path
            SET cache_name='{}'
            WHERE cache_name='{}'
            ; """.format(
            new_name, cache_name
        )
        self.execute_statement(statement)
