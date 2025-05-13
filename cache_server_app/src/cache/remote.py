#!/usr/bin/env python3.12
"""
remote

This module provides functionality to interact with remote caches.

Author: Radim Mifka

Date: 25.4.2025
"""

import json
import urllib.request
import urllib.error
import time

from cache_server_app.src.cache.base import BinaryCache
from cache_server_app.src.cache.constants import LATENCY_WEIGHT, LOAD_SCORE_WEIGHT

class RemoteCacheHelper:
    """Utility class for remote cache operations."""

    def __init__(self, cache: BinaryCache) -> None:
        self.cache = cache
        self.cached_paths: dict[str, str] = {}


    def ping_remote_cache(self, remote_cache_url: str) -> bool:
        """Ping the remote cache to check if it's reachable."""
        remote_url = f"{remote_cache_url}/nix-cache-info"
        try:
            with urllib.request.urlopen(remote_url) as resp:
                if resp.status == 200:
                    return True
                else:
                    print(f"ERROR: Remote cache returned status code {resp.status}")
                    return False
        except urllib.error.URLError as e:
            return False
        except Exception as e:
            print(f"ERROR: Unexpected error pinging remote cache: {e}")
            return False

    def get_remote_cache_url(self, store_hash: str) -> str | None:
        """Get the URL of the best remote cache for a given store hash."""
        remote_cache_ids = self.cache.dht.get(store_hash)
        if not remote_cache_ids:
            return None

        best_remote_cache = None
        lowest_score = float('inf')

        for remote_cache_id in remote_cache_ids:

            remote_cache = self.cache.dht.get(remote_cache_id)
            if not remote_cache or not remote_cache[-1]:
                continue

            try:
                remote_cache_info = json.loads(remote_cache[-1])

                start_time = time.time()
                alive = self.ping_remote_cache(remote_cache_info.get("url"))
                if not alive:
                    continue

                latency = (time.time() - start_time) * 1000 # ms

                # float('inf') is the highest possible value
                load_score = float('inf')
                if "metrics" in remote_cache_info:
                    load_score = remote_cache_info["metrics"].get("load_score", float('inf'))

                score = (latency * LATENCY_WEIGHT) + (load_score * LOAD_SCORE_WEIGHT)

                if score < lowest_score:
                    lowest_score = load_score
                    best_remote_cache = remote_cache_info

            except json.JSONDecodeError:
                print(f"ERROR: Invalid JSON in remote cache data for {remote_cache_id}")
                continue

        return best_remote_cache.get("url") if best_remote_cache else None

    def narinfo_dict_to_bytes(self, narinfo_dict: dict) -> bytes:
        """Convert narinfo dictionary to bytes."""
        ordered_keys = [
            "StorePath", "URL", "Compression", "FileHash", "FileSize",
            "NarHash", "NarSize", "Deriver", "System", "References", "Sig"
        ]

        response = ""
        for key in ordered_keys:
            value = narinfo_dict.get(key, "")
            if key == "References" and value:
                value = " ".join(value)
            response += f"{key}: {value}\n"

        return response.encode()

    def fetch_and_process_remote_narinfo(self, store_hash: str, remote_cache_url: str) -> tuple[bytes | None, int]:
        """Fetch narinfo from remote cache and process it."""
        try:
            remote_url = f"{remote_cache_url}/{store_hash}.narinfo"
            with urllib.request.urlopen(remote_url) as resp:
                if resp.status != 200:
                    return None, resp.status

                narinfo_data = resp.read()
                narinfo_dict = self.cache.sign(narinfo_data)

                file_url: str = narinfo_dict.get("URL") # type: ignore
                if file_url:
                    self.cached_paths[file_url] = remote_cache_url

                narinfo_bytes = self.narinfo_dict_to_bytes(narinfo_dict)
                return narinfo_bytes, 200

        except urllib.error.HTTPError as e:
            print(f"ERROR: Failed to fetch remote narinfo: {e}")
            return None, e.code
        except Exception as e:
            print(f"ERROR: Unexpected error fetching narinfo: {e}")
            return None, 500

    def fetch_remote_nar_file(self, file_hash: str, compression: str, remote_cache_url: str) -> tuple[bytes | None, int]:
        """Fetch nar file from remote cache."""
        nar_path = f"nar/{file_hash}.nar.{compression}"
        try:
            remote_url = f"{remote_cache_url}/{nar_path}"
            with urllib.request.urlopen(remote_url) as resp:
                if resp.status != 200:
                    return None, resp.status

                nar_data = resp.read()

                # maybe try to save the file locally to avoid future redirects ???
                # try:
                #     self.cache.storage.save(f"{file_hash}.nar.{compression}", nar_data)
                # except Exception as cache_err:
                #     print(f"Failed to cache remote nar file locally: {cache_err}")

                if nar_path in self.cached_paths:
                    self.cached_paths.pop(nar_path)

                return nar_data, 200
        except urllib.error.URLError as e:
            print(f"ERROR: Failed to fetch remote nar file: {e}")
            return None, 502
        except Exception as e:
            print(f"ERROR: Unexpected error fetching nar file: {e}")
            return None, 500
