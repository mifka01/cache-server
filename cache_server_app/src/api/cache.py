#!/usr/bin/env python3.12
"""
cache

Module containing classes for Binary cache HTTP API.

Author: Marek Križan, Radim Mifka

Date: 17.5.2025
"""

import base64
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Tuple, Any

from cache_server_app.src.cache.base import BinaryCache
from cache_server_app.src.cache.remote import RemoteCacheHelper
from cache_server_app.src.store_path import StorePath

class HTTPBinaryCache(ThreadingHTTPServer):
    def __init__(self, server_address: Tuple[str, int], request_handler: type["BinaryCacheRequestHandler"], cache: BinaryCache) -> None:
        super().__init__(server_address, request_handler)
        self.cache = cache
        self.remote = RemoteCacheHelper(cache)

class BinaryCacheRequestHandler(BaseHTTPRequestHandler):

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.server: HTTPBinaryCache # type: ignore

    """
    Class to handle binary cache HTTP requests.
    """
    def do_GET(self) -> None:
        if self.server.cache.is_private():
            if (
                base64.b64decode(self.headers["Authorization"].split()[1]).decode(
                    "utf-8"
                )[1:]
                != self.server.cache.token
            ):
                self.send_response(401)
                self.end_headers()
                return

        # /nix-cache-info
        if m := re.match(r"^/nix-cache-info$", self.path):
            cache_info = "Priority: 30\nStoreDir: /nix/store\nWantMassQuery: 1\n".encode(
                "utf-8"
            )
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(len(cache_info)))
            self.end_headers()
            self.wfile.write(cache_info)

        # /{storeHash}.narinfo
        elif m := re.match(r"^\/([a-z0-9]+)\.narinfo$", self.path):
            store_hash = m.group(1)
            response : bytes | None = None

            path = StorePath.get(self.server.cache.name, store_hash=m.group(1))
            if path:
                response = path.get_narinfo().encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/x-nix-narinfo")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)
                return

            remote_cache_url = self.server.remote.get_remote_cache_url(store_hash)
            if not remote_cache_url:
                self.send_response(404)
                self.end_headers()
                return

            response, status = self.server.remote.fetch_and_process_remote_narinfo(
                store_hash,
                remote_cache_url
            )

            if not response:
                self.send_response(status)
                self.end_headers()
                return

            self.send_response(status)
            self.send_header("Content-Type", "text/x-nix-narinfo")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

        # /nar/{fileHash}.nar.{compression}
        elif m := re.match(r"^/nar/([a-z0-9]+)\.nar\.(xz|zst)$", self.path):
            file_hash = m.group(1)
            compression = m.group(2)
            nar_path = f"nar/{file_hash}.nar.{compression}"

            path = StorePath.get(self.server.cache.name, file_hash=m.group(1))
            if path:
                nar_file = f"{file_hash}.nar.{compression}"
                try:
                    response = self.server.cache.storage.read(nar_file, binary=True)
                    self.send_response(200)
                    self.send_header("Content-Type", "application/octet-stream")
                    self.send_header("Content-Length", str(len(response)))
                    self.end_headers()
                    self.wfile.write(response)
                    return
                except Exception as e:
                    print(f"Error reading local nar file: {e}")

            if nar_path in self.server.remote.cached_paths:
                remote_cache_url = self.server.remote.cached_paths[nar_path]
                response, status = self.server.remote.fetch_remote_nar_file(
                    file_hash,
                    compression,
                    remote_cache_url,
                )

                if not response:
                    self.send_response(status)
                    self.end_headers()
                    return

                self.send_response(status)
                self.send_header("Content-Type", "application/octet-stream")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)
                return

            self.send_response(404)
            self.end_headers()

    def do_PUT(self) -> None:
        # /{narUuid}
        if m := re.match(
            r"^/([a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})$",
            self.path,
        ):

            content_length = int(self.headers["Content-Length"])

            name = m.group(1)
            findings = self.server.cache.storage.find(name)
            if findings is None:
                self.send_response(400)
                self.end_headers()
                return

            filename, storage = findings

            if not filename:
                self.send_response(400)
                self.end_headers()
                return

            body = self.rfile.read(content_length)


            self.server.cache.dht.put(filename, self.server.cache.id)

            storage.save(filename, body)

            self.send_response(201)
            self.send_header("Content-Location", "/")
            self.end_headers()
        else:
            self.send_response(400)
            self.end_headers()

    def do_HEAD(self) -> None:

        if self.server.cache.is_private():
            if (
                base64.b64decode(self.headers["Authorization"].split()[1]).decode(
                    "utf-8"
                )[1:]
                != self.server.cache.token
            ):
                self.send_response(401)
                self.end_headers()
                return

        # /{storeHash}.narinfo
        if m := re.match(r"^\/([a-z0-9]+)\.narinfo", self.path):

            path = StorePath.get(self.server.cache.name, store_hash=m.group(1))
            if not path:
                self.send_response(400)
                self.end_headers()
                return

            self.send_response(200)
            self.end_headers()
        else:
            self.send_response(400)
            self.end_headers()
