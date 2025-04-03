#!/usr/bin/env python3.12
"""
binary_cache

Module containing the StorageManager class.

Author: Marek Križan, Radim Mifka
Date: 1.5.2024
"""

import uuid

from typing import List
from cache_server_app.src.storage.base import Storage
from cache_server_app.src.database import CacheServerDatabase
from cache_server_app.src.storage.factory import StorageFactory

class StorageManager:
    def __init__(self, cache_id: str, storages: List[Storage], database: CacheServerDatabase | None = None):
        self.cache_id = cache_id
        self.storages = storages
        self.database = database or CacheServerDatabase()

    def __str__(self) -> str:
        return ", ".join([str(storage) for storage in self.storages])

    def get_store_paths(self):
        ids = [storage.id for storage in self.storages]
        return self.database.get_storages_store_paths(ids)

    def get_store_path(self, store_hash: str = "", file_hash: str = ""):
        ids = [storage.id for storage in self.storages]
        return self.database.get_store_path_row(ids, store_hash, file_hash)

    def get_storage(self, id: str | None = None, name: str | None = None) -> Storage | None:
        for storage in self.storages:
            if storage.id == id or storage.name == name:
                return storage
        return None

    def add_storage(self, name: str, type: str, config: dict, cache_dir: str):
        id = str(uuid.uuid1())
        storage = StorageFactory.create_storage(id, name, type, config, cache_dir)

        self.storages.append(storage)
        self.database.insert_cache_storage(storage.id, storage.name, storage.type, self.cache_id)
        for key, value in storage.config.items():
            self.database.insert_storage_config(storage.id, key, value)

    def remove_storage(self, id: str | None = None, name: str | None = None):
        for i, storage in enumerate(self.storages):
            if storage.id == id or storage.name == name:
                self.storages.pop(i)
                self.database.delete_storage(storage.id)
                break

    def update_storage(self, name: str, type: str, config: dict):
        for storage in self.storages:
            if storage.name == name:
                self.database.update_storage(storage.id, type)
                self.database.delete_storage_config(storage.id)
                for key, value in config.items():
                    self.database.insert_storage_config(storage.id, key, value)

    def new_file(self, path: str, data: bytes = b""):
        # TODO choose right storage
        self.storages[0].new_file(path, data)

    def read(self, path: str, binary: bool = False) -> str | bytes:
        # TODO choose right storage
        return self.storages[0].read(path, binary)

    def find(self, path: str) -> bool:
        # TODO choose right storage
        pass
    def save(self, path: str, data: bytes):
        # TODO choose right storage
        self.storages[0].save(path, data)
    def remove(self, path: str):
        # TODO choose right storage
        self.storages[0].remove(path)
    def rename(self, path: str, new_path: str):
        # TODO choose right storage
        self.storages[0].rename(path, new_path)

