#!/usr/bin/env python3.12
"""
binary_cache

Module containing the BinaryCache class.

Author: Marek Križan, Radim Mifka
Date: 1.5.2024
"""

import base64
import json
import os
import time

import ed25519

import cache_server_app.src.config.base as config
from cache_server_app.src.database import CacheServerDatabase
from cache_server_app.src.storage.manager import StorageManager
from cache_server_app.src.storage.factory import StorageFactory
from typing import Optional, Self, Type


class BinaryCache:
    """
    Class to represent binary cache.

    Attributes:
        cache_dir: directory where cache stores NAR files
        database: object to handle database connection
        id: binary cache id
        name: binary cache name
        url: binary cache url
        token: binary cache JWT authentication token
        access: binary cache access ('public'/'private')
        port: port on which binary cache listens
        retention: binary cache retention
        storages: list of storage objects
    """

    def __init__(
        self,
        id: str,
        name: str,
        url: str,
        token: str,
        access: str,
        port: int,
        retention: int,
        storage: StorageManager,
    ):
        self.cache_dir = os.path.join(config.cache_dir, name)
        self.database = CacheServerDatabase()
        self.id = id
        self.name = name
        self.url = url
        self.token = token
        self.access = access
        self.port = port
        self.retention = retention
        self.storage = storage

    @staticmethod
    def exist(id: str | None = None, name: str | None = None, port: int | None = None):
        return CacheServerDatabase().get_binary_cache_row(id, name, port) is not None

    @staticmethod
    def get(id: str | None = None, name: str | None = None, port: int | None = None) -> Optional['BinaryCache']:
        database = CacheServerDatabase()
        row = database.get_binary_cache_row(id, name, port)
        if not row:
            return None

        id = str(row[0])
        name = str(row[1])
        url = str(row[2])
        token = str(row[3])
        access = str(row[4])
        port = int(row[5])
        retention = int(row[6])
        cache_dir = os.path.join(config.cache_dir, name)

        storages = []
        for storage in database.get_cache_storages(id):
            storage_id = storage[0]
            storage_name = storage[1]
            storage_type = storage[2]
            storage_config = database.get_storage_config(storage_id)
            storages.append(StorageFactory.create_storage(storage_id, storage_name, storage_type, storage_config, cache_dir))
        return BinaryCache(
            id, name, url, token, access, port, retention, StorageManager(id, storages, database)
        )

    def save(self) -> None:
        self.database.insert_binary_cache(
            self.id,
            self.name,
            self.url,
            self.token,
            self.access,
            self.port,
            self.retention,
        )

    def update(self) -> None:
        self.database.update_binary_cache(
            self.id,
            self.name,
            self.url,
            self.token,
            self.access,
            self.port,
            self.retention,
        )
        #! TODO Update storages

    def delete(self) -> None:
        self.database.delete_storage(self.id)
        self.database.delete_binary_cache(self.id)

    def cache_json(self, permission: str) -> str:
        public_key = self.storage.read("key.pub")

        return json.dumps(
            {
                "githubUsername": "",
                "isPublic": (self.access == "public"),
                "name": self.name,
                "permission": permission,  # TODO
                "preferredCompressionMethod": "XZ",
                "publicSigningKeys": [public_key],
                "uri": self.url,
            }
        )

    def cache_workspace_dict(self) -> dict:

        public_key = self.storage.read("key.pub")

        return {
            "cacheName": self.name,
            "isPublic": (self.access == "public"),
            # !TODO: CHECK THIS
            "publicKey": public_key.split(":")[1],
        }

    def get_store_hashes(self) -> list[str]:
        return [path[1] for path in self.storage.get_store_paths()]

    def get_missing_store_hashes(self, hashes: list) -> list:
        return [
            store_hash
            for store_hash in hashes
            if store_hash not in self.get_store_hashes()
        ]

    def get_paths(self) -> list:
        return self.storage.get_store_paths()

    def update_workspaces(self, new_name: str) -> None:
        self.database.update_cache_in_workspaces(self.name, new_name)

    def update_paths(self, new_name: str) -> None:
        self.database.update_cache_in_paths(self.name, new_name)

    def garbage_collector(self):
        while True:
            self.collect_garbage()
            time.sleep(3600)

    def collect_garbage(self) -> None:
        # TODO: Implement garbage collection
        for file in os.listdir(self.cache_dir):
            file_age = (
                os.path.getctime(os.path.join(self.cache_dir, file)) - time.time()
            ) / 604800
            if file_age > self.retention:
                os.remove(file)

    def generate_keys(self) -> None:
        sk, pk = ed25519.create_keypair()

        prefix = "{}.{}-1:".format(self.name, config.server_hostname).encode("utf-8")

        self.storage.new_file(
            "key.priv",
            prefix + base64.b64encode(sk.to_bytes()),
        )

        self.storage.new_file(
            "key.pub",
            prefix + base64.b64encode(pk.to_bytes()),
        )
