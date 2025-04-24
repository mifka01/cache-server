#!/usr/bin/env python3.12
"""
factory

This module provides factory for storages

Author: Radim Mifka

Date: 5.12.2024
"""

import importlib
from typing import Type, Any

from cache_server_app.src.storage.base import Storage
from cache_server_app.src.storage.type import StorageType


class StorageFactory:
    @staticmethod
    def create_storage(id:str, name: str, type: str, *args: Any) -> Storage:
        try:
            storage_type = StorageType(type.lower())

            #!TODO Check this
            module_name = f"cache_server_app.src.storage.providers.{storage_type.value}"

            class_name = f"{storage_type.value.capitalize()}Storage"
            module = importlib.import_module(module_name)

            storage_class: Type[Storage] = getattr(module, class_name)

            return storage_class(id, name, type, *args)

        except (ValueError, AttributeError) as e:
            raise ValueError(f"Invalid storage type. Valid types are: {StorageType.str()}") from e
