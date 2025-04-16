"""
local

This module contains the implementation of the LocalStorage class, which is a subclass of the Storage class.

Author: Radim Mifka
Date: 5.12.2024
"""

import os
from typing import Dict

from cache_server_app.src.storage.base import Storage, StorageConfig
from cache_server_app.src.storage.registry import StorageRegistry
from cache_server_app.src.storage.type import StorageType


@StorageRegistry.register(StorageType.LOCAL)
class LocalStorage(Storage):
    @classmethod
    def get_config_requirements(cls) -> StorageConfig:
        """Get the configuration requirements for local storage."""
        return StorageConfig(
            required=[],
            prefix="",
            config_key="local"
        )

    def setup(self, config: Dict[str, str], path: str) -> None:
        if os.path.exists(path):
            return
        try:
            os.makedirs(path, mode=0o755)
        except PermissionError:
            print(f"ERROR: Can't create directory {path}. Permission denied.")
            exit(1)
        except Exception:
            print(f"ERROR: Failed to create directory {path}.")
            exit(1)

    def get_type(self) -> str:
        return StorageType.LOCAL

    def new_file(self, path: str, data: bytes = b"") -> None:
        path = os.path.join(self.root, path)
        with open(path, "wb") as f:
            f.write(data)

    def save(self, path: str, data: bytes) -> None:
        path = os.path.join(self.root, path)
        with open(path, "wb") as f:
            f.write(data)

    def remove(self, path: str) -> None:
        path = os.path.join(self.root, path)
        os.remove(path)

    def read(self, path: str, binary: bool = False) -> str | bytes:
        path = os.path.join(self.root, path)
        with open(path, "rb" if binary else "r") as f:
            return f.read()

    def rename(self, path: str, new_name: str) -> None:
        path = os.path.join(self.root, path)
        new_path = os.path.join(self.root, new_name)

        os.rename(path, new_path)

    def list(self) -> list[str]:
        return os.listdir(self.root)

    def find(self, name: str, strict: bool = False) -> str | None:
        for file in os.listdir(self.root):
            if strict and name == file:
                return file
            elif not strict and name in file:
                return file
        return None
