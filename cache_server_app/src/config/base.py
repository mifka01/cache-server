#!/usr/bin/env python3.12
"""
base

Configuration loader for the cache-server application.

Author: Radim Mifka

Date: 16.4.2025
"""

import os
import sys
from yaml import safe_load

from cache_server_app.src.storage.type import StorageType

# Respect XDG_CONFIG_HOME, fallback to ~/.config
xdg_config_home = os.environ.get("XDG_CONFIG_HOME", os.path.join(os.path.expanduser("~"), ".config"))
config_file = os.path.join(xdg_config_home, "cache-server", "config.yaml")

if not os.path.exists(config_file):
    print(f"ERROR: Config file {config_file} not found.")
    sys.exit(1)

try:
    with open(config_file, 'r') as file:
        config = safe_load(file)

    server_config = config.get("server", {})
    database = server_config.get("database", "/var/lib/cache-server/db.sqlite")
    server_hostname = server_config.get("hostname", "localhost")
    standalone = server_config.get("standalone", False)
    dht_port = int(server_config.get("dht-port", 4222))
    dht_bootstrap_host = server_config.get("dht-bootstrap-host", "localhost")
    dht_bootstrap_port = int(server_config.get("dht-bootstrap-port", 4223))
    server_port = int(server_config.get("server-port", 5000))
    deploy_port = int(server_config.get("deploy-port", 5001))
    key = server_config.get("key", "")

    default_retention = int(server_config.get("default-retention", 4))
    default_port = int(server_config.get("default-port", 8080))
    default_storage = server_config.get("default-storage", StorageType.LOCAL.value)
    default_storage_strategy = server_config.get("default-storage-strategy", "round-robin")

    should_bootstrap = (
        dht_bootstrap_host != server_hostname or
        dht_bootstrap_port != dht_port
    )

    caches = config.get("caches", [])
    for cache in caches:
        if "storages" not in cache:
            cache["storages"] = []

    workspaces = config.get("workspaces", [])
    agents = config.get("agents", [])

except Exception as e:
    print(f"ERROR: Failed to parse config: {e}")
    sys.exit(1)

