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


class S3StorageAction(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        # Set the storage type
        setattr(namespace, self.dest, values)

        # If S3 is selected, validate S3-specific arguments
        if values == "s3":
            required_s3_args = [
                "s3_bucket",
                "s3_region",
                "s3_access_key",
                "s3_secret_key",
            ]

            # Check if S3 arguments are present
            for arg in required_s3_args:
                if not getattr(namespace, arg, None):
                    parser.error(
                        f"When using S3 storage, '{arg.replace('_', '-')}' is required"
                    )


def parse_arguments(argv):
    parser = argparse.ArgumentParser(
        prog="cache-server", description="Cache server options"
    )
    subparser = parser.add_subparsers(dest="command")

    subparser.add_parser(
        "listen", description="Start cache server", help="Start cache server"
    )

    start_parser = subparser.add_parser("hidden-start")
    start_subparser = start_parser.add_subparsers(dest="start_command")
    start_subparser.add_parser(
        "server", description="Start cache server", help="Start cache server"
    )
    start_cache_parser = start_subparser.add_parser(
        "cache", description="Start binary cache", help="Start binary cache"
    )
    start_cache_parser.add_argument("name", type=str, help="Binary cache name")
    start_cache_parser.add_argument("port", type=int, help="Binary cache port")

    subparser.add_parser(
        "stop", description="Stop cache server", help="Stop cache server"
    )

    cache_parser = subparser.add_parser(
        "cache", description="Manage caches", help="Manage caches"
    )
    cache_subparser = cache_parser.add_subparsers(dest="cache_command")
    cache_create_parser = cache_subparser.add_parser(
        "create", description="Create binary cache", help="Create binary cache"
    )
    cache_create_parser.add_argument("name", type=str, help="Binary cache name")
    cache_create_parser.add_argument("port", type=int, help="Binary cache port")
    cache_create_parser.add_argument(
        "storage",
        type=str,
        help="Storage type",
        choices=["local", "s3"],
        action=S3StorageAction,
    )
    cache_create_parser.add_argument(
        "-r",
        "--retention",
        help="Number of weeks after which paths will be removed",
        dest="retention",
    )

    s3_group = cache_create_parser.add_argument_group("S3 Storage Options")
    s3_group.add_argument(
        "--s3-bucket", type=str, help="S3 bucket name (required when storage is s3)"
    )
    s3_group.add_argument(
        "--s3-region",
        type=str,
        help="AWS region for the S3 bucket (required when storage is s3)",
    )
    s3_group.add_argument(
        "--s3-access-key",
        type=str,
        help="AWS Access Key ID (required when storage is s3)",
    )
    s3_group.add_argument(
        "--s3-secret-key",
        type=str,
        help="AWS Secret Access Key (required when storage is s3)",
    )

    cache_start_parser = cache_subparser.add_parser(
        "start", description="Start binary cache", help="Start binary cache"
    )
    cache_start_parser.add_argument("name", type=str, help="Binary cache name")
    cache_stop_parser = cache_subparser.add_parser(
        "stop", description="Stop binary cache", help="Stop binary cache"
    )
    cache_stop_parser.add_argument("name", type=str, help="Binary cache name")
    cache_delete_parser = cache_subparser.add_parser(
        "delete", description="Delete binary cache", help="Delete binary cache"
    )
    cache_delete_parser.add_argument("name", type=str, help="Binary cache name")
    cache_update_parser = cache_subparser.add_parser(
        "update", description="Update binary cache", help="Update binary cache"
    )
    cache_update_parser.add_argument("name", type=str, help="Binary cache name")
    cache_update_parser.add_argument(
        "-n", "--name", type=str, help="Change cache name to NAME", dest="new_name"
    )
    cache_update_parser.add_argument(
        "-a",
        "--access",
        choices=["public", "private"],
        help="Change access to public/private",
    )
    cache_update_parser.add_argument(
        "-p", "--port", type=int, help="Change cache port to PORT"
    )
    cache_update_parser.add_argument(
        "-r", "--retention", type=int, help="Change cache retention to RETENTION"
    )
    cache_list_parser = cache_subparser.add_parser(
        "list", description="List binary caches", help="List binary caches"
    )
    cache_list_group = cache_list_parser.add_mutually_exclusive_group()
    cache_list_group.add_argument(
        "-p", "--private", help="List private caches", action="store_true"
    )
    cache_list_group.add_argument(
        "-P", "--public", help="List public caches", action="store_true"
    )
    cache_info_parser = cache_subparser.add_parser(
        "info",
        help="Display info about binary cache",
        description="Display info about binary cache",
    )
    cache_info_parser.add_argument("name", help="Binary cache name")

    agent_parser = subparser.add_parser(
        "agent", description="Manage deployment agents", help="Manage deployment agents"
    )
    agent_subparser = agent_parser.add_subparsers(dest="agent_command")
    agent_add_parser = agent_subparser.add_parser(
        "add", description="Create agent", help="Create agent"
    )
    agent_add_parser.add_argument("name", type=str, help="Agent name")
    agent_add_parser.add_argument("workspace", type=str, help="Workspace name")
    agent_remove_parser = agent_subparser.add_parser(
        "remove", description="Remove agent", help="Remove agent"
    )
    agent_remove_parser.add_argument("name", type=str, help="Agent name")
    agent_list_parser = agent_subparser.add_parser(
        "list", description="List agents", help="List agents"
    )
    agent_list_parser.add_argument("workspace", type=str, help="Workspace name")
    agent_info_parser = agent_subparser.add_parser(
        "info", help="Display info about agent", description="Display info about agent"
    )
    agent_info_parser.add_argument("name", help="Agent name")

    workspace_parser = subparser.add_parser(
        "workspace",
        description="Manage deployment workspaces",
        help="Manage deployment workspaces",
    )
    workspace_subparser = workspace_parser.add_subparsers(dest="workspace_command")
    workspace_create_parser = workspace_subparser.add_parser(
        "create", description="Create workspace", help="Create workspace"
    )
    workspace_create_parser.add_argument("name", type=str, help="Workspace name")
    workspace_create_parser.add_argument("cache", type=str, help="Binary cache name")
    workspace_delete_parser = workspace_subparser.add_parser(
        "delete", description="Delete workspace", help="Delete workspace"
    )
    workspace_delete_parser.add_argument("name", type=str, help="Workspace name")
    workspace_subparser.add_parser(
        "list", description="List workspaces", help="List workspaces"
    )
    workspace_info_parser = workspace_subparser.add_parser(
        "info",
        help="Display info about workspace",
        description="Display info about workspace",
    )
    workspace_info_parser.add_argument("name", help="Workspace name")
    workspace_cache_parser = workspace_subparser.add_parser(
        "cache",
        description="Change workspace binary cache",
        help="Change workspace binary cache",
    )
    workspace_cache_parser.add_argument("name", help="Workspace name")
    workspace_cache_parser.add_argument("cache", help="New workspace binary cache")

    store_path_parser = subparser.add_parser(
        "store-path", description="Manage store paths", help="Manage store paths"
    )
    store_path_subparser = store_path_parser.add_subparsers(dest="store_path_command")
    store_path_list_parser = store_path_subparser.add_parser(
        "list", description="List store paths", help="List store paths"
    )
    store_path_list_parser.add_argument("cache", type=str, help="Binary cache name")
    store_path_delete_parser = store_path_subparser.add_parser(
        "delete", description="Delete store path", help="Delete store path"
    )
    store_path_delete_parser.add_argument("hash", type=str, help="Store path hash")
    store_path_delete_parser.add_argument("cache", type=str, help="Binary cache name")
    store_path_info_parser = store_path_subparser.add_parser(
        "info",
        help="Display info about store path",
        description="Display info about store path",
    )
    store_path_info_parser.add_argument("hash", help="Store path hash")
    store_path_info_parser.add_argument("cache", type=str, help="Binary cache name")

    return parser.parse_args(argv)


def handle_arguments(argv) -> None:
    arguments = parse_arguments(argv)
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
                        "s3_bucket": arguments.s3_bucket,
                        "s3_region": arguments.s3_region,
                        "s3_access_key": arguments.s3_access_key,
                        "s3_secret_key": arguments.s3_secret_key,
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
