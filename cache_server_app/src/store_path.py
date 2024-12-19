#!/usr/bin/env python3.12
"""
store_path

Module containing the StorePath class.

Author: Marek Križan, Radim Mifka
Date: 1.5.2024
"""

import base64
import os

import ed25519

from cache_server_app.src.binary_cache import BinaryCache
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
        cache: binary cache in which the store path is stored
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
        cache: BinaryCache,
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
        self.cache = cache

    @staticmethod
    def get(cache_name: str, store_hash: str = "", file_hash: str = ""):

        if store_hash:
            row = CacheServerDatabase().get_store_path_row(
                cache_name, store_hash=store_hash
            )
        else:
            row = CacheServerDatabase().get_store_path_row(
                cache_name, file_hash=file_hash
            )

        if not row:
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
            BinaryCache.get(row[9]),
        )

    def get_narinfo(self) -> str:
        file_name = self.cache.storage.find(self.file_hash)

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
        content = self.cache.storage.read("key.priv", binary=True).split(b":")

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
            " ".join(self.references),
            self.cache.name,
        )

    def delete(self) -> None:
        self.database.delete_store_path(self.store_hash, self.cache.name)
