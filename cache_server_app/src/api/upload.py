#!/usr/bin/env python3.12
"""
upload

Streaming pieces of multipart NAR uploads.

cachix uploads a NAR in parts: each part is PUT to its own URL and answered with
an ETag (the part's MD5), and `complete` lists the parts in order. The parts are
stored as separate files and concatenated when the upload completes.
"""

import hashlib
import uuid
from typing import Iterator

from cache_server_app.src.storage.base import Readable, Storage

NIX_BASE32_ALPHABET = "0123456789abcdfghijklmnpqrsvwxyz"


def part_name(nar_id: str, part_number: int) -> str:
    """Storage file name of one uploaded part."""
    return f"{nar_id}.part{part_number}"


def staging_name(nar_id: str) -> str:
    """Unique temporary file of an upload, renamed into place once it is verified."""
    return f"{nar_id}.staging-{uuid.uuid4().hex}"


def etag(md5_hex: str) -> str:
    return f'"{md5_hex}"'


def normalize_etag(value: str) -> str:
    return value.strip().strip('"').lower()


class BodyReader:
    """Reads exactly `length` bytes of a request body and hashes them with MD5."""

    def __init__(self, stream: Readable, length: int) -> None:
        self._stream = stream
        self.remaining = length
        self.md5 = hashlib.md5()

    def read(self, size: int = -1, /) -> bytes:
        if self.remaining <= 0:
            return b""
        if size < 0 or size > self.remaining:
            size = self.remaining
        data = self._stream.read(size)
        self.remaining -= len(data)
        self.md5.update(data)
        return data


class PartsReader:
    """Concatenation of stored parts; records each part's MD5 and the SHA-256 and size of the whole."""

    def __init__(self, storage: Storage, names: list[str]) -> None:
        self._chunks = self._iterate(storage, names)
        self._buffer = bytearray()
        self.part_md5s: list[str] = []
        self.sha256 = hashlib.sha256()
        self.size = 0

    def _iterate(self, storage: Storage, names: list[str]) -> Iterator[bytes]:
        for name in names:
            md5 = hashlib.md5()
            for chunk in storage.read_stream(name):
                md5.update(chunk)
                yield chunk
            self.part_md5s.append(md5.hexdigest())

    def read(self, size: int = -1, /) -> bytes:
        # Fill the request completely unless the parts are exhausted: S3 multipart
        # uploads of non-seekable streams treat a short read as the last part.
        while size < 0 or len(self._buffer) < size:
            chunk = next(self._chunks, None)
            if chunk is None:
                break
            self._buffer += chunk

        end = len(self._buffer) if size < 0 else min(size, len(self._buffer))
        data = bytes(self._buffer[:end])
        del self._buffer[:end]
        self.sha256.update(data)
        self.size += len(data)
        return data


def nix_base32(digest: bytes) -> str:
    """Nix's base32 encoding of a hash digest (printHash32)."""
    length = (len(digest) * 8 - 1) // 5 + 1
    chars = []
    for n in range(length - 1, -1, -1):
        bit = n * 5
        i, j = divmod(bit, 8)
        c = digest[i] >> j
        if i + 1 < len(digest):
            c |= digest[i + 1] << (8 - j)
        chars.append(NIX_BASE32_ALPHABET[c & 0x1F])
    return "".join(chars)


def file_hash_matches(expected: str, digest: bytes) -> bool:
    """Whether a narinfo FileHash (base16 or Nix base32 SHA-256) names this digest."""
    return expected in (digest.hex(), nix_base32(digest))
