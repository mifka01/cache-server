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

    cache_dir = config.get("cache-server", "cache-dir")
    database = config.get("cache-server", "database")
    server_hostname = config.get("cache-server", "hostname")
    server_port = int(config.get("cache-server", "server-port"))
    deploy_port = int(config.get("cache-server", "deploy-port"))
    key = config.get("cache-server", "key")
except Exception:
    print("ERROR: Failed to parse config.")
    sys.exit(1)
