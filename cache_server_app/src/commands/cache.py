#!/usr/bin/env python3.12
"""
cache

Cache command handlers.

Author: Radim Mifka
Date: 1.5.2024
"""

import os
import shutil
import sys
import uuid
from typing import Any

import jwt

import cache_server_app.src.config as config
from cache_server_app.src.api import BinaryCacheRequestHandler, HTTPBinaryCache
from cache_server_app.src.binary_cache import BinaryCache
from cache_server_app.src.commands.base import BaseCommand
from cache_server_app.src.storage.factory import StorageFactory


class CacheCommands(BaseCommand):
    """Handles all cache-related commands."""

    def create(self, name: str, port: int, storage: str, retention: int | None, storage_config: dict[str, str] | None) -> None:
        """Create a new binary cache."""
        if BinaryCache.get(name):
            print(f"ERROR: Binary cache {name} already exists.")
            sys.exit(1)

        if BinaryCache.get_by_port(port):
            print(f"ERROR: There already is binary cache with port {port} specified.")
            sys.exit(1)

        if not retention:
            retention = -1

        cache_url = f"http://{name}.{config.server_hostname}"
        cache_id = str(uuid.uuid1())
        cache_token = jwt.encode({"name": name}, config.key, algorithm="HS256")
        cache_dir = os.path.join(config.cache_dir, name)

        storage = StorageFactory.create_storage(storage, storage_config, cache_dir)

        cache = BinaryCache(
            cache_id,
            name,
            cache_url,
            cache_token,
            "public",
            port,
            retention,
            storage,
        )
        cache.generate_keys()
        cache.save()

    def start(self, name: str) -> None:
        """Start a binary cache."""
        cache = BinaryCache.get(name)
        if not cache:
            print(f"ERROR: Binary cache {name} does not exist.")
            sys.exit(1)

        if self.get_pid(f"/var/run/{cache.id}.pid"):
            print(f"ERROR: Binary cache {name} is already running.")
            sys.exit(1)

        server = HTTPBinaryCache(
            (config.server_hostname, cache.port),
            BinaryCacheRequestHandler,
            cache
        )
        print(f"Binary cache started http://localhost:{cache.port}")
        server.serve_forever()

    def stop(self, name: str) -> None:
        """Stop a binary cache."""
        cache = BinaryCache.get(name)
        if not cache:
            print(f"ERROR: Binary cache {name} does not exist.")
            sys.exit(1)

        pid_file = f"/var/run/{cache.id}.pid"
        pid = self.get_pid(pid_file)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print("Server stopped.")
                self.remove_pid(pid_file)
            except ProcessLookupError:
                print("Server is not running.")
                self.remove_pid(pid_file)
        else:
            print("Server is not running.")
            sys.exit(1)

    def delete(self, name: str) -> None:
        """Delete a binary cache."""
        cache = BinaryCache.get(name)
        if not cache:
            print(f"ERROR: Binary cache {name} does not exist.")
            sys.exit(1)

        for workspace in self.database.get_workspace_list():
            if name == workspace[3]:
                print(
                    f"ERROR: Binary cache {name} is connected to workspace {workspace[1]}."
                )
                sys.exit(1)

        pid_file = f"/var/run/{cache.id}.pid"
        if self.get_pid(pid_file):
            print(f"ERROR: Binary cache {name} is running.")
            sys.exit(1)

        cache_dir = os.path.join(config.cache_dir, name)
        try:
            shutil.rmtree(cache_dir)
        except PermissionError:
            print(f"ERROR: Can't delete directory {cache_dir}. Permission denied.")
            sys.exit(1)
        cache.delete()

    def update(self, name: str, new_name: str | None, access: str | None, retention: int | None, port: int | None) -> None:
        """Update a binary cache."""
        cache = BinaryCache.get(name)
        if not cache:
            print(f"ERROR: Binary cache {name} does not exist.")
            sys.exit(1)

        if self.get_pid(f"/var/run/{cache.id}.pid"):
            print(f"ERROR: Binary cache {name} is running.")
            sys.exit(1)

        if access:
            cache.access = access

        if new_name:
            if not BinaryCache.get(new_name):
                os.rename(cache.cache_dir, os.path.join(config.cache_dir, new_name))
                cache.update_workspaces(new_name)
                cache.update_paths(new_name)
                cache.name = new_name
                cache.url = f"http://{new_name}.{config.server_hostname}"
                cache.token = jwt.encode(
                    {"name": new_name}, config.key, algorithm="HS256"
                )
            else:
                print(
                    f"ERROR: Binary cache {new_name} already exists. Name won't be changed."
                )

        if retention:
            cache.retention = retention

        if port:
            cache.port = port

        cache.update()

    def list(self, private: bool, public: bool) -> None:
        """List binary caches."""
        db_result = []
        if private:
            db_result = self.database.get_private_cache_list()
        elif public:
            db_result = self.database.get_public_cache_list()
        else:
            db_result = self.database.get_cache_list()

        for row in db_result:
            print(row[1])

    def info(self, name: str) -> None:
        """Get information about a binary cache."""
        cache = BinaryCache.get(name)
        if not cache:
            print(f"ERROR: Binary cache {name} does not exist.")
            sys.exit(1)

        if cache.retention == -1:
            retention = None
        else:
            retention = cache.retention

        output = f"Id: {cache.id}\nName: {cache.name}\nUrl: {cache.url}\nToken: {cache.token}\nAccess: {cache.access}\nPort: {cache.port}\nRetention: {retention}\nStorage: {cache.storage}"
        print(output)

    def execute(self, command: str, *args: Any, **kwargs: Any) -> None:
        """Execute the specified cache command."""
        commands = {
            "create": self.create,
            "start": self.start,
            "stop": self.stop,
            "delete": self.delete,
            "update": self.update,
            "list": self.list,
            "info": self.info,
        }
        
        if command not in commands:
            raise ValueError(f"Unknown cache command: {command}")
            
        commands[command](*args, **kwargs) 