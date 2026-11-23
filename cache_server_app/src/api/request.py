#!/usr/bin/env python3.12
"""
request

Request body handling shared by the HTTP APIs.
"""

import json
from email.message import Message
from typing import Any

from cache_server_app.src.storage.base import Readable


class RequestError(Exception):
    """Ends request handling with the given HTTP status."""

    def __init__(self, status: int, reason: str = "") -> None:
        super().__init__(reason or str(status))
        self.status = status


def body_length(headers: Message, max_size: int) -> int:
    """Validated Content-Length; refuses bodies that would be too large to accept before reading them."""
    value = headers.get("Content-Length")
    if value is None:
        raise RequestError(411, "missing Content-Length")
    try:
        length = int(value)
    except ValueError:
        raise RequestError(400, "invalid Content-Length")
    if length < 0:
        raise RequestError(400, "invalid Content-Length")
    if length > max_size:
        raise RequestError(413, f"body of {length} bytes exceeds {max_size}")
    return length


def read_json(rfile: Readable, headers: Message, max_size: int) -> Any:
    """Read and parse a JSON request body of at most `max_size` bytes."""
    length = body_length(headers, max_size)
    try:
        return json.loads(rfile.read(length).decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        raise RequestError(400, "invalid JSON body")
