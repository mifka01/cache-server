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
from typing import Any, Callable, Dict, List
import signal
import threading

from cache_server_app.src.storage.strategies import Strategy
import jwt

import cache_server_app.src.config.base as config
from cache_server_app.src.api.cache import BinaryCacheRequestHandler, HTTPBinaryCache
from cache_server_app.src.cache.base import BinaryCache, CacheAccess
from cache_server_app.src.commands.base import BaseCommand
from cache_server_app.src.storage.factory import StorageFactory
from cache_server_app.src.storage.manager import StorageManager


class CacheCommands(BaseCommand):
    """Handles all cache-related commands."""

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
        cache_token = jwt.encode({"name": name}, config.key, algorithm="HS256")

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

        print(f"Binary cache started http://{config.server_hostname}:{cache.port}")
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
            if name == workspace[3]:
                print(
                    f"ERROR: Binary cache {name} is connected to workspace {workspace[1]}."
                )
                sys.exit(1)
        #
        # pid_file = f"/var/run/{cache.id}.pid"
        # if self.get_pid(pid_file):
        #     print(f"ERROR: Binary cache {name} is running.")
        #     sys.exit(1)

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
            if not BinaryCache.get(new_name):
                # !! TODO !!
                # os.rename(cache.cache_dir, os.path.join(config.cache_dir, new_name))
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
            f"Storage: {cache.storage}"
        )
        print(output)


    def execute(self, command: str, *args: Any, **kwargs: Any) -> None:
        """Execute the specified cache command."""

        commands: dict[str, Callable[..., None]] = {
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
