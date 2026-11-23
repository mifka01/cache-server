#!/usr/bin/env python3.12
"""
argument_parsing

Module to define the cache-server CLI and to parse command line arguments.

Author: Marek Križan, Radim Mifka

Date: 1.5.2024
"""

import inspect
import sys
from argparse import Namespace
from typing import Any, Callable

from cache_server_app.src.commands.registry import CommandRegistry
from cache_server_app.src.parser.base import parse
from cache_server_app.src.storage.strategies import Strategy
from cache_server_app.src.storage.type import StorageType


def _cache_create_storages(arguments: Namespace) -> list[dict[str, Any]]:
    """The single storage `cache create` sets up, in the shape the config file uses."""
    storage_config: dict[str, str] = {}
    if arguments.storage_type == StorageType.S3.value:
        options = {
            "s3_bucket": arguments.bucket,
            "s3_region": arguments.region,
            "s3_access_key": arguments.access_key,
            "s3_secret_key": arguments.secret_key,
        }
        missing = [key for key, value in options.items() if not value]
        if missing:
            raise ValueError(f"S3 storage needs {', '.join(missing)}")
        storage_config = options

    return [{
        "name": arguments.storage_type,
        "type": arguments.storage_type,
        "root": arguments.root,
        Strategy.SPLIT.value: 100,
        "config": storage_config,
    }]


def _call(handler: Callable[..., None], arguments: Namespace) -> None:
    """Call a command handler with the parsed arguments named like its parameters."""
    values = vars(arguments)
    parameters = inspect.signature(handler).parameters
    missing = [name for name in parameters if name not in values]
    if missing:
        raise ValueError(f"Missing arguments: {', '.join(missing)}")
    handler(**{name: values[name] for name in parameters})


def handle_arguments(argv: list[str]) -> None:
    """Handle command line arguments."""
    arguments = parse(argv)
    registry = CommandRegistry()

    try:
        if arguments.command == "hidden-start":
            command, subcommand = arguments.start_command, "start"
        elif arguments.command in ["stop", "listen"]:
            command, subcommand = "server", arguments.command
        else:
            command = arguments.command
            subcommand = getattr(arguments, f"{command.replace('-', '_')}_command")

        if command == "cache" and subcommand == "create":
            arguments.storages = _cache_create_storages(arguments)

        _call(registry.handler(command, subcommand), arguments)

    except ValueError as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)
