import multiprocessing
from typing import Dict, Any
import cache_server_app.src.config.base as config
from cache_server_app.src.commands.cache import CacheCommands


class CacheManager:
    """
    Manages the lifecycle of cache processes.
    Maintains a registry of running cache processes and ensures proper cleanup.
    """

    def __init__(self):
        self.cache_processes = {}
        self.running = False
        self.cache_commands = CacheCommands()

    def run(self):
        for cache in config.caches:
            name = cache.get("name")
            if cache.get("enabled", True):
                self.start_cache(name)

    def stop(self):
        """Stop all running cache processes."""
        for name, process in self.cache_processes.items():
            if process.is_alive():
                print(f"Stopping cache {name} with PID {process.pid}.")
                process.terminate()
                process.join()
                print(f"Cache {name} stopped.")

        self.cache_processes.clear()
        print("All caches stopped.")

    def start_cache(self, name: str) -> bool:
        """Start a cache instance as a subprocess and track it."""
        if name in self.cache_processes and self.cache_processes[name].poll() is None:
            print(f"Cache {name} is already running.")
            return False

        process = multiprocessing.Process(target=self.cache_commands.start, args=(name,))
        process.start()

        self.cache_processes[name] = process
        print(f"Cache {name} started with PID {process.pid}.")
        self.cache_commands.info(name)

        return True
