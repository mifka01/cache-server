#!/usr/bin/env python3.12
"""
Main module for the cache-server application.

Author: Marek Križan, Radim Mifka
Date: 1.5.2024
"""

import sys

import cache_server_app.src.config.base as config
from cache_server_app.src.argument_parsing import handle_arguments
from cache_server_app.src.commands.registry import CommandRegistry
from cache_server_app.src.config.manager import ConfigManager
from cache_server_app.src.database import CacheServerDatabase


def load_configuration() -> bool:
    """Load and apply all configurations from the config file."""
    config_manager = ConfigManager()
    validation, errors = config_manager.load_configuration()

    if not validation:
        for error in errors:
            print(f"ERROR: {error}")

    return validation


def start_services() -> None:
    """Start the server and all configured caches if auto-start is enabled."""
    if not config.auto_start_server:
        return

    registry = CommandRegistry()

    registry.execute("server", "listen")

    for cache_config in config.caches:
        name = cache_config.get("name")
        if name:
            registry.execute("cache", "start", name)


def main() -> None:
    """Main entry point for the cache-server application."""
    if len(sys.argv) == 1:
        CacheServerDatabase().create_database()
        if load_configuration():
            start_services()
    else:
        handle_arguments(sys.argv[1:])

if __name__ == "__main__":
    main()
