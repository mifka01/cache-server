#!/usr/bin/env python3.12
"""
config

This module contains the configuration validation for storage types.

Author: Radim Mifka
Date: 5.12.2024
"""

from typing import Dict, Optional

from cache_server_app.src.storage.registry import StorageRegistry
from cache_server_app.src.storage.type import StorageType


def get_storage_config(cache_config: Dict[str, str], storage_type: str) -> Optional[Dict[str, str]]:
    """Get the storage configuration for a given storage type."""
    storage_class = StorageRegistry.get_class(storage_type)
    if not storage_class:
        print(f"ERROR: Unknown storage type: {storage_type}")
        return None

    config = storage_class.get_config_requirements()
    storage_config = {}

    for key, value in cache_config.items():
        if key.startswith(config.prefix):
            storage_config[key] = value

    missing_keys = [
        key for key in config.required
        if f"{config.prefix}{key}" not in storage_config
    ]

    if missing_keys:
        print(f"ERROR: Missing required configuration for {storage_type}: {', '.join(missing_keys)}")
        return None

    return storage_config
