#!/usr/bin/env python3.12
"""
server

Server command handlers.

Author: Marek Križan, Radim Mifka
Date: 30.3.2025
"""

import asyncio
import sys
import threading
from typing import Any
from cache_server_app.src.agent import Agent
import cache_server_app.src.config.base as config
from cache_server_app.src.api.server import CacheServerRequestHandler, HTTPCacheServer, WebSocketConnectionHandler
from cache_server_app.src.commands.base import BaseCommand
from cache_server_app.src.commands.workspace import WorkspaceCommands
from cache_server_app.src.commands.agent import AgentCommands
from cache_server_app.src.cache.manager import CacheManager
from cache_server_app.src.dht.node import DHT
from cache_server_app.src.workspace import Workspace

class ServerCommands(BaseCommand):
    """Handles all server-related commands."""

    def __init__(self) -> None:
        super().__init__()
        self.process_manager = CacheManager()
        self.ws_handler: WebSocketConnectionHandler | None = None
        self.ws_thread: threading.Thread | None = None
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
        def header(title: str, width: int = 55) -> str:
            padding = width - len(title) - 2  # account for the spaces
            left = padding // 2
            right = padding - left
            return "#" * left + f" {title} " + "#" * right

        print(header("SERVER"), "\n")
        self.dht.start()

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
        print(f"Server started http://{config.server_hostname}:{config.server_port}\n")

        print(header("CACHE"), "\n")
        self.process_manager.run()

        workspace_commands = WorkspaceCommands()
        workspaces = Workspace.get_rows()
        if workspaces:
            print(header("WORKSPACE"), "\n")
        for workspace in workspaces:
            workspace_commands.info(workspace[1])

        agent_commands = AgentCommands()
        agents = Agent.get_rows()
        if agents:
            print(header("AGENT"), "\n")
        for agent in agents:
            agent_commands.info(agent[1])

        print("Press Ctrl+C to stop the server\n")

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
        async def run_with_cancellation() -> None:
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
