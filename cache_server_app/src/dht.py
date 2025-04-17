#!/usr/bin/env python3.12
"""
dht

Abstraction over opendht library to create simple access for cache server

Author: Radim Mifka

Date: 16.4.2025
"""

import opendht as dht
import cache_server_app.src.config.base as config

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
        self.node.run(port=config.dht_port)
        print(f"DHT node started on port {config.dht_port}")

        # Attempt to bootstrap to the specified host and port
        should_bootstrap = (
            config.dht_bootstrap_host != config.server_hostname or
            config.dht_bootstrap_port != config.dht_port
        )

        if should_bootstrap:
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

    def put(self, key: str, value: str) -> None:
        """
        Put a value into the DHT.

        Args:
            key: Key to put
            value: Value to put
        """
        key = dht.InfoHash(key)
        self.node.put(key, dht.Value(value))

    def get(self, key: str) -> str:
        """
        Get a value from the DHT.

        Args:
            key: Key to get

        Returns:
            str: Value associated with the key
        """
        return self.node.get(key)



