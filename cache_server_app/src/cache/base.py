#!/usr/bin/env python3.12
"""
base

Module containing the BinaryCache class.

Author: Marek Križan, Radim Mifka

Date: 1.5.2024
"""

import base64
import json
import time
from typing import Dict, List, Optional
from datetime import datetime, timedelta, timezone
from cache_server_app.src.cache.constants import ADVERTISING_INTERVAL, GARBAGE_COLLECTION_INTERVAL
from cache_server_app.src.types import BinaryCacheRow, StorePathRow
from cache_server_app.src.cache.metrics import CacheMetrics

import ed25519

import cache_server_app.src.config.base as config
from cache_server_app.src.database import CacheServerDatabase
from cache_server_app.src.storage.manager import StorageManager
from cache_server_app.src.storage.factory import StorageFactory
from cache_server_app.src.cache.access import CacheAccess
from cache_server_app.src.dht.client import DHTClient

class BinaryCache:
    """
    Class to represent binary cache.

    Attributes:
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
        self.database = CacheServerDatabase()
        self.id = id
        self.name = name
        self.url = url
        self.token = token
        self.access = CacheAccess(access)
        self.port = port
        self.retention = retention
        self.storage = storage
        self.dht = DHTClient(token)
        self.metrics = CacheMetrics(self.id)

    @staticmethod
    def exist(id: Optional[str] = None, name: Optional[str] = None, port: Optional[int] = None) -> bool:
        return CacheServerDatabase().get_binary_cache_row(id, name, port) is not None

    @staticmethod
    def get_rows() -> List[BinaryCacheRow]:
        return CacheServerDatabase().get_binary_caches()

    @staticmethod
    def get(id: Optional[str] = None, name: Optional[str] = None, port: Optional[int] = None) -> Optional['BinaryCache']:
        database = CacheServerDatabase()
        row = database.get_binary_cache_row(id, name, port)
        if not row:
            return None

        storages = []
        for storage in database.get_cache_storages(row[0]):
            storage_id = storage[0]
            storage_name = storage[1]
            storage_type = storage[2]
            storage_root = storage[3]
            storage_config = database.get_storage_config(storage_id)
            storages.append(StorageFactory.create_storage(storage_id, storage_name, storage_type, storage_root, storage_config))

        return BinaryCache(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            StorageManager(row[0], storages, row[7], json.loads(str(row[8])), database)
        )

    def is_public(self) -> bool:
        return self.access == CacheAccess.PUBLIC

    def is_private(self) -> bool:
        return self.access == CacheAccess.PRIVATE

    def save(self) -> None:
        self.database.insert_binary_cache(
            self.id,
            self.name,
            self.url,
            self.token,
            self.access.value,
            self.port,
            self.retention,
            self.storage.strategy,
            json.dumps(self.storage.strategy_state),
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
            self.storage.strategy,
            json.dumps(self.storage.strategy_state),
        )

    def delete(self) -> None:
        self.storage.delete()
        self.database.delete_binary_cache(self.id)

    def cache_json(self, permission: str) -> str:
        public_key = self.storage.read("key.pub")

        return json.dumps(
            {
                "githubUsername": "",
                "isPublic": self.is_public(),
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
            "isPublic": self.is_public(),
            "publicKey": public_key.split(":")[1],
        }

    def get_store_hashes(self) -> List[str]:
        return [path[1] for path in self.storage.get_store_paths()]

    def get_missing_store_hashes(self, hashes: List[str]) -> List[str]:
        known = set(self.get_store_hashes())
        return [store_hash for store_hash in hashes if store_hash not in known]

    def get_paths(self) -> List[StorePathRow]:
        return self.storage.get_store_paths()

    def advertise(self) -> None:
        """
        Advertise the cache to the DHT. DHT values are public, so private caches
        are never advertised and credentials are never part of the payload.
        """
        if self.is_private():
            return

        payload = {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "access": str(self.access),
            "port": self.port,
            "metrics": self.metrics.to_dict(),
            "available_space": self.storage.get_available_space(),
            "retention": self.retention,
            "storage": str(self.storage),
        }

        self.dht.put(self.id, json.dumps(payload), False)

    def sync(self) -> None:
        """
        Synchronize the cache with the DHT.
        """

        if self.is_private():
            return

        self.advertise()
        paths = self.storage.get_store_paths()

        for path in paths:
            store_hash = path[1]
            self.dht.put(store_hash, self.id)


    def advertise_periodically(self) -> None:
        """
        Periodically advertise the cache to the DHT.
        """
        while True:
            time.sleep(ADVERTISING_INTERVAL * 60) # minutes to seconds
            self.advertise()

    def garbage_collector(self) -> None:
        while True:
            time.sleep(GARBAGE_COLLECTION_INTERVAL * 3600) # hours to seconds
            try:
                self.collect_garbage()
            except Exception as e:
                print(f"ERROR: Garbage collection of cache {self.name} failed: {e}")

    def collect_garbage(self) -> None:
        """Remove expired store paths nothing live depends on, then files without a store path.

        A store path is live while its NAR is younger than the retention; everything a
        live path references, directly or transitively, is kept so its closure stays
        complete. A retention of 0 or less keeps store paths forever.
        """
        if self.retention > 0:
            self._remove_expired_paths(self.storage.get_store_paths())
        self._remove_orphaned_files(self.storage.get_store_paths())

    def _remove_expired_paths(self, rows: List[StorePathRow]) -> None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=self.retention)
        # NAR files are named "{file_hash}.nar.{compression}"
        nar_files = {
            storage.id: {name.split(".", 1)[0]: name for name in storage.list() if ".nar." in name}
            for storage in self.storage.storages
        }
        by_name = {f"{row[1]}-{row[2]}": row for row in rows}

        live: List[str] = []
        expired = []
        for row in rows:
            storage = self.storage.get_storage(row[9])
            nar_file = nar_files.get(row[9], {}).get(row[3])
            if storage and nar_file and storage.get_file_creation_time(nar_file) > cutoff:
                live.append(f"{row[1]}-{row[2]}")
            else:
                expired.append((row, storage, nar_file))

        keep = set()
        while live:
            name = live.pop()
            if name in keep:
                continue
            keep.add(name)
            referrer = by_name.get(name)
            if referrer and referrer[8]:
                live.extend(referrer[8].split(" "))

        for row, storage, nar_file in expired:
            if f"{row[1]}-{row[2]}" in keep:
                continue
            print(f"Removing expired store path {row[1]}-{row[2]} from cache {self.name}")
            if storage and nar_file:
                storage.remove(nar_file)
            self.database.delete_store_path(row[1], row[9])

    def _remove_orphaned_files(self, rows: List[StorePathRow]) -> None:
        """Remove files no store path refers to, except keys and recent ones (uploads in progress)."""
        referenced = {(row[9], row[3]) for row in rows}
        for storage in self.storage.storages:
            for name in storage.list():
                if name.startswith("key.") or (storage.id, name.split(".", 1)[0]) in referenced:
                    continue
                if storage.is_new_file(name):
                    continue
                print(f"Removing file {name} from storage {storage.name}")
                storage.remove(name)

    def generate_keys(self) -> None:
        sk, pk = ed25519.create_keypair()

        prefix = "{}.{}-1:".format(self.name, config.server_hostname).encode("utf-8")

        self.storage.new_file(
            "key.priv",
            prefix + base64.b64encode(sk.to_bytes()), True
        )

        self.storage.new_file(
            "key.pub",
            prefix + base64.b64encode(pk.to_bytes()), True
        )
