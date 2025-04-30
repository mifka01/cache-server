#!/usr/bin/env python3.12
"""
node

Abstraction over opendht library to create simple access for cache server

Author: Radim Mifka

Date: 16.4.2025
"""

import opendht as dht
import cache_server_app.src.config.base as config
from typing import Callable, List

class DHT:
    """
    Class to represent a DHT node.

    Attributes:
        node: DHT node instance
    """
    _instance = None

    @classmethod
    def get_instance(cls) -> "DHT":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def __init__(self) -> None:
        if DHT._instance is not None:
            raise Exception("This class is a singleton!")

        self.node = dht.DhtRunner()

    def start(self) -> None:
        """
        Start the DHT node.
        """

        if not config.standalone:
            self.node.run(port=config.dht_port)
            print(f"Trying to bootstrap to {config.dht_bootstrap_host}:{config.dht_bootstrap_port}")
            success = self._bootstrap(config.dht_bootstrap_host, config.dht_bootstrap_port)
            if not success:
                print("WARNING: Bootstrap failed. Starting standalone DHT node.")
        else:
            print("Running standalone DHT node")

    def stop(self) -> None:
        """
        Stop the DHT node.
        """
        self.node.shutdown()
        print("DHT node stopped.")

    def _bootstrap(self, host: str, port: int) -> bool:
        """
        Attempt to bootstrap to the specified host and port.

        Args:
            host: Host to bootstrap to
            port: Port to bootstrap to

        Returns:
            bool: True if bootstrap was successful, False otherwise
        """
        try:
            self.node.bootstrap(host, str(port))
            return True
        except Exception as e:
            print(f"ERROR: Exception during bootstrap: {e}")
            return False

    def put(self, key: str, value: str, done_callback: Callable | None =None) -> None:
        """
        Put a value into the DHT.

        Args:
            key: Key to put
            value: Value to put
        """

        if not self.node.isRunning():
            return None

        hash_key = dht.InfoHash.get(key)
        self.node.put(hash_key, dht.Value(value.encode()), done_cb=done_callback)

    def get(self, key: str, get_callback: Callable | None =None, done_callback:Callable | None=None) -> List[str] | None:
        """
        Get a value from the DHT.

        Args:
            key: Key to get

        Returns:
            str: Value associated with the key
        """

        if not self.node.isRunning():
            return None

        hash_key = dht.InfoHash.get(key)
        res = self.node.get(hash_key, get_cb=get_callback, done_cb=done_callback)
        if res:
            return [value.data.decode() for value in res]

        return None
