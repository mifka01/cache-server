#!/usr/bin/env python3.12
"""
config

Module to parse configuration file.

Author: Marek Križan, Radim Mifka
Date: 1.5.2024
"""

import configparser
import os
import sys

config_file = os.path.join(os.path.expanduser("~"), ".cache-server.conf")

if not os.path.exists(config_file):
    print("ERROR: Config file %s not found." % config_file)
    sys.exit(1)

try:
    config = configparser.ConfigParser()
    config.read(config_file)

    # Server settings
    cache_dir = config.get("cache-server", "cache-dir")
    database = config.get("cache-server", "database")
    server_hostname = config.get("cache-server", "hostname")
    server_port = int(config.get("cache-server", "server-port"))
    deploy_port = int(config.get("cache-server", "deploy-port"))
    key = config.get("cache-server", "key")

    # Default cache settings
    default_retention = int(config.get("cache-server", "default-retention", fallback="4"))
    default_port = int(config.get("cache-server", "default-port", fallback="8080"))
    default_storage = config.get("cache-server", "default-storage", fallback="local")

    # S3 settings
    s3_bucket = config.get("cache-server", "s3-bucket", fallback="")
    s3_region = config.get("cache-server", "s3-region", fallback="")
    s3_access_key = config.get("cache-server", "s3-access-key", fallback="")
    s3_secret_key = config.get("cache-server", "s3-secret-key", fallback="")

except Exception as e:
    print(f"ERROR: Failed to parse config: {e}")
    sys.exit(1)
