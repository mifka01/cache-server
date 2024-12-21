#!/usr/bin/env python3.12
"""
argument_parsing

Module to define the cache-server CLI and to parse command line arguments.

Author: Marek Križan, Radim Mifka
Date: 1.5.2024
"""

import argparse
import sys

from cache_server_app.src.commands import CacheServerCommandHandler
from cache_server_app.src.parser.base import parse


def handle_arguments(argv) -> None:
    arguments = parse(argv)
    command_handler = CacheServerCommandHandler()

    if arguments.command == "listen":
        command_handler.listen_command()

    elif arguments.command == "hidden-start":
        if arguments.start_command == "server":
            command_handler.start_server()
        elif arguments.start_command == "cache":
            command_handler.start_cache(arguments.name, arguments.port)

    elif arguments.command == "stop":
        command_handler.stop_command()

    else:

        if not command_handler.get_pid("/var/run/cache-server.pid"):
            print("ERROR: cache-server is not running.")
            sys.exit(1)

        if arguments.command == "cache":
            if arguments.cache_command == "create":

                storage_config = {}
                if arguments.storage == "s3":
                    storage_config = {
                        "s3_bucket": arguments.bucket,
                        "s3_region": arguments.region,
                        "s3_access_key": arguments.access_key,
                        "s3_secret_key": arguments.secret_key,
                    }

                command_handler.cache_create(
                    arguments.name,
                    arguments.port,
                    arguments.storage,
                    arguments.retention,
                    storage_config,
                )
            elif arguments.cache_command == "start":
                command_handler.cache_start(arguments.name)
            elif arguments.cache_command == "stop":
                command_handler.cache_stop(arguments.name)
            elif arguments.cache_command == "delete":
                command_handler.cache_delete(arguments.name)
            elif arguments.cache_command == "update":
                command_handler.cache_update(
                    arguments.name,
                    arguments.new_name,
                    arguments.access,
                    arguments.retention,
                    arguments.port,
                )
            elif arguments.cache_command == "list":
                command_handler.cache_list(arguments.private, arguments.public)
            elif arguments.cache_command == "info":
                command_handler.cache_info(arguments.name)

        elif arguments.command == "agent":
            if arguments.agent_command == "add":
                command_handler.agent_add(arguments.name, arguments.workspace)
            elif arguments.agent_command == "remove":
                command_handler.agent_remove(arguments.name)
            elif arguments.agent_command == "list":
                command_handler.agent_list(arguments.workspace)
            elif arguments.agent_command == "info":
                command_handler.agent_info(arguments.name)

        elif arguments.command == "workspace":
            if arguments.workspace_command == "create":
                command_handler.workspace_create(arguments.name, arguments.cache)
            elif arguments.workspace_command == "delete":
                command_handler.workspace_delete(arguments.name)
            elif arguments.workspace_command == "list":
                command_handler.workspace_list()
            elif arguments.workspace_command == "info":
                command_handler.workspace_info(arguments.name)
            elif arguments.workspace_command == "cache":
                command_handler.workspace_cache(arguments.name, arguments.cache)

        elif arguments.command == "store-path":
            if arguments.store_path_command == "list":
                command_handler.store_path_list(arguments.cache)
            elif arguments.store_path_command == "delete":
                command_handler.store_path_delete(arguments.cache, arguments.hash)
            elif arguments.store_path_command == "info":
                command_handler.store_path_info(arguments.hash, arguments.cache)
