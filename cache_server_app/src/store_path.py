#!/usr/bin/env python3.12
"""
store_path

Module containing the StorePath class.

Author: Marek Križan, Radim Mifka

Date: 1.5.2024
"""

import base64
import os

from cache_server_app.src.storage.base import Storage
import ed25519

from cache_server_app.src.cache.base import BinaryCache
from cache_server_app.src.database import CacheServerDatabase


class StorePath:
    """
    Class to represent store object.

    Attributes:
        database: object to handle database connection
        id: store path id
        store_hash: hash part of store path
        store_suffix: suffix part of store path
        file_hash: file hash of compressed NAR file
        file_size: file size of compressed NAR file
        nar_hash: hash of decompressed NAR file
        nar_size: size of decompressed NAR file
        deriver: store path of the deriver
        references: immediate dependencies of the store path
        storage: storage object
    """

    def __init__(
        self,
        id: str,
        store_hash: str,
        store_suffix: str,
        file_hash: str,
        file_size: int,
        nar_hash: str,
        nar_size: int,
        deriver: str,
        references: list[str],
        storage: Storage
    ):
        self.id = id
        self.database = CacheServerDatabase()
        self.store_hash = store_hash
        self.store_suffix = store_suffix
        self.file_hash = file_hash
        self.file_size = file_size
        self.nar_hash = nar_hash
        self.nar_size = nar_size
        self.deriver = deriver
        self.references = references
        self.storage = storage

    @staticmethod
    def get(cache_name: str, store_hash: str = "", file_hash: str = ""):
        cache = BinaryCache.get(name=cache_name)
        if not cache:
            return None

        row = cache.storage.get_store_path(store_hash=store_hash, file_hash=file_hash)
        if not row:
            return None

        storage = cache.storage.get_storage(row[9])
        if not storage:
            return None

        return StorePath(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            row[7],
            row[8].split(" "),
            storage
        )

    def get_narinfo(self) -> str:
        file_name = self.storage.find(self.file_hash)

        if file_name is None:
            raise FileNotFoundError(f"File with hash {self.file_hash} not found.")

        narinfo_dict = f"""StorePath: /nix/store/{self.store_hash}-{self.store_suffix}
URL: nar/{self.file_hash}.nar{os.path.splitext(file_name)[1]}
Compression: {os.path.splitext(file_name)[1][1:]}
FileHash: sha256:{self.file_hash}
FileSize: {self.file_size}
NarHash: {self.nar_hash}
NarSize: {self.nar_size}
Deriver: {self.deriver}
System: "x86_64-linux"
References: {' '.join(self.references)}
Sig: {self.signature()}
"""
        return narinfo_dict

    def fingerprint(self) -> bytes:
        refs = ",".join(["/nix/store/" + ref for ref in self.references])
        output = f"1;/nix/store/{self.store_hash}-{self.store_suffix};{self.nar_hash};{self.nar_size};{refs}".encode(
            "utf-8"
        )
        return output

    def signature(self) -> str:
        content = self.storage.read("key.priv", binary=True).split(b":")
        prefix = content[0]

        sk = ed25519.SigningKey(base64.b64decode(content[1]))
        sig = prefix + b":" + base64.b64encode(sk.sign(self.fingerprint()))
        return sig.decode("utf-8")

    def save(self) -> None:
        self.database.insert_store_path(
            self.id,
            self.store_hash,
            self.store_suffix,
            self.file_hash,
            self.file_size,
            self.nar_hash,
            self.nar_size,
            self.deriver,
            self.references,
            self.storage.id
        )

    def delete(self) -> None:
        self.database.delete_store_path(self.store_hash, self.storage.id)
