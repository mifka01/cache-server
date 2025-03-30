#!/usr/bin/env python3.12
"""
config
Module to parse configuration file.
Author: Radim Mifka
Date: 1.5.2024
Modified: 30.3.2025
"""
import os
import sys
import yaml

config_file = os.path.join(os.path.expanduser("~"), ".cache-server.yaml")
if not os.path.exists(config_file):
    print("ERROR: Config file %s not found." % config_file)
    sys.exit(1)

try:
    with open(config_file, 'r') as file:
       config = yaml.safe_load(file)

    server_config = config.get("server", {})
    cache_dir = server_config.get("cache-dir", "/var/cache/cache-server")
    database = server_config.get("database", "/var/lib/cache-server/db.sqlite")
    server_hostname = server_config.get("hostname", "localhost")
    server_port = int(server_config.get("server-port", 5000))
    deploy_port = int(server_config.get("deploy-port", 5001))
    key = server_config.get("key", "")
    auto_start_server = server_config.get("auto-start", False)

    default_retention = int(server_config.get("default-retention", 4))
    default_port = int(server_config.get("default-port", 8080))
    default_storage = server_config.get("default-storage", "local")

    caches = config.get("caches", [])

    for cache in caches:
        if "storages" not in cache:
            cache["storages"] = []

    workspaces = config.get("workspaces", [])

    agents = config.get("agents", [])

except Exception as e:
    print(f"ERROR: Failed to parse config: {e}")
    sys.exit(1)
