#!/usr/bin/env python3.12
"""
server Server command handlers.
Author: Radim Mifka
Date: 1.5.2024
"""
import asyncio
import os
import signal
import subprocess
import sys
import threading
from typing import Any
import cache_server_app.src.config.base as config
from cache_server_app.src.api import CacheServerRequestHandler, HTTPCacheServer, WebSocketConnectionHandler
from cache_server_app.src.commands.base import BaseCommand
from cache_server_app.src.cache.manager import CacheManager
from cache_server_app.src.dht import DHT

class ServerCommands(BaseCommand):
    """Handles all server-related commands."""

    def __init__(self):
        super().__init__()
        self.process_manager = CacheManager()
        self.ws_handler = None
        self.ws_thread = None
        # Create an event to signal thread termination
        self.stop_event = threading.Event()
        self.dht = DHT.get_instance()

    def listen(self) -> None:
        """Start the cache server in the background."""
        pid_file = "/var/run/cache-server.pid"
        if self.get_pid(pid_file):
            print("Server is already running.")
            sys.exit(1)
        self.start()

    def start(self) -> None:
        """Start the cache server."""
        self.dht.start()

        # pid_file = "/var/run/cache-server.pid"
        # self.save_pid(pid_file)
        self.process_manager.run()

        self.stop_event.clear()

        self.ws_handler = WebSocketConnectionHandler(config.deploy_port)
        self.ws_thread = threading.Thread(
            target=self._start_workspace,
            args=(self.ws_handler, self.stop_event)
        )
        self.ws_thread.daemon = True
        self.ws_thread.start()

        server = HTTPCacheServer(
            (config.server_hostname, config.server_port),
            CacheServerRequestHandler,
            self.ws_handler,
        )
        print(f"Server started http://localhost:{config.server_port}")
        self.stop
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            self.stop()

    def stop(self) -> None:
        """Stop the cache server."""

        self.dht.stop()
        # pid_file = "/var/run/cache-server.pid"
        # pid = self.get_pid(pid_file)
        self.process_manager.stop()

        self.stop_event.set()
        if self.ws_thread and self.ws_thread.is_alive():
            self.ws_thread.join(timeout=5.0)

    def _start_workspace(self, ws_handler: WebSocketConnectionHandler, stop_event: threading.Event) -> None:
        """Start the WebSocket handler with a stop event for clean shutdown."""
        async def run_with_cancellation():
            ws_task = asyncio.create_task(ws_handler.run())

            while not stop_event.is_set():
                await asyncio.sleep(0.1)

            if not ws_task.done():
                ws_task.cancel()

            try:
                await asyncio.shield(ws_task)
            except asyncio.CancelledError:
                pass

        asyncio.run(run_with_cancellation())

    def execute(self, command: str, *args: Any, **kwargs: Any) -> None:
        """Execute the specified server command."""
        commands = {
            "listen": self.listen,
            "start": self.start,
            "stop": self.stop,
        }
        if command not in commands:
            raise ValueError(f"Unknown server command: {command}")
        commands[command](*args, **kwargs)
