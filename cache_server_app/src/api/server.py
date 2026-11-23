#!/usr/bin/env python3.12
"""
server

Module containing classes for Cache server HTTP and WebSocket APIs.

Author: Marek Križan, Radim Mifka

Date: 17.4.2025
"""

import asyncio
import json
import os
import re
import uuid
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from cache_server_app.src.api.constants import DATETIME_FORMAT
import websockets
from websockets.server import WebSocketServerProtocol
from typing import Any, Tuple

from cache_server_app.src.agent import Agent
from cache_server_app.src.api.validation import parse_narinfo_create
from cache_server_app.src.auth import bearer_token, tokens_match
from cache_server_app.src.cache.base import BinaryCache
from cache_server_app.src.store_path import StorePath
from cache_server_app.src.dht.node import DHT
from cache_server_app.src.workspace import Workspace
import cache_server_app.src.config.base as config


class HTTPCacheServer(ThreadingHTTPServer):
    def __init__(self, server_address: Tuple[str, int], request_handler: type["CacheServerRequestHandler"], websocket_handler: "WebSocketConnectionHandler") -> None:
        self.websocket_handler = websocket_handler
        self.dht = DHT.get_instance()
        super().__init__(server_address, request_handler)


class CacheServerRequestHandler(BaseHTTPRequestHandler):
    """
    Class to handle cache-server HTTP requests.
    """

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.server: HTTPCacheServer # type: ignore

    def _send_status(self, status: int) -> None:
        self.send_response(status)
        self.end_headers()

    def _request_token(self) -> str | None:
        return bearer_token(self.headers.get("Authorization"))

    def _authorized_for_cache(self, cache: BinaryCache) -> bool:
        return tokens_match(self._request_token(), cache.token)

    def _authorized_for_any_cache(self) -> bool:
        token = self._request_token()
        return any(tokens_match(token, row[3]) for row in BinaryCache.get_rows())

    def _authorized_workspace(self) -> Workspace | None:
        token = self._request_token()
        for row in Workspace.get_rows():
            if tokens_match(token, row[2]):
                return Workspace.get(id=row[0])
        return None

    def do_GET(self) -> None:
        # /api/v1/dht/get/{key}
        if m := re.match(r"^/api/v1/dht/get/([^/]+)$", self.path):
            key = m.group(1)

            result = self.server.dht.get(key)
            response = json.dumps({"value": result}).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            try:
                self.wfile.write(response)
            except BrokenPipeError:
                print("Client disconnected before response was sent")
            return

        elif m := re.match(r"^/api/v1/cache/([a-z0-9]*)(\?)?", self.path):
            cache = BinaryCache.get(name=m.group(1))
            if not cache:
                self.send_response(400)
                self.end_headers()
                return

            if cache.is_private() and not self._authorized_for_cache(cache):
                self._send_status(401)
                return

            # /api/v1/cache/{name}
            if m := re.match(r"^/api/v1/cache/([a-z0-9]*)(\?)?$", self.path):
                response = cache.cache_json("Read").encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

        # /api/v1/deploy/deployment/{uuid}
        elif m := re.match(
            r"^/api/v1/deploy/deployment/([a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})(\?)?",
            self.path,
        ):
            if self._authorized_workspace() is None:
                self._send_status(401)
                return

            deploy_id = m.group(1)
            deploy_status = self.server.websocket_handler.deployments.get(deploy_id)
            if deploy_status is None:
                self._send_status(404)
                return

            response = json.dumps(
                {
                    "closureSize": 0,
                    "createdOn": datetime.now(timezone.utc).strftime(
                        DATETIME_FORMAT
                    ),
                    "id": deploy_id,
                    "index": 0,
                    "startedOn": datetime.now(timezone.utc).strftime(
                        DATETIME_FORMAT
                    ),
                    "status": deploy_status,
                    "storePath": "",
                }
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        else:
            self.send_response(400)
            self.end_headers()

    def do_POST(self) -> None:
        # /api/v1/dht/put
        if self.path == "/api/v1/dht/put":
            if not self._authorized_for_any_cache():
                self._send_status(401)
                return

            content_length = int(self.headers["Content-Length"])
            try:
                body = json.loads(self.rfile.read(content_length).decode("utf-8"))
            except ValueError:
                self._send_status(400)
                return

            # to make sure that dht put is non-blocking
            def done(ok: bool, _: Any) -> None:
                pass

            if not isinstance(body, dict) or "key" not in body or "value" not in body:
                self._send_status(400)
                return

            permanent = bool(body.get("permanent", False))
            self.server.dht.put(str(body["key"]), str(body["value"]), done, permanent=permanent)
            self._send_status(200)
            return

        elif m := re.match(r"^/api/v1/cache/([a-z0-9]*)", self.path):

            cache = BinaryCache.get(name=m.group(1))

            if not cache:
                self.send_response(400)
                self.end_headers()
                return

            if not self._authorized_for_cache(cache):
                self._send_status(401)
                return

            # /api/v1/cache/{name}/narinfo
            if re.match(r"^/api/v1/cache/[a-z0-9]*/narinfo(\?)?$", self.path):
                content_length = int(self.headers["Content-Length"])
                body = json.loads(self.rfile.read(content_length).decode("utf-8"))
                response = json.dumps(cache.get_missing_store_hashes(body)).encode(
                    "utf-8"
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            # /api/v1/cache/{name}/multipart-nar
            elif m := re.match(
                r"^/api/v1/cache/[a-z0-9]*/multipart-nar\?compression=(xz|zst)$",
                self.path,
            ):
                id = uuid.uuid4()
                response = """{{
                    "narId": "{}",
                    "uploadId": "{}"
                    }}""".format(
                    id, id
                ).encode(
                    "utf-8"
                )

                filename = f"{id}.nar.{m.group(1)}"
                cache.storage.new_file(filename)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

            # /api/v1/cache/{name}/multipart-nar/{narUuid}/complete
            elif m := re.match(
                r"^/api/v1/cache/[a-z0-9]+/multipart-nar/([a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})/complete(\?)?",
                self.path,
            ):
                content_length = int(self.headers["Content-Length"])
                try:
                    body = json.loads(self.rfile.read(content_length).decode("utf-8"))
                    narinfo_create = parse_narinfo_create(body.get("narInfoCreate") if isinstance(body, dict) else None)
                except ValueError as e:
                    print(f"ERROR: Rejected narinfo for upload {m.group(1)}: {e}")
                    self._send_status(400)
                    return

                name = m.group(1)
                finding = cache.storage.find(name)
                if finding is None:
                    self.send_response(400)
                    self.end_headers()
                    return

                filename, storage = finding

                StorePath(
                    id=str(uuid.uuid4()),
                    store_hash=narinfo_create.store_hash,
                    store_suffix=narinfo_create.store_suffix,
                    file_hash=narinfo_create.file_hash,
                    file_size=narinfo_create.file_size,
                    nar_hash=narinfo_create.nar_hash,
                    nar_size=narinfo_create.nar_size,
                    deriver=narinfo_create.deriver,
                    references=narinfo_create.references,
                    storage=storage
                ).save()

                new_filename = "{}.nar{}".format(
                    narinfo_create.file_hash, os.path.splitext(filename)[1]
                )

                if cache.is_public():
                    self.server.dht.put(narinfo_create.store_hash, cache.id)

                storage.rename(filename, new_filename)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

            # /api/v1/cache/{name}/multipart-nar/{narUuid}/abort
            elif m := re.match(
                r"^/api/v1/cache/[a-z0-9]+/multipart-nar/([a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})/abort(\?)?",
                self.path,
            ):
                name = m.group(1)
                findings = cache.storage.find(name)

                if findings is None:
                    self.send_response(400)
                    self.end_headers()
                    return

                filename, storage = findings

                storage.remove(filename)

                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

            # /api/v1/cache/{name}/multipart-nar/{narUuid}
            elif m := re.match(
                r"^/api/v1/cache/[a-z0-9]+/multipart-nar/([a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})(\?)?",
                self.path,
            ):

                content_length = int(self.headers["Content-Length"])
                body = json.loads(self.rfile.read(content_length).decode("utf-8"))
                upload_url = os.path.join(cache.url, m.group(1))
                response = """{{
                    "uploadUrl": "{}"
                }}""".format(
                    upload_url
                ).encode(
                    "utf-8"
                )
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

        # /api/v2/deploy/activate
        elif m := re.match(r"^/api/v2/deploy/activate(\?)?", self.path):
            workspace = self._authorized_workspace()
            if workspace is None:
                self._send_status(401)
                return

            content_length = int(self.headers["Content-Length"])
            body = json.loads(self.rfile.read(content_length).decode("utf-8"))
            requested: dict[str, str] = body["agents"]

            for agent_name in requested:
                agent = Agent.get(name=agent_name)
                if not agent or agent.workspace.id != workspace.id:
                    self._send_status(400)
                    return

            agents = {}
            for agent_name, path in requested.items():
                deploy_id = str(uuid.uuid4())
                agents[agent_name] = {"id": deploy_id, "url": ""}
                asyncio.run(
                    self.server.websocket_handler.start_deployment(
                        agent_name, path, deploy_id
                    )
                )

            response = json.dumps({"agents": agents}).encode("utf-8")

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        else:
            self.send_response(400)
            self.end_headers()


class WebSocketConnectionHandler:
    """
    Class to handle cache-server WebSocket connections.

    Attributes:
        port: port on which the WebSocket server runs
        agents: dictionary containing agent connections
        deployments: dictionary containing deployment connections
    """

    def __init__(self, port: int):
        self.port = port
        self.agents: dict[str, WebSocketServerProtocol] = {}
        self.deployments: dict[str, str] = {}
        self._stop_event = asyncio.Event()


    async def agent_handler(self, websocket: WebSocketServerProtocol) -> None:
        agent = Agent.get(name=websocket.request_headers["name"])
        if not agent:
            await websocket.close()
            return

        try:
            if websocket.request_headers["Authorization"].split()[1] != agent.token:
                await websocket.close()
                return

            cache = agent.workspace.cache
            self.agents[agent.name] = websocket
            message = json.dumps(
                {
                    "agent": agent.id,
                    "command": {
                        "contents": {
                            "cache": cache.cache_workspace_dict(),
                            "id": agent.id,
                        },
                        "tag": "AgentRegistered",
                    },
                    "id": "00000000-0000-0000-0000-000000000000",
                    "method": "AgentRegistered",
                }
            )

            await websocket.send(message)

            async for message in websocket: # type: ignore
                pass

        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            del self.agents[agent.name]

    async def deployment_handler(self, websocket: WebSocketServerProtocol) -> None:
        try:
            async for message in websocket:
                message_dict = json.loads(message)
                if message_dict["method"] == "DeploymentFinished":
                    if message_dict["command"]["hasSucceeded"]:
                        self.deployments[message_dict["command"]["id"]] = "Succeeded"
                    else:
                        self.deployments[message_dict["command"]["id"]] = "Failed"
                    await websocket.close()

        except websockets.exceptions.ConnectionClosed:
            pass

    async def log_handler(self, websocket: WebSocketServerProtocol) -> None:
        if "name" not in websocket.request_headers.keys():
            await websocket.close()
        try:
            async for message in websocket:
                message_dict = json.loads(message)
                if message_dict["line"] == "Successfully activated the deployment.":
                    await websocket.close()
                if "Failed to activate the deployment." in message_dict["line"]:
                    await websocket.close()

        except websockets.exceptions.ConnectionClosed:
            pass

    async def handler(self, websocket: WebSocketServerProtocol, path: str) -> None:
        if "/ws" == path:
            await self.agent_handler(websocket)
        elif "/ws-deployment" == path:
            await self.deployment_handler(websocket)
        elif "/api/v1/deploy/log/" == path:
            await self.log_handler(websocket)
        else:
            return

    async def start_deployment(
        self, agent_name: str, path: str, deploy_id: str
    ) -> None:
        agent = Agent.get(name=agent_name)
        if not agent:
            return None
        websocket = self.agents[agent.name]
        self.deployments[deploy_id] = "InProgress"
        message = json.dumps(
            {
                "agent": agent.id,
                "command": {
                    "contents": {
                        "id": deploy_id,
                        "index": 0,
                        "rollbackScript": None,
                        "storePath": path,
                    },
                    "tag": "Deployment",
                },
                "id": "00000000-0000-0000-0000-000000000000",
                "method": "Deployment",
            }
        )
        await websocket.send(message)

    async def run(self) -> None:
        async with websockets.serve(self.handler, config.server_hostname, self.port):
            print(f"WebSocket server started on ws://{config.server_hostname}:{self.port}")
            await self._stop_event.wait()

    def stop(self) -> None:
        if not self._stop_event.is_set():
            self._stop_event.set()
