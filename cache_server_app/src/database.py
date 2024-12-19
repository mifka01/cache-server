#!/usr/bin/env python3.12
"""
database

Module to handle SQL queries.

Author: Marek Križan, Radim Mifka
Date: 1.5.2024
"""

import os
import sqlite3
from typing import Dict

import cache_server_app.src.config as config


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
                                    id VARCHAR UNIQUE,
                                    name VARCHAR UNIQUE,
                                    url VARCHAR,
                                    token VARCHAR,
                                    access VARCHAR,
                                    port VARCHAR,
                                    retention INT,
                                    storage VARCHAR
                                ); """

            cache_storage_config = """ CREATE TABLE cache_storage_config (
                                    id SERIAL PRIMARY KEY,
                                    cache_id INT REFERENCES caches(id) ON DELETE CASCADE,
                                    config_key VARCHAR(255) NOT NULL,
                                    config_value TEXT,
                                    UNIQUE (cache_id, config_key)
                                    );"""

            store_path_table = """ CREATE TABLE store_path (
                                    id VARCHAR UNIQUE,
                                    store_hash VARCHAR,
                                    store_suffix VARCHAR,
                                    file_hash VARCHAR,
                                    file_size INT,
                                    nar_hash VARCHAR,
                                    nar_size INT,
                                    deriver VARCHAR,
                                    refs VARCHAR,
                                    cache_name VARCHAR,
                                    FOREIGN KEY(cache_name) REFERENCES binary_cache(name)
                                ); """

            workspace_table = """ CREATE TABLE workspace (
                                    id VARCHAR UNIQUE,
                                    name VARCHAR,
                                    token VARCHAR,
                                    cache_name VARCHAR,
                                    FOREIGN KEY(cache_name) REFERENCES binary_cache(name)
                                ); """

            agent_table = """ CREATE TABLE agent (
                                    id VARCHAR UNIQUE,
                                    name VARCHAR,
                                    token VARCHAR,
                                    workspace_name VARCHAR,
                                    FOREIGN KEY(workspace_name) REFERENCES workspace(name)
                                ); """

            # create tables
            with sqlite3.connect(self.database_file) as db_connection:
                db_cursor = db_connection.cursor()
                db_cursor.execute(binary_cache_table)
                db_cursor.execute(cache_storage_config)
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
    def execute_select(self, statement: str) -> list:
        try:
            with sqlite3.connect(self.database_file) as db_connection:
                db_cursor = db_connection.cursor()
                result = db_cursor.execute(statement).fetchall()
                db_connection.commit()
            return result
        except sqlite3.Error as e:
            print("ERROR: ", e)

    def insert_binary_cache(
        self,
        id: str,
        name: str,
        url: str,
        token: str,
        access: str,
        port: int,
        retention: int,
        storage: str,
    ) -> None:
        statement = """
            INSERT INTO binary_cache (id, name, url, token, access, port, retention, storage)
            VALUES ('{}', '{}', '{}', '{}', '{}', '{}', '{}', '{}')
            ; """.format(
            id,
            name,
            url,
            token,
            access,
            port,
            retention,
            storage,
        )
        self.execute_statement(statement)

    def insert_storage_config(self, cache_id: int, config_key: str, config_value: str):
        statement = """
            INSERT INTO cache_storage_config (cache_id, config_key, config_value)
            VALUES ('{}', '{}', '{}')
            ; """.format(
            cache_id, config_key, config_value
        )
        self.execute_statement(statement)

    def delete_binary_cache(self, name: str) -> None:
        statement = """
            DELETE FROM binary_cache
            WHERE name='{}'
            ; """.format(
            name
        )
        self.execute_statement(statement)

    def delete_cache_storage_config_records(self, cache_id: int) -> None:
        statement = """
            DELETE FROM cache_storage_config
            WHERE cache_id='{}'
            ; """.format(
            cache_id
        )
        self.execute_statement(statement)

    def delete_all_cache_paths(self, name: str) -> None:
        statement = """
            DELETE FROM store_path
            WHERE cache_name='{}'
        ; """.format(
            name
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
        retention: int,
        storage: str,
    ) -> None:
        statement = """
            UPDATE binary_cache
            SET name='{}', url='{}', token='{}', access='{}', port='{}', retention='{}', storage='{}'
            WHERE id='{}'
            ; """.format(
            name, url, token, access, port, retention, storage, id
        )
        self.execute_statement(statement)

    def get_binary_cache_row(self, name: str) -> list | None:
        statement = """
            SELECT * FROM binary_cache
            WHERE name='{}'
            ; """.format(
            name
        )
        db_result = self.execute_select(statement)

        if not db_result:
            return None

        return db_result[0]

    def get_storage_config(self, id: int) -> Dict[str, str]:

        statement = """
            SELECT * FROM cache_storage_config
            WHERE cache_id='{}'
            ; """.format(
            id
        )
        db_result = self.execute_select(statement)

        if not db_result:
            return {}

        storage_config = {}

        for row in db_result:
            storage_config[row[2]] = row[3]

        return storage_config

    def get_binary_cache_row_by_port(self, port: int) -> list | None:
        statement = """
            SELECT * FROM binary_cache
            WHERE port='{}'
            ; """.format(
            port
        )
        db_result = self.execute_select(statement)

        if not db_result:
            return None

        return db_result[0]

    def get_private_cache_list(self) -> list[str]:
        statement = """
            SELECT * FROM binary_cache
            WHERE access='private'
            ; """
        return self.execute_select(statement)

    def get_public_cache_list(self) -> list[str]:
        statement = """
            SELECT * FROM binary_cache
            WHERE access='public'
            ; """
        return self.execute_select(statement)

    def get_cache_list(self) -> list[str]:
        statement = """
            SELECT * FROM binary_cache
            ; """
        return self.execute_select(statement)

    def get_cache_store_paths(self, cache_name: str) -> list:
        statement = """
            SELECT * FROM store_path
            WHERE cache_name='{}'
            ; """.format(
            cache_name
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

    def get_agent_row(self, name: str) -> list | None:
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

    def get_workspace_agents(self, workspace_name: str) -> list[str]:
        statement = """
            SELECT * FROM agent
            WHERE workspace_name='{}'
            ; """.format(
            workspace_name
        )
        return self.execute_select(statement)

    def get_store_path_row(
        self, cache_name: str, store_hash: str = "", file_hash: str = ""
    ) -> list | None:
        if store_hash:
            statement = """
                SELECT * FROM store_path
                WHERE store_hash='{}'
                AND cache_name='{}'
                ; """.format(
                store_hash, cache_name
            )
        else:
            statement = """
                SELECT * FROM store_path
                WHERE file_hash='{}'
                AND cache_name='{}'
                ; """.format(
                file_hash, cache_name
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
        cache_name: str,
    ) -> None:
        statement = """
            INSERT INTO store_path (id, store_hash, store_suffix, file_hash, file_size, nar_hash,
            nar_size, deriver, refs, cache_name)
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
            references,
            cache_name,
        )
        print(statement)
        self.execute_statement(statement)

    def delete_store_path(self, store_hash: str, cache_name: str) -> None:
        statement = """
            DELETE FROM store_path
            WHERE store_hash='{}'
            AND cache_name='{}'
            ; """.format(
            store_hash, cache_name
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

    def get_workspace_row(self, name: str) -> list | None:
        statement = """
            SELECT * FROM workspace
            WHERE name='{}'
            ; """.format(
            name
        )
        db_result = self.execute_select(statement)

        if not db_result:
            return None

        return db_result[0]

    def get_workspace_row_by_token(self, token: str) -> list | None:
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

    def get_workspace_list(self) -> list[str]:
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
