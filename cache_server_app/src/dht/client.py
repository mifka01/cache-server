#!/usr/bin/env python3.12
"""
dht_client

Client for the central DHT service

Author: Radim Mifka

Date: 22.4.2025
"""

import json
import urllib.request
import urllib.error
import urllib.parse
import cache_server_app.src.config.base as config
from typing import List

class DHTClient:
    """
    Client class to connect to the central DHT service.
    """
    _instance = None

    @classmethod
    def get_instance(cls) -> "DHTClient":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        self.base_url = f"http://{config.server_hostname}:{config.server_port}/api/v1/dht"

    def put(self, key: str, value: str, permanent: bool = False) -> None:
        """
        Put a value into the DHT.

        Args:
            key: Key to put
            value: Value to put
            permanent: If True, the node will automatically keep the value on the network as long as node is running,
                       otherwise the value will be removed after a timeout. https://github.com/savoirfairelinux/opendht/issues/196
        """

        if config.standalone:
            return None

        data = json.dumps({"key": key, "value": value, "permanent": permanent}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/put",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as response:
                if response.status != 200:
                    print(f"ERROR: Failed to put value into DHT. Status code: {response.status}")
        except urllib.error.URLError as e:
            print(f"ERROR: Error putting value in DHT: {e}")

    def get(self, key: str) -> List[str] | None:
        """
        Get a value from the DHT.

        Args:
            key: Key to get

        Returns:
            List[str] | None : Value associated with the key
        """

        if config.standalone:
            return None

        try:
            with urllib.request.urlopen(f"{self.base_url}/get/{urllib.parse.quote(key)}") as response:
                if response.status == 200:
                    data = json.loads(response.read().decode("utf-8"))
                    value: List[str] | None = data.get("value")
                    if value is not None:
                        return value
        except urllib.error.URLError as e:
            print(f"Error getting value from DHT: {e}")

        return None
