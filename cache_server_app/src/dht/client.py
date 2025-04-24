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

    def put(self, key: str, value: str) -> None:
        """
        Put a value into the DHT.

        Args:
            key: Key to put
            value: Value to put
        """
        data = json.dumps({"key": key, "value": value}).encode("utf-8")
        req = urllib.request.Request(
            f"{self.base_url}/put",
            data=data,
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req) as response:
                return response.status == 200
        except urllib.error.URLError as e:
            print(f"Error putting value in DHT: {e}")

    def get(self, key: str) -> str:
        """
        Get a value from the DHT.

        Args:
            key: Key to get

        Returns:
            str: Value associated with the key
        """
        try:
            with urllib.request.urlopen(f"{self.base_url}/get/{urllib.parse.quote(key)}") as response:
                if response.status == 200:
                    return json.loads(response.read().decode("utf-8"))["value"]
                return ""
        except urllib.error.URLError as e:
            print(f"Error getting value from DHT: {e}")
            return ""
