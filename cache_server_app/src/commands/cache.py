#!/usr/bin/env python3.12
"""
cache

Cache command handlers.

Author: Marek Križan, Radim Mifka
Date: 30.3.2025
"""

import os
import sys
import uuid
from typing import Callable, Dict, List
import signal
import threading

from cache_server_app.src.storage.strategies import Strategy

import cache_server_app.src.config.base as config
from cache_server_app.src.api.cache import BinaryCacheRequestHandler, HTTPBinaryCache
from cache_server_app.src.auth import generate_token
from cache_server_app.src.cache.base import BinaryCache, CacheAccess
from cache_server_app.src.commands.base import BaseCommand
from cache_server_app.src.storage.factory import StorageFactory
from cache_server_app.src.storage.manager import StorageManager


class CacheCommands(BaseCommand):
    """Handles all cache-related commands."""

    name = "cache"

    def create(self, name: str, port: int, access:str, retention: int | None, storage_strategy: str, storages: List[Dict[str, str | Dict[str, str]]]) -> None:
        """Create a new binary cache."""
        if BinaryCache.exist(name=name):
            print(f"ERROR: Binary cache {name} already exists.")
            sys.exit(1)

        if BinaryCache.exist(port=port):
            print(f"ERROR: There already is binary cache with port {port} specified.")
            sys.exit(1)

        if access not in CacheAccess.list():
            print(f"ERROR: Access must be one of {CacheAccess.str()}.")
            sys.exit(1)

        if not retention:
            retention = -1

        cache_url = f"http://{name}.{config.server_hostname}"
        cache_id = str(uuid.uuid1())
        cache_token = generate_token()

        storage_instances = []
        state: dict[str, List[str]] = {}

        if storage_strategy == Strategy.SPLIT.value:
            state[Strategy.SPLIT.value] = []

        for storage in storages:
            storage_id = str(uuid.uuid1())
            storage_name = str(storage['name'])
            storage_type = str(storage['type'])
            storage_config = storage['config']
            storage_root = os.path.join(str(storage['root']), name)
            storage_instances.append(StorageFactory.create_storage(storage_id, storage_name, storage_type, storage_root, storage_config))

            if storage_strategy == Strategy.SPLIT.value:
                state[Strategy.SPLIT.value].append(str(storage[Strategy.SPLIT.value]))

        manager = StorageManager(cache_id, storage_instances, storage_strategy, state)

        cache = BinaryCache(
            cache_id,
            name,
            cache_url,
            cache_token,
            access,
            port,
            retention,
            manager
        )
        cache.generate_keys()
        cache.save()

    def start(self, name: str) -> None:
        """Start a binary cache."""
        cache = BinaryCache.get(name=name)
        if not cache:
            print(f"ERROR: Binary cache {name} does not exist.")
            sys.exit(1)

        server = HTTPBinaryCache(
            (config.server_hostname, cache.port),
            BinaryCacheRequestHandler,
            cache
        )

        cache.sync()
        try:
            cg_thread = threading.Thread(target=cache.garbage_collector)
            cg_thread.daemon = True
            cg_thread.start()

            adv_thread = threading.Thread(target=cache.advertise_periodically)
            adv_thread.daemon = True
            adv_thread.start()

            server.serve_forever()
        except KeyboardInterrupt:
            sys.exit(0)

    def stop(self, name: str) -> None:
        """Stop a binary cache."""
        cache = BinaryCache.get(name=name)
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
        cache = BinaryCache.get(name=name)
        if not cache:
            print(f"ERROR: Binary cache {name} does not exist.")
            sys.exit(1)

        for workspace in self.database.get_workspace_list():
            if workspace[3] == cache.id:
                print(
                    f"ERROR: Binary cache {name} is connected to workspace {workspace[1]}."
                )
                sys.exit(1)

        cache.delete()

    def update(self, name: str, new_name: str | None, port: int | None, access: str | None, retention: int | None, storage_strategy: str | None) -> None:
        """Update a binary cache."""
        cache = BinaryCache.get(name=name)
        if not cache:
            print(f"ERROR: Binary cache {name} does not exist.")
            sys.exit(1)

        if self.get_pid(f"/var/run/{cache.id}.pid"):
            print(f"ERROR: Binary cache {name} is running.")
            sys.exit(1)

        if access and access not in CacheAccess.list():
            print(f"ERROR: Access must be one of {CacheAccess.str()}.")
            sys.exit(1)

        if access:
            cache.access = CacheAccess(access)

        if new_name:
            # Workspaces reference the cache by id and storages keep their directories,
            # so renaming only changes the name, URL and token.
            if not BinaryCache.exist(name=new_name):
                cache.name = new_name
                cache.url = f"http://{new_name}.{config.server_hostname}"
                cache.token = generate_token()
            else:
                print(
                    f"ERROR: Binary cache {new_name} already exists. Name won't be changed."
                )

        if retention is not None:
            cache.retention = retention

        if port:
            cache.port = port

        if storage_strategy:
            cache.storage.strategy = Strategy(storage_strategy)

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
        """Display detailed information about a binary cache."""
        cache = BinaryCache.get(name=name)
        if not cache:
            print(f"ERROR: Binary cache '{name}' does not exist.")
            sys.exit(1)

        retention = None if cache.retention == -1 else cache.retention

        strategy = cache.storage.strategy.value
        split_info = ""
        if strategy == Strategy.SPLIT.value:
            split_storages = cache.storage.strategy_state.get(Strategy.SPLIT.value, [])
            split_info = " - " + "/".join(map(str, split_storages))

        output = (
            f"Id: {cache.id}\n"
            f"Name: {cache.name}\n"
            f"Url: {cache.url}\n"
            f"Token: {cache.token}\n"
            f"Access: {cache.access}\n"
            f"Port: {cache.port}\n"
            f"Retention: {retention}\n"
            f"Storage strategy: {strategy}{split_info}\n"
            f"Storage: {cache.storage}\n"
        )
        print(output)

    def handlers(self) -> dict[str, Callable[..., None]]:
        return {
            "create": self.create,
            "start": self.start,
            "stop": self.stop,
            "delete": self.delete,
            "update": self.update,
            "list": self.list,
            "info": self.info,
        }
