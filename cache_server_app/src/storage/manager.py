#!/usr/bin/env python3.12
"""
manager

Abstraction above more possible storages for cache instance

Author: Radim Mifka

Date: 3.4.2025
"""

import uuid
import os
import json

from typing import Dict, List, Literal, Optional, Tuple, overload
from cache_server_app.src.storage.base import Storage
from cache_server_app.src.database import CacheServerDatabase
from cache_server_app.src.storage.factory import StorageFactory
from cache_server_app.src.storage.type import StorageType
from cache_server_app.src.types import StorePathRow
from cache_server_app.src.storage.strategies import Strategy

class StorageManager:
    def __init__(self, cache_id: str, storages: List[Storage], strategy: str, strategy_state: dict = {}, database: Optional[CacheServerDatabase] = None) -> None:
        self.cache_id = cache_id
        self.storages = storages
        self.strategy_state = strategy_state
        self.strategy = Strategy(strategy)
        self.database = database or CacheServerDatabase()

    def __str__(self) -> str:
        return ", ".join([str(storage) for storage in self.storages])

    def get_storage(self, id: str | None = None, name: str | None = None) -> Optional[Storage]:
        for storage in self.storages:
            if storage.id == id or storage.name == name:
                return storage
        return None

    def get_storage_by_type(self, type: str) -> List[Storage]:
        return [storage for storage in self.storages if storage.type == type]

    def get_store_paths(self) -> List[StorePathRow]:
        storage_ids = [storage.id for storage in self.storages]
        return self.database.get_store_paths(storage_ids)

    def get_store_path(self, store_hash: str = "", file_hash: str = "") -> StorePathRow | None:
        storage_ids = [storage.id for storage in self.storages]
        return self.database.get_store_path_row(storage_ids, store_hash, file_hash)

    def add_storage(self, name: str, type: str, root: str, config: dict) -> None:
        id = str(uuid.uuid1())
        storage = StorageFactory.create_storage(id, name, type, root, config)

        self.storages.append(storage)
        self.database.insert_cache_storage(storage.id, storage.name, storage.type, storage.root, self.cache_id)
        for key, value in storage.config.items():
            self.database.insert_storage_config(storage.id, key, value)

    def remove_storage(self, id: str | None = None, name: str | None = None) -> None:
        for i, storage in enumerate(self.storages):
            if storage.id == id or storage.name == name:
                self.storages.pop(i)
                self.database.delete_storage(storage.id)
                break

    def update_storage(self, name: str, type: str, root: str, config: Dict[str, str]) -> None:
        for storage in self.storages:
            if storage.name == name:
                self.database.update_storage(storage.id, type, root)
                self.database.delete_storage_config(storage.id)
                for key, value in config.items():
                    self.database.insert_storage_config(storage.id, key, value)

    def _choose_storage(self) -> Storage:

        if len(self.storages) == 1:
            if self.storages[0].is_full():
                print(f"ERROR: Storage {self.storages[0].name} is full.")
                raise Exception("Storage is full")
            return self.storages[0]

        try:
            storage = self.strategy.func(self.storages, self.strategy_state)
        except Exception as e:
            print(f"ERROR: Failed to choose storage: {e}")
            raise

        # this could be probbly moved to some part when the server is stopped
        # not really needed to be done every time when the storage is chosen
        # because the instance holds the state itself
        self.database.update_storage_strategy_state(self.cache_id, self.strategy, json.dumps(self.strategy_state))

        return storage

    def new_file(self, path: str, data: bytes = b"", all: bool = False) -> None:
        if all:
            for storage in self.storages:
                storage.new_file(path, data)
            return

        storage = self._choose_storage()
        storage.new_file(path, data)

    @overload
    def read(self, path: str, binary: Literal[True]) -> bytes: ...

    @overload
    def read(self, path: str, binary: Literal[False]) -> str: ...

    @overload
    def read(self, path: str) -> str: ...

    def read(self, path: str, binary: bool = False) -> str | bytes:
        storage = self._choose_storage()

        # for mypy to understand the overload
        if binary:
            return storage.read(path, True)
        else:
            return storage.read(path, False)

    def find(self, path: str) -> Optional[Tuple[str, Storage]]:
        for storage in self.storages:
            finding = storage.find(path)
            if finding:
                return finding, storage
        return None

    def save(self, path: str, data: bytes) -> None:
        storage = self._choose_storage()
        storage.save(path, data)

    def remove(self, path: str) -> None:
        storage = self._choose_storage()
        storage.remove(path)

    def rename(self, path: str, new_path: str) -> None:
        storage = self._choose_storage()
        storage.rename(path, new_path)

    def get_available_space(self) -> int:
        """Get the available space in bytes."""
        space = 0

        seen_disk_ids = set()

        for storage in self.storages:
            if storage.type == StorageType.LOCAL.value:
                path = storage.root
                try:
                    device_id = os.stat(path).st_dev
                except FileNotFoundError:
                    print(f"ERROR: Can't get device id for {path}.")
                    continue

                # don't count the same disk twice
                if device_id in seen_disk_ids:
                    continue

                space += storage.get_available_space()
                seen_disk_ids.add(device_id)
            else:
                # non-local storages
                space += storage.get_available_space()

        return space


