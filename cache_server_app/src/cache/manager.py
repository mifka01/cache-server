#!/usr/bin/env python3.12
"""
base

Process manager for cache instances

Author: Radim Mifka
Date: 16.4.2025
"""

import multiprocessing
import cache_server_app.src.config.base as config
from cache_server_app.src.commands.cache import CacheCommands


class CacheManager:
    """
    Manages the lifecycle of cache processes.
    Maintains a registry of running cache processes and ensures proper cleanup.
    """

    def __init__(self) -> None:
        self.cache_processes: dict[str, multiprocessing.Process] = {}
        self.running = False
        self.cache_commands = CacheCommands()

    def run(self) -> None:
        for cache in config.caches:
            name = cache.get("name")
            if cache.get("enabled", True):
                self.start_cache(name)

    def stop(self) -> None:
        """Stop all running cache processes."""
        for _ , process in self.cache_processes.items():
            if process.is_alive():
                process.terminate()
                process.join()

        self.cache_processes.clear()
        print("All caches stopped.")

    def start_cache(self, name: str) -> bool:
        """Start a cache instance as a subprocess and track it."""
        if name in self.cache_processes and self.cache_processes[name].is_alive():
            print(f"Cache {name} is already running.")
            return False

        process = multiprocessing.Process(target=self.cache_commands.start, args=(name,))
        process.start()

        self.cache_processes[name] = process
        self.cache_commands.info(name)

        return True
