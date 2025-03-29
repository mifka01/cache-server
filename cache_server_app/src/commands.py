#!/usr/bin/env python3.12
"""
commands

Module to handle command execution.

Author: Marek Križan, Radim Mifka
Date: 1.5.2024
"""

import asyncio
import os
import shutil
import signal
import subprocess
import sys
import threading
import uuid

import jwt

import cache_server_app.src.config as config
from cache_server_app.src.agent import Agent
from cache_server_app.src.api import (BinaryCacheRequestHandler,
                                      CacheServerRequestHandler,
                                      HTTPBinaryCache, HTTPCacheServer,
                                      WebSocketConnectionHandler)
from cache_server_app.src.binary_cache import BinaryCache
from cache_server_app.src.database import CacheServerDatabase
from cache_server_app.src.storage.factory import StorageFactory
from cache_server_app.src.store_path import StorePath
from cache_server_app.src.workspace import Workspace


class CacheServerCommandHandler:
    """
    Class to handle command execution.

    Attributes:
        database: object to handle database connection
    """

    def __init__(self):
        self.database = CacheServerDatabase()

    def save_pid(self, filename: str) -> None:
        try:
            with open(filename, "w") as f:
                f.write(str(os.getpid()))
        except PermissionError:
            print("ERROR: Can't create file %s. Permission denied." % filename)
            sys.exit(1)

    def get_pid(self, filename: str) -> int | None:
        try:
            with open(filename, "r") as f:
                return int(f.read().strip())
        except FileNotFoundError:
            return None
        except PermissionError:
            print("ERROR: Can't read file %s. Permission denied." % filename)
            sys.exit(1)

    def remove_pid(self, filename: str) -> None:
        try:
            os.remove(filename)
        except FileNotFoundError:
            pass
        except PermissionError:
            print("ERROR: Can't remove file %s. Permission denied." % filename)
            sys.exit(1)

    # cache-server listen
    def listen_command(self) -> None:
        pid_file = "/var/run/cache-server.pid"
        if self.get_pid(pid_file):
            print("Server is already running.")
            sys.exit(1)

        # subprocess.Popen(["cache-server", "hidden-start", "server"])
        subprocess.Popen([sys.executable, "-m", "cache_server_app.main", "hidden-start", "server"])


    def start_workspace(self, ws_handler) -> None:
        asyncio.run(ws_handler.run())

    def start_server(self) -> None:
        pid_file = "/var/run/cache-server.pid"
        self.save_pid(pid_file)

        ws_handler = WebSocketConnectionHandler(config.deploy_port)
        ws_thread = threading.Thread(target=self.start_workspace, args=(ws_handler,))
        ws_thread.start()
        server = HTTPCacheServer(
            (config.server_hostname, config.server_port),
            CacheServerRequestHandler,
            ws_handler,
        )
        print("Server started http://localhost:%d" % config.server_port)
        CacheServerDatabase().create_database()
        server.serve_forever()

    # cache-server stop
    def stop_command(self):
        pid_file = "/var/run/cache-server.pid"
        pid = self.get_pid(pid_file)
        if pid:
            try:
                os.kill(pid, signal.SIGTERM)
                print("Server stopped.")
                self.remove_pid(pid_file)
            except ProcessLookupError:
                print("ERROR: Server is not running.")
                self.remove_pid(pid_file)
        else:
            print("ERROR: Server is not running.")
            sys.exit(1)

    # cache-server cache create <name> <port> <storage> <config>
    def cache_create(
        self,
        name: str,
        port: int,
        storage: str,
        retention: int | None,
        storage_config: dict[str, str] | None,
    ) -> None:
        if BinaryCache.get(name):
            print("ERROR: Binary cache %s already exists." % name)
            sys.exit(1)

        if BinaryCache.get_by_port(port):
            print("ERROR: There already is binary cache with port %d specified." % port)
            sys.exit(1)

        if not retention:
            retention = -1

        cache_url = "http://{}.{}".format(name, config.server_hostname)
        cache_id = uuid.uuid1()
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
        # try:
        #     os.makedirs(cache.cache_dir)
        # except FileExistsError:
        #     print("ERROR: Directory %s already exists." % cache.cache_dir)
        #     sys.exit(1)
        # except PermissionError:
        #     print(
        #         "ERROR: Can't create directory %s. Permission denied." % cache.cache_dir
        #     )
        #     sys.exit(1)
        cache.generate_keys()
        cache.save()

    # cache-server cache start <name>
    def cache_start(self, name: str) -> None:
        cache = BinaryCache.get(name)
        if not cache:
            print("ERROR: Binary cache %s does not exist." % name)
            sys.exit(1)

        if self.get_pid("/var/run/{}.pid".format(cache.id)):
            print("ERROR: Binary cache %s is already running." % name)
            sys.exit(1)

        subprocess.Popen(
            ["cache-server", "hidden-start", "cache", name, str(cache.port)]
        )

    def start_cache(self, name: str, port: int) -> None:
        cache = BinaryCache.get(name)
        if not cache:
            print("ERROR: Binary cache %s does not exist." % name)
            sys.exit(1)

        pid_file = "/var/run/{}.pid".format(cache.id)
        self.save_pid(pid_file)

        if cache.retention > 0:
            ws_thread = threading.Thread(target=cache.garbage_collector)
            ws_thread.start()

        server = HTTPBinaryCache(
            (config.server_hostname, port), BinaryCacheRequestHandler, cache
        )
        print("Binary cache started http://localhost:%d" % port)
        server.serve_forever()

    # cache-server cache stop <name>
    def cache_stop(self, name: str) -> None:
        cache = BinaryCache.get(name)
        if not cache:
            print("ERROR: Binary cache %s does not exist." % name)
            sys.exit(1)

        pid_file = "/var/run/{}.pid".format(cache.id)
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

    # cache-server cache delete <name>
    def cache_delete(self, name: str) -> None:
        cache = BinaryCache.get(name)
        if not cache:
            print("ERROR: Binary cache %s does not exist." % name)
            sys.exit(1)

        for workspace in self.database.get_workspace_list():
            if name == workspace[3]:
                print(
                    "ERROR: Binary cache %s is connected to workspace %s."
                    % (name, workspace[1])
                )
                sys.exit(1)

        pid_file = "/var/run/{}.pid".format(cache.id)
        if self.get_pid(pid_file):
            print("ERROR: Binary cache %s is running." % name)
            sys.exit(1)

        cache_dir = os.path.join(config.cache_dir, name)
        try:
            shutil.rmtree(cache_dir)
        except PermissionError:
            print("ERROR: Can't delete directory %s. Permission denied." % cache_dir)
            sys.exit(1)
        cache.delete()

    # cache-server agent add <name> <workspace_name>
    def agent_add(self, name: str, workspace_name: str) -> None:
        if Agent.get(name):
            print("ERROR: Agent %s already exists." % (name))
            sys.exit(1)

        workspace = Workspace.get(workspace_name)
        if not workspace:
            print("ERROR: Workspace %s does not exist.")
            sys.exit(1)

        agent_id = str(uuid.uuid1())
        encoded_jwt = jwt.encode({"name": name}, config.key, algorithm="HS256")
        Agent(agent_id, name, encoded_jwt, workspace).save()

    # cache-server agent remove <name>
    def agent_remove(self, name: str) -> None:
        agent = Agent.get(name)
        if not agent:
            print("ERROR: Agent %s does not exist." % (name))
            sys.exit(1)

        agent.delete()

    # cache-server cache update
    def cache_update(
        self,
        name: str,
        new_name: str | None,
        access: str | None,
        retention: int | None,
        port: int | None,
    ) -> None:
        cache = BinaryCache.get(name)
        if not cache:
            print("ERROR: Binary cache %s does not exist." % name)
            sys.exit(1)

        if self.get_pid("/var/run/{}.pid".format(cache.id)):
            print("ERROR: Binary cache %s is running." % name)
            sys.exit(1)

        if access:
            cache.access = access

        if new_name:
            if not BinaryCache.get(new_name):
                os.rename(cache.cache_dir, os.path.join(config.cache_dir, new_name))
                cache.update_workspaces(new_name)
                cache.update_paths(new_name)
                cache.name = new_name
                cache.url = "http://{}.{}".format(new_name, config.server_hostname)
                cache.token = jwt.encode(
                    {"name": new_name}, config.key, algorithm="HS256"
                )
            else:
                print(
                    "ERROR: Binary cache %s already exists. Name won't be changed."
                    % name
                )

        if retention:
            cache.retention = retention

        if port:
            cache.port = port

        cache.update()

    # cache-server cache list
    def cache_list(self, private: bool, public: bool) -> None:
        db_result = []
        if private:
            db_result = self.database.get_private_cache_list()
        elif public:
            db_result = self.database.get_public_cache_list()
        else:
            db_result = self.database.get_cache_list()

        for row in db_result:
            print(row[1])

    # cache-server cache info <name>
    def cache_info(self, name: str) -> None:
        cache = BinaryCache.get(name)
        if not cache:
            print("ERROR: Binary cache %s does not exist." % name)
            sys.exit(1)

        if cache.retention == -1:
            retention = None
        else:
            retention = cache.retention

        output = "Id: {}\nName: {}\nUrl: {}\nToken: {}\nAccess: {}\nPort: {}\nRetention: {}\nStorage: {}".format(
            cache.id,
            cache.name,
            cache.url,
            cache.token,
            cache.access,
            cache.port,
            retention,
            cache.storage,
        )
        print(output)

    # cache-server agent list <workspace_name>
    def agent_list(self, workspace_name: str) -> None:
        workspace = Workspace.get(workspace_name)
        if not workspace:
            print("ERROR: Workspace %s does not exist." % workspace_name)
            sys.exit(1)

        for row in workspace.get_agents():
            print(row[1])

    # cache-server store-path list <cache_name>
    def store_path_list(self, cache_name: str) -> None:
        cache = BinaryCache.get(cache_name)
        if not cache:
            print("ERROR: Binary cache %s does not exist." % cache_name)
            sys.exit(1)

        for path in cache.get_paths():
            print(path[1])

    # cache-server store-path delete <store_hash> <cache_name>
    def store_path_delete(self, cache_name: str, store_hash: str) -> None:
        cache = BinaryCache.get(cache_name)
        if not cache:
            print("ERROR: Binary cache %s does not exist." % cache_name)
            sys.exit(1)

        path = StorePath.get(cache_name, store_hash=store_hash)
        if not path:
            print("ERROR: Store path not found")
            sys.exit(1)

        for file in os.listdir(cache.cache_dir):
            if path.file_hash in file:
                os.remove(os.path.join(cache.cache_dir, file))
        path.delete()

    # cache-server store-path info <store_hash> <cache_name>
    def store_path_info(self, store_hash: str, cache_name: str) -> None:
        cache = BinaryCache.get(cache_name)
        if not cache:
            print("ERROR: Binary cache %s does not exist." % cache_name)
            sys.exit(1)

        path = StorePath.get(cache_name, store_hash=store_hash)
        if not path:
            print("ERROR: Store path not found")
            sys.exit(1)

        output = "Store hash: {}\nStore suffix: {}\nFile hash: {}".format(
            path.store_hash, path.store_suffix, path.file_hash
        )
        print(output)

    # cache-server agent info <name>
    def agent_info(self, name: str) -> None:
        agent = Agent.get(name)
        if not agent:
            print("ERROR: Agent %s does not exist." % name)
            sys.exit(1)

        output = "Id: {}\nName: {}\nToken: {}\nWorkspace: {}".format(
            agent.id, agent.name, agent.token, agent.workspace.name
        )
        print(output)

    # cache-server workspace create <name> <cache_name>
    def workspace_create(self, name: str, cache_name: str) -> None:
        if Workspace.get(name):
            print("ERROR: Workspace %s already exists." % name)
            sys.exit(1)

        cache = BinaryCache.get(cache_name)
        if not cache:
            print("ERROR: Binary cache %s does not exist." % cache_name)
            sys.exit(1)

        encoded_jwt = jwt.encode({"name": name}, config.key, algorithm="HS256")
        workspace_id = str(uuid.uuid1())
        Workspace(workspace_id, name, encoded_jwt, cache).save()

    # cache-server workspace delete <name>
    def workspace_delete(self, name: str) -> None:
        workspace = Workspace.get(name)
        if not workspace:
            print("ERROR: Workspace %s does not exist." % name)
            sys.exit(1)

        workspace.delete()

    # cache-server workspace list
    def workspace_list(self) -> None:
        db_result = self.database.get_workspace_list()

        for row in db_result:
            print(row[1])

    # cache-server workspace info <name>
    def workspace_info(self, name: str) -> None:
        workspace = Workspace.get(name)
        if not workspace:
            print("ERROR: Workspace %s does not exist." % name)
            sys.exit(1)

        output = "Id: {}\nName: {}\nToken: {}\nBinary cache: {}".format(
            workspace.id, workspace.name, workspace.token, workspace.cache.name
        )
        print(output)

    # cache-server workspace cache <name> <cache-name>
    def workspace_cache(self, name: str, cache_name: str) -> None:
        workspace = Workspace.get(name)
        if not workspace:
            print("ERROR: Workspace %s does not exist." % name)
            sys.exit(1)

        cache = BinaryCache.get(cache_name)
        if not cache:
            print("ERROR: Binary cache %s does not exist." % cache_name)
            sys.exit(1)

        workspace.cache = cache
        workspace.update()
