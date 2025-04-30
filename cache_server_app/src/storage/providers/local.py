"""
local

This module contains the implementation of the LocalStorage class, which is a subclass of the Storage class.

Author: Radim Mifka

Date: 5.12.2024
"""

import os
from typing import Dict
from datetime import datetime, timezone

from cache_server_app.src.storage.base import Storage, StorageConfig
from cache_server_app.src.storage.registry import StorageRegistry
from cache_server_app.src.storage.type import StorageType
from cache_server_app.src.storage.constants import CONSIDERED_NEW_FILE_AGE, DIR_PERMISSIONS, MAX_STORAGE_USAGE

@StorageRegistry.register(StorageType.LOCAL)
class LocalStorage(Storage):
    @classmethod
    def get_config_requirements(cls) -> StorageConfig:
        """Get the configuration requirements for local storage."""
        return StorageConfig(
            required=[],
            prefix="",
            config_key=StorageType.LOCAL.value,
        )

    def setup(self, config: Dict[str, str], path: str) -> None:
        if os.path.exists(path):
            return
        try:
            os.makedirs(path, mode=DIR_PERMISSIONS, exist_ok=True)
        except PermissionError:
            print(f"ERROR: Can't create directory {path}. Permission denied.")
            exit(1)
        except Exception:
            print(f"ERROR: Failed to create directory {path}.")
            exit(1)

    def get_type(self) -> str:
        return StorageType.LOCAL

    def new_file(self, path: str, data: bytes = b"") -> None:
        path = os.path.join(self.storage_path, path)
        with open(path, "wb") as f:
            f.write(data)

    def save(self, path: str, data: bytes) -> None:
        path = os.path.join(self.storage_path, path)
        with open(path, "wb") as f:
            f.write(data)

    def remove(self, path: str) -> None:
        path = os.path.join(self.storage_path, path)
        os.remove(path)

    def clear(self) -> None:
        for dirpath, _, filenames in os.walk(self.storage_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                print(f"Removing {filepath}")
                # os.remove(filepath)

    def read(self, path: str, binary: bool = False) -> str | bytes:
        path = os.path.join(self.storage_path, path)
        with open(path, "rb" if binary else "r") as f:
            return f.read()

    def rename(self, path: str, new_name: str) -> None:
        path = os.path.join(self.storage_path, path)
        new_path = os.path.join(self.storage_path, new_name)

        os.rename(path, new_path)

    def list(self) -> list[str]:
        return os.listdir(self.storage_path)

    def get_file_creation_time(self, path: str) -> datetime:
        path = os.path.join(self.storage_path, path)
        file_mod_time = os.path.getmtime(path)
        return datetime.fromtimestamp(file_mod_time, tz=timezone.utc)

    def is_new_file(self, path: str) -> bool:
        file_mod_time = self.get_file_creation_time(path)
        file_mod_time_utc = file_mod_time.astimezone(timezone.utc)
        current_time_utc = datetime.now(timezone.utc)

        return (current_time_utc - file_mod_time_utc).total_seconds() <= CONSIDERED_NEW_FILE_AGE

    def find(self, name: str, strict: bool = False) -> str | None:
        for file in os.listdir(self.storage_path):
            if strict and name == file:
                return file
            elif not strict and name in file:
                return file
        return None

    def get_available_space(self) -> int:
        """Get the available space in bytes."""
        statvfs = os.statvfs(self.storage_path)
        return statvfs.f_bavail * statvfs.f_frsize

    def get_used_space(self) -> int:
        """Get the used space in bytes."""
        space = 0
        for dirpath, _, filenames in os.walk(self.storage_path):
            for filename in filenames:
                filepath = os.path.join(dirpath, filename)
                space += os.path.getsize(filepath)
        return space

    def is_full(self) -> bool:
        normalized_used_space = self.get_used_space() / self.get_available_space() * 0.01
        return normalized_used_space > MAX_STORAGE_USAGE
