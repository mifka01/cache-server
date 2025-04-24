#!/usr/bin/env python3.12
"""
registry

Module for automatic storage class registration.

Author: Radim Mifka

Date: 3.4.2025
"""

from typing import Dict, Type, Callable

from cache_server_app.src.storage.base import Storage
from cache_server_app.src.storage.type import StorageType


class StorageRegistry:
    """Registry for storage classes."""

    _classes: Dict[StorageType, Type[Storage]] = {}

    @classmethod
    def register(cls, storage_type: StorageType) -> Callable:
        """Decorator to register a storage class."""
        def decorator(storage_class: Type[Storage]) -> Type[Storage]:
            cls._classes[storage_type] = storage_class
            return storage_class
        return decorator

    @classmethod
    def get_class(cls, storage_type: str) -> Type[Storage]:
        """Get the storage class for a given storage type."""
        return cls._classes[StorageType(storage_type)]


    @classmethod
    def get_all_types(cls) -> list[str]:
        """Get all registered storage types."""
        return [t.value for t in cls._classes.keys()]
