#!/usr/bin/env python3.12
"""
cache

Module containing classes for Binary cache HTTP API.

Author: Marek Križan, Radim Mifka

Date: 17.4.2025
"""

import base64
import http.client
import re
import urllib.error
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Tuple, Any
from urllib.parse import parse_qs, urlsplit
import time

import cache_server_app.src.config.base as config
from cache_server_app.src.api.constants import MAX_UPLOAD_PART_SIZE
from cache_server_app.src.api.request import RequestError, body_length
from cache_server_app.src.api.upload import BodyReader, etag, part_name, staging_name
from cache_server_app.src.api.validation import parse_part_number
from cache_server_app.src.auth import basic_auth_password, tokens_match
from cache_server_app.src.cache.base import BinaryCache
from cache_server_app.src.cache.remote import RemoteCacheHelper
from cache_server_app.src.storage.base import Storage
from cache_server_app.src.storage.constants import STREAM_CHUNK_SIZE
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
    def _authorized(self) -> bool:
        """Public caches are readable by anyone; private ones need the cache token as Basic auth password."""
        if not self.server.cache.is_private():
            return True
        password = basic_auth_password(self.headers.get("Authorization"))
        return tokens_match(password, self.server.cache.token)

    def _send_nar(self, storage: Storage, name: str) -> bool:
        """Stream a NAR file to the client; False when it can't be read (nothing sent then)."""
        try:
            size = storage.size(name)
            chunks = storage.read_stream(name)
            # read_stream is lazy: take the first chunk so the file is open (and a
            # missing file fails) before the 200 goes out.
            first = next(chunks, b"")
        except (OSError, ValueError) as e:
            print(f"Error reading local nar file: {e}")
            return False

        self.send_response(200)
        self.send_header("Content-Type", "application/octet-stream")
        self.send_header("Content-Length", str(size))
        self.end_headers()
        try:
            self.wfile.write(first)
            for chunk in chunks:
                self.wfile.write(chunk)
        except (BrokenPipeError, ConnectionResetError):
            print(f"Client disconnected while downloading {name}")
        finally:
            chunks.close()
        return True

    def do_GET(self) -> None:
        start_time = time.time()

        if not self._authorized():
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

            response_time = time.time() - start_time
            self.server.cache.metrics.record_request(True, response_time)
            return

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

                response_time = time.time() - start_time
                self.server.cache.metrics.record_request(True, response_time)
                return

            # served as signed by the cache that owns it
            path = StorePath.find(m.group(1))
            if path:
                response = path.get_narinfo().encode()
                self.send_response(200)
                self.send_header("Content-Type", "text/x-nix-narinfo")
                self.send_header("Content-Length", str(len(response)))
                self.end_headers()
                self.wfile.write(response)

                response_time = time.time() - start_time
                self.server.cache.metrics.record_request(False, response_time)
                return

            if not config.remote_fallback:
                self.send_response(404)
                self.end_headers()
                response_time = time.time() - start_time
                self.server.cache.metrics.record_request(False, response_time)
                return

            remote_cache_url = self.server.remote.get_remote_cache_url(store_hash)
            if not remote_cache_url or remote_cache_url == self.server.cache.url:
                self.send_response(404)
                self.end_headers()

                response_time = time.time() - start_time
                self.server.cache.metrics.record_request(False, response_time)
                return

            # forwarded unmodified: a DHT peer is untrusted, clients verify its own signature
            response, status = self.server.remote.fetch_remote_narinfo(
                store_hash,
                remote_cache_url
            )

            if not response:
                self.send_response(status)
                self.end_headers()
                response_time = time.time() - start_time
                self.server.cache.metrics.record_request(False, response_time)
                return

            self.send_response(status)
            self.send_header("Content-Type", "text/x-nix-narinfo")
            self.send_header("Content-Length", str(len(response)))
            self.end_headers()
            self.wfile.write(response)

            response_time = time.time() - start_time
            self.server.cache.metrics.record_request(False, response_time)

        # /nar/{fileHash}.nar.{compression}
        elif m := re.match(r"^/nar/([a-z0-9]+)\.nar\.(xz|zst)$", self.path):
            file_hash = m.group(1)
            compression = m.group(2)
            nar_path = f"nar/{file_hash}.nar.{compression}"

            # try to find the nar file in the local cache
            nar_file = f"{file_hash}.nar.{compression}"
            path = StorePath.get(self.server.cache.name, file_hash=m.group(1))
            if path and self._send_nar(path.storage, nar_file):
                self.server.cache.metrics.record_request(True, time.time() - start_time)
                return

            # try to find the nar file in the other local cache
            path = StorePath.find(file_hash=m.group(1))
            if path and self._send_nar(path.storage, nar_file):
                self.server.cache.metrics.record_request(False, time.time() - start_time)
                return

            if nar_path in self.server.remote.cached_paths:
                remote_cache_url = self.server.remote.cached_paths[nar_path]
                try:
                    upstream = self.server.remote.open_remote_nar_file(file_hash, compression, remote_cache_url)
                except urllib.error.HTTPError as e:
                    print(f"ERROR: Failed to fetch remote nar file: {e}")
                    status = e.code
                except OSError as e:
                    print(f"ERROR: Failed to fetch remote nar file: {e}")
                    status = 502
                else:
                    with upstream:
                        self.send_response(200)
                        self.send_header("Content-Type", "application/octet-stream")
                        length = upstream.headers.get("Content-Length")
                        if length is not None:
                            self.send_header("Content-Length", length)
                        self.end_headers()
                        try:
                            while chunk := upstream.read(STREAM_CHUNK_SIZE):
                                self.wfile.write(chunk)
                        except (OSError, http.client.HTTPException) as e:
                            print(f"ERROR: Streaming remote nar file failed: {e}")
                    self.server.cache.metrics.record_request(False, time.time() - start_time)
                    return

                self.send_response(status)
                self.end_headers()
                self.server.cache.metrics.record_request(False, time.time() - start_time)
                return

            self.send_response(404)
            self.end_headers()

    def do_PUT(self) -> None:
        start_time = time.time()
        try:
            response_headers = self._handle_put()
        except RequestError as e:
            print(f"ERROR: Rejected PUT {urlsplit(self.path).path}: {e}")
            self.send_response(e.status)
            self.end_headers()
            self.server.cache.metrics.record_request(False, time.time() - start_time)
            return

        self.send_response(201)
        for header, value in response_headers.items():
            self.send_header(header, value)
        self.end_headers()
        self.server.cache.metrics.record_request(True, time.time() - start_time)

    def _handle_put(self) -> dict[str, str]:
        """Store one part of a multipart upload: PUT /{narUuid}?partNumber=N; returns response headers."""
        url = urlsplit(self.path)
        m = re.fullmatch(r"/([a-z0-9]{8}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{4}-[a-z0-9]{12})", url.path)
        if not m:
            raise RequestError(400, "unknown endpoint")
        nar_id = m.group(1)
        try:
            part_number = parse_part_number(parse_qs(url.query).get("partNumber", [None])[0])
        except ValueError as e:
            raise RequestError(400, str(e))

        finding = self.server.cache.storage.find_upload(nar_id)
        if finding is None:
            raise RequestError(400, f"unknown upload {nar_id}")
        _, storage = finding

        length = body_length(self.headers, MAX_UPLOAD_PART_SIZE)
        name = part_name(nar_id, part_number)
        # Written under a unique name first, so a failed retry can't replace a part
        # that was already accepted, and completion never sees a half-written part.
        staging = staging_name(nar_id)
        reader = BodyReader(self.rfile, length)
        try:
            storage.write_stream(staging, reader)

            expected_md5 = self.headers.get("Content-MD5")
            if reader.remaining:
                raise RequestError(400, f"part {name} ended {reader.remaining} bytes early")
            if expected_md5 is not None and expected_md5.strip() != base64.b64encode(reader.md5.digest()).decode():
                raise RequestError(400, f"part {name} does not match Content-MD5")
        except BaseException:
            if storage.exists(staging):
                storage.remove(staging)
            raise

        storage.rename(staging, name)
        return {"ETag": etag(reader.md5.hexdigest()), "Content-Location": "/"}

    def do_HEAD(self) -> None:
        start_time = time.time()

        if not self._authorized():
            self.send_response(401)
            self.end_headers()
            response_time = time.time() - start_time
            self.server.cache.metrics.record_request(False, response_time)
            return

        # /{storeHash}.narinfo
        if m := re.match(r"^\/([a-z0-9]+)\.narinfo", self.path):

            path = StorePath.get(self.server.cache.name, store_hash=m.group(1))
            if not path:
                self.send_response(400)
                self.end_headers()
                response_time = time.time() - start_time
                self.server.cache.metrics.record_request(False, response_time)
                return

            self.send_response(200)
            self.end_headers()
            response_time = time.time() - start_time
            self.server.cache.metrics.record_request(True, response_time)
        else:
            self.send_response(400)
            self.end_headers()
            response_time = time.time() - start_time
            self.server.cache.metrics.record_request(False, response_time)
