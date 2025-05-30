#!/usr/bin/env python3.12
"""
base

Module containing the BinaryCache class.

Author: Marek Križan, Radim Mifka

Date: 1.5.2024
"""

import base64
import json
import time
from typing import Dict, List, Optional, Set
from datetime import datetime, timedelta, timezone
from cache_server_app.src.cache.constants import ADVERTISING_INTERVAL, GARBAGE_COLLECTION_INTERVAL
from cache_server_app.src.types import BinaryCacheRow, NarInfoDict, StorePathRow
from cache_server_app.src.cache.metrics import CacheMetrics
from collections import deque

import ed25519

import cache_server_app.src.config.base as config
from cache_server_app.src.database import CacheServerDatabase
from cache_server_app.src.storage.manager import StorageManager
from cache_server_app.src.storage.factory import StorageFactory
from cache_server_app.src.cache.access import CacheAccess
from cache_server_app.src.dht.client import DHTClient

class BinaryCache:
    """
    Class to represent binary cache.

    Attributes:
        database: object to handle database connection
        id: binary cache id
        name: binary cache name
        url: binary cache url
        token: binary cache JWT authentication token
        access: binary cache access
        port: port on which binary cache listens
        retention: binary cache retention
        storages: list of storage objects
    """

    def __init__(
        self,
        id: str,
        name: str,
        url: str,
        token: str,
        access: str,
        port: int,
        retention: int,
        storage: StorageManager,
    ) -> None:
        self.database = CacheServerDatabase()
        self.id = id
        self.name = name
        self.url = url
        self.token = token
        self.access = CacheAccess(access)
        self.port = port
        self.retention = retention
        self.storage = storage
        self.dht = DHTClient.get_instance()
        self.metrics = CacheMetrics(self.id)

    @staticmethod
    def exist(id: Optional[str] = None, name: Optional[str] = None, port: Optional[int] = None) -> bool:
        return CacheServerDatabase().get_binary_cache_row(id, name, port) is not None

    @staticmethod
    def get_rows() -> List[BinaryCacheRow]:
        return CacheServerDatabase().get_binary_caches()

    @staticmethod
    def get(id: Optional[str] = None, name: Optional[str] = None, port: Optional[int] = None) -> Optional['BinaryCache']:
        database = CacheServerDatabase()
        row = database.get_binary_cache_row(id, name, port)
        if not row:
            return None

        storages = []
        for storage in database.get_cache_storages(row[0]):
            storage_id = storage[0]
            storage_name = storage[1]
            storage_type = storage[2]
            storage_root = storage[3]
            storage_config = database.get_storage_config(storage_id)
            storages.append(StorageFactory.create_storage(storage_id, storage_name, storage_type, storage_root, storage_config))

        return BinaryCache(
            row[0],
            row[1],
            row[2],
            row[3],
            row[4],
            row[5],
            row[6],
            StorageManager(row[0], storages, row[7], json.loads(str(row[8])), database)
        )

    def is_public(self) -> bool:
        return self.access == CacheAccess.PUBLIC

    def is_private(self) -> bool:
        return self.access == CacheAccess.PRIVATE

    def save(self) -> None:
        self.database.insert_binary_cache(
            self.id,
            self.name,
            self.url,
            self.token,
            self.access.value,
            self.port,
            self.retention,
            self.storage.strategy,
            json.dumps(self.storage.strategy_state),
        )

    def update(self) -> None:
        self.database.update_binary_cache(
            self.id,
            self.name,
            self.url,
            self.token,
            self.access.value,
            self.port,
            self.retention,
            self.storage.strategy,
            json.dumps(self.storage.strategy_state),
        )

    def delete(self) -> None:
        self.storage.delete()
        self.database.delete_binary_cache(self.id)

    def cache_json(self, permission: str) -> str:
        public_key = self.storage.read("key.pub")

        return json.dumps(
            {
                "githubUsername": "",
                "isPublic": self.is_public(),
                "name": self.name,
                "permission": permission,  # TODO
                "preferredCompressionMethod": "XZ",
                "publicSigningKeys": [public_key],
                "uri": self.url,
            }
        )

    def cache_workspace_dict(self) -> Dict[str, str | bool]:
        public_key = self.storage.read("key.pub")

        return {
            "cacheName": self.name,
            "isPublic": self.is_public(),
            "publicKey": public_key.split(":")[1],
        }

    def get_store_hashes(self) -> List[str]:
        return [path[1] for path in self.storage.get_store_paths()]

    def get_missing_store_hashes(self, hashes: List[str]) -> List[str]:
        return [
            store_hash
            for store_hash in hashes
            if store_hash not in self.get_store_hashes()
        ]

    def get_paths(self) -> List[StorePathRow]:
        return self.storage.get_store_paths()

    def update_workspaces(self, new_name: str) -> None:
        self.database.update_cache_in_workspaces(self.name, new_name)

    def update_paths(self, new_name: str) -> None:
        self.database.update_cache_in_paths(self.name, new_name)

    def advertise(self) -> None:
        """
        Advertise the cache to the DHT.
        """
        payload = {
            "id": self.id,
            "name": self.name,
            "url": self.url,
            "token": self.token,
            "access": str(self.access),
            "port": self.port,
            "metrics": self.metrics.to_dict(),
            "available_space": self.storage.get_available_space(),
            "retention": self.retention,
            "storage": str(self.storage),
        }

        self.dht.put(self.id, json.dumps(payload), False)

    def sync(self) -> None:
        """
        Synchronize the cache with the DHT.
        """

        if self.is_private():
            return

        self.advertise()
        paths = self.storage.get_store_paths()

        for path in paths:
            store_hash = path[1]
            self.dht.put(store_hash, self.id)


    def advertise_periodically(self) -> None:
        """
        Periodically advertise the cache to the DHT.
        """
        while True:
            time.sleep(ADVERTISING_INTERVAL * 60) # minutes to seconds
            self.advertise()

    def garbage_collector(self) -> None:
        while True:
            time.sleep(GARBAGE_COLLECTION_INTERVAL * 3600) # hours to seconds
            self.collect_garbage()

    def collect_garbage(self) -> None:
        retention = timedelta(days=self.retention)
        now = datetime.now(timezone.utc)

        healthy_packages: Set[str] = set()
        expired_rows: List[StorePathRow] = []

        for storage in self.storage.storages:
            for file in storage.list():
                if file.startswith("key"):
                    continue

                created_at = storage.get_file_creation_time(file)
                if created_at.tzinfo is None:
                    created_at = created_at.replace(tzinfo=timezone.utc)  # always use UTC

                file_hash = file.split(".")[0]
                row = self.database.get_store_path_row([storage.id], file_hash=file_hash)

                if not row:
                    if storage.is_new_file(file):
                        continue
                    print(f"Removing file {file} from storage {storage.name}")
                    storage.remove(file)
                    continue

                package_name = f"{row[1]}-{row[2]}"
                references = row[8].split(" ") if row[8] else []

                if created_at + retention > now:
                    healthy_packages.add(package_name)
                    healthy_packages.update(references)
                else:
                    expired_rows.append(row)

        queue = deque(expired_rows)
        visited = set()

        while queue:
            row = queue.popleft()
            package_name = f"{row[1]}-{row[2]}"
            refs = row[8].split(" ") if row[8] else []
            filename = f"{row[3]}.nar.xz"
            current_storage = self.storage.get_storage(row[9])

            if not current_storage:
                continue

            if package_name in healthy_packages:
                healthy_packages.update(refs)
                continue

            if package_name in visited:
                print(f"Removing file {package_name} from storage {current_storage.name}")
                current_storage.remove(filename)
                self.database.delete_store_path(row[1], row[9])
            else:
                visited.add(package_name)
                queue.append(row)

    def fingerprint(self, references: List[str], store_path: str, nar_hash: str, nar_size: str) -> bytes:

        refs = ",".join(["/nix/store/" + ref for ref in references])

        output = f"1;{store_path};{nar_hash};{nar_size};{refs}".encode(
            "utf-8"
        )
        return output

    def _parse_narinfo_text(self, narinfo_str: str) -> Optional[NarInfoDict]:
        """Parse narinfo text into a dictionary of key-value pairs.

        Args:
            narinfo_str: Raw narinfo string content

        Returns:
            Dictionary of narinfo fields or None if required fields are missing
        """
        result: NarInfoDict = {}

        for line in narinfo_str.strip().splitlines():
            if not line or line.startswith("Sig:"):
                continue

            if line.startswith("References:"):
                refs = line.split(": ", 1)[1]
                result["References"] = refs.split(" ") if refs and refs != " " else []
                continue

            try:
                key, val = line.split(": ", 1)
                result[key] = val
            except ValueError:
                continue

        if all(result[key] or result["References"] == [] for key in result):
            return result

        return None


    def sign(self, narinfo: bytes) -> NarInfoDict:
        """Sign narinfo content and return the complete signed narinfo.

        Args:
            narinfo: Raw narinfo content in bytes

        Returns:
            Complete signed narinfo text
        """

        content = self.storage.read("key.priv", binary=True).split(b":")
        prefix = content[0]


        narinfo_dict = self._parse_narinfo_text(narinfo.decode())
        if not narinfo_dict:
            raise ValueError("Invalid narinfo content")

        references: List[str] = narinfo_dict.get("References") # type: ignore
        store_path: str = narinfo_dict.get("StorePath") # type: ignore
        nar_hash: str = narinfo_dict.get("NarHash") # type: ignore
        nar_size: str = narinfo_dict.get("NarSize") # type: ignore


        fingerprint = self.fingerprint(
            references,
            store_path,
            nar_hash,
            nar_size,
        )

        sk = ed25519.SigningKey(base64.b64decode(content[1]))
        sig = prefix + b":" + base64.b64encode(sk.sign(fingerprint))
        narinfo_dict["Sig"] = sig.decode("utf-8")

        return narinfo_dict


    def generate_keys(self) -> None:
        sk, pk = ed25519.create_keypair()

        prefix = "{}.{}-1:".format(self.name, config.server_hostname).encode("utf-8")

        self.storage.new_file(
            "key.priv",
            prefix + base64.b64encode(sk.to_bytes()), True
        )

        self.storage.new_file(
            "key.pub",
            prefix + base64.b64encode(pk.to_bytes()), True
        )
