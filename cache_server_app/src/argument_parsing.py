#!/usr/bin/env python3.12
"""
argument_parsing

Module to define the cache-server CLI and to parse command line arguments.

Author: Marek Križan, Radim Mifka

Date: 1.5.2024
"""

import sys

from cache_server_app.src.commands.registry import CommandRegistry
from cache_server_app.src.parser.base import parse


def handle_arguments(argv) -> None:
    """Handle command line arguments."""
    arguments = parse(argv)
    registry = CommandRegistry()

    try:
        if arguments.command == "hidden-start":
            registry.execute(arguments.start_command, "start")
        elif arguments.command in ["stop", "listen"]:
            registry.execute("server", arguments.command)
        else:
            command_args = [arg for arg in vars(arguments).values() if arg is not None][2:]
            registry.execute(arguments.command, getattr(arguments, f"{arguments.command}_command"), *command_args)

    except ValueError as e:
        print(f"ERROR: {str(e)}")
        sys.exit(1)
