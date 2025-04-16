#!/usr/bin/env python3.12
"""
base

Module containing the BinaryCache class.

Author: Marek Križan, Radim Mifka
Date: 1.5.2024
"""

import base64
import json
import os
import time
from typing import Dict, List, Optional
from cache_server_app.src.types import StorePathRow

import ed25519

import cache_server_app.src.config.base as config
from cache_server_app.src.database import CacheServerDatabase
from cache_server_app.src.storage.manager import StorageManager
from cache_server_app.src.storage.factory import StorageFactory
from cache_server_app.src.cache.access import CacheAccess
from cache_server_app.src.dht import DHT

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
        access: binary cache access
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
    ) -> None:
        self.cache_dir = os.path.join(config.cache_dir, name)
        self.database = CacheServerDatabase()
        self.id = id
        self.name = name
        self.url = url
        self.token = token
        self.access = CacheAccess(access)
        self.port = port
        self.retention = retention
        self.storage = storage
        self.dht = DHT.get_instance()

    @staticmethod
    def exist(id: Optional[str] = None, name: Optional[str] = None, port: Optional[int] = None) -> bool:
        return CacheServerDatabase().get_binary_cache_row(id, name, port) is not None

    @staticmethod
    def get(id: Optional[str] = None, name: Optional[str] = None, port: Optional[int] = None) -> Optional['BinaryCache']:
        database = CacheServerDatabase()
        row = database.get_binary_cache_row(id, name, port)
        if not row:
            return None

        cache_dir = os.path.join(config.cache_dir, row[1])

        storages = []
        for storage in database.get_cache_storages(row[0]):
            storage_id = storage[0]
            storage_name = storage[1]
            storage_type = storage[2]
            storage_config = database.get_storage_config(storage_id)
            storages.append(StorageFactory.create_storage(storage_id, storage_name, storage_type, storage_config, cache_dir))

        return BinaryCache(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            StorageManager(row[0], storages, database)
        )

    def advertise(self) -> None:
        """Advertise the binary cache to the DHT."""

        payload = {
            "name": self.name,
            "host": config.server_hostname,
            "port": self.port,
            "load": '',
            "free_space": '',
        }

        data = json.dumps(payload)
        self.dht.put(f"cache:{self.id}", data)

    def save(self) -> None:
        self.database.insert_binary_cache(
            self.id,
            self.name,
            self.url,
            self.token,
            self.access.value,
            self.port,
            self.retention,
        )

    def update(self) -> None:
        self.database.update_binary_cache(
            self.id,
            self.name,
            self.url,
            self.token,
            self.access.value,
            self.port,
            self.retention,
        )

    def delete(self) -> None:
        self.database.delete_storage(self.id)
        self.database.delete_binary_cache(self.id)

    def cache_json(self, permission: str) -> str:
        public_key = self.storage.read("key.pub")

        return json.dumps(
            {
                "githubUsername": "",
                "isPublic": (self.access == CacheAccess.PUBLIC.value),
                "name": self.name,
                "permission": permission,  # TODO
                "preferredCompressionMethod": "XZ",
                "publicSigningKeys": [public_key],
                "uri": self.url,
            }
        )

    def cache_workspace_dict(self) -> Dict[str, str | bool]:
        public_key = self.storage.read("key.pub")

        return {
            "cacheName": self.name,
            "isPublic": (self.access == CacheAccess.PUBLIC.value),
            # !TODO: CHECK THIS
            "publicKey": public_key.split(":")[1],
        }

    def get_store_hashes(self) -> List[str]:
        return [path[1] for path in self.storage.get_store_paths()]

    def get_missing_store_hashes(self, hashes: List[str]) -> List[str]:
        return [
            store_hash
            for store_hash in hashes
            if store_hash not in self.get_store_hashes()
        ]

    def get_paths(self) -> List[StorePathRow]:
        return self.storage.get_store_paths()

    def update_workspaces(self, new_name: str) -> None:
        self.database.update_cache_in_workspaces(self.name, new_name)

    def update_paths(self, new_name: str) -> None:
        self.database.update_cache_in_paths(self.name, new_name)

    def garbage_collector(self) -> None:
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
