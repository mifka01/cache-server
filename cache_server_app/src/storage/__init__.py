"""
Storage package initialization.

This module imports all storage implementations to ensure they are registered.
"""

import os
import importlib

storage_dir = os.path.dirname(__file__) + "/providers"
for filename in os.listdir(storage_dir):
    if filename.endswith(".py") and not filename.startswith("_"):
        module_name = f"cache_server_app.src.storage.providers.{filename[:-3]}"
        try:
            importlib.import_module(module_name)
        except Exception as e:
            print(f"Warning: Failed to import storage module {module_name}: {e}")
