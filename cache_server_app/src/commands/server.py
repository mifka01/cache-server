#!/usr/bin/env python3.12
"""
server

Server command handlers.

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

import cache_server_app.src.config as config
from cache_server_app.src.api import CacheServerRequestHandler, HTTPCacheServer, WebSocketConnectionHandler
from cache_server_app.src.commands.base import BaseCommand
from cache_server_app.src.database import CacheServerDatabase


class ServerCommands(BaseCommand):
    """Handles all server-related commands."""

    def listen(self) -> None:
        """Start the cache server in the background."""
        pid_file = "/var/run/cache-server.pid"
        if self.get_pid(pid_file):
            print("Server is already running.")
            sys.exit(1)

        subprocess.Popen([sys.executable, "-m", "cache_server_app.main", "hidden-start", "server"])

    def start(self) -> None:
        """Start the cache server."""
        pid_file = "/var/run/cache-server.pid"
        self.save_pid(pid_file)

        ws_handler = WebSocketConnectionHandler(config.deploy_port)
        ws_thread = threading.Thread(target=self._start_workspace, args=(ws_handler,))
        ws_thread.start()

        server = HTTPCacheServer(
            (config.server_hostname, config.server_port),
            CacheServerRequestHandler,
            ws_handler,
        )
        print(f"Server started http://localhost:{config.server_port}")
        CacheServerDatabase().create_database()
        server.serve_forever()

    def stop(self) -> None:
        """Stop the cache server."""
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

    def _start_workspace(self, ws_handler: WebSocketConnectionHandler) -> None:
        """Start the WebSocket handler."""
        asyncio.run(ws_handler.run())

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
