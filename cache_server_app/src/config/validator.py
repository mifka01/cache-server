#!/usr/bin/env python3.12
"""
Validator for the cache-server application configuration.

Author: Radim Mifka

Date: 3.4.2025
"""

from typing import Dict, List, Tuple

import cache_server_app.src.config.base as config
import os
from cache_server_app.src.commands.registry import CommandRegistry
from cache_server_app.src.storage.registry import StorageRegistry
from cache_server_app.src.cache.base import CacheAccess
from cache_server_app.src.storage.strategies import STRATEGIES, Strategy
from cache_server_app.src.storage.type import StorageType


class ConfigValidator:
    """Manages loading and applying configurations from the config file."""

    def __init__(self) -> None:
        self.registry = CommandRegistry()
        self.errors: List[str] = []

    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """
        Validate the configuration before applying it.

        Returns:
            Tuple of (is_valid, errors)
        """
        self._validate_server(config.server_config)
        self._validate_caches(config.caches)
        self._validate_workspaces(config.workspaces, config.caches)
        self._validate_agents(config.agents, config.workspaces)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors

    def _validate_server(self, server: Dict) -> None:
        """Validate server configurations."""
        required_fields = ["database", "hostname", "server-port", "deploy-port"]

        for field in required_fields:
            if field not in server:
                self.errors.append(f"Server is missing required field '{field}'")

        if "standalone" in server and not isinstance(server["standalone"], bool):
            self.errors.append("Server 'standalone' must be a boolean")

        dht_required_fields = ["dht-bootstrap-host", "dht-bootstrap-port"]
        if not server.get("standalone", False):
            if any(field not in server for field in dht_required_fields):
                self.errors.append(f"Server is missing required fields for DHT: {', '.join(dht_required_fields)}")
                return

        strings = ["database", "hostname", "key"]
        ports = ["server-port", "deploy-port"]


        if not isinstance(config.dht_port, int) or config.dht_port < 1 or config.dht_port > 65535:
                self.errors.append(f"Server 'dht-port' must be an integer between 1 and 65535")

        if not server.get("standalone", False):
            strings.append("dht-bootstrap-host")
            ports.append("dht-bootstrap-port")

        for field in strings:
            if not isinstance(server[field], str):
                self.errors.append(f"Server '{field}' must be a string")

        for field in ports:
            if not isinstance(server[field], int) or server[field] < 1 or server[field] > 65535:
                self.errors.append(f"Server '{field}' must be an integer between 1 and 65535")

    def _validate_caches(self, caches: List[Dict]) -> None:
        """Validate cache configurations."""
        cache_names = set()

        for i, cache in enumerate(caches):
            if "name" not in cache:
                self.errors.append(f"Cache at index {i} is missing required field 'name'")
                continue

            name = cache["name"]
            if name in cache_names:
                self.errors.append(f"Duplicate cache name: {name}")
            cache_names.add(name)

            if "port" in cache:
                port = cache["port"]
                if not isinstance(port, int) or port < 1 or port > 65535:
                    self.errors.append(f"Cache '{name}': port must be an integer between 1 and 65535")

            if "access" in cache:
                access = cache["access"]
                if access not in CacheAccess.list():
                    self.errors.append(f"Cache '{name}': access must be one of {CacheAccess.str()}")

            if "retention" in cache:
                retention = cache["retention"]
                if not isinstance(retention, int) or retention <= 0:
                    self.errors.append(f"Cache '{name}': retention must be a positive integer")

            if "storage-strategy" in cache:
                strategy = cache["storage-strategy"]
                if strategy not in STRATEGIES.keys():
                    self.errors.append(f"Cache '{name}': storage-strategy must be one of {', '.join(STRATEGIES.keys())}")

                if strategy == Strategy.SPLIT.value:
                    split = 100
                    for storage in cache.get("storages", []):
                        if Strategy.SPLIT.value not in storage:
                            self.errors.append(f"Cache '{name}': Storage '{storage['name']}' must have '{Strategy.SPLIT.value}' field for {Strategy.SPLIT.value} strategy")
                        else:
                            split -= storage[Strategy.SPLIT.value]

                    if split != 0:
                        self.errors.append(f"Cache '{name}': Storage {Strategy.SPLIT.value} values must sum to 100, but got {100 - split}")

            if "storages" in cache:
                self._validate_storages(cache["storages"], name)


    def _validate_storages(self, storages: List[Dict], cache_name: str) -> None:
        """Validate storage configurations for a cache."""
        storage_names = set()

        for i, storage in enumerate(storages):
            if "name" not in storage:
                self.errors.append(f"Cache '{cache_name}': Storage at index {i} is missing required field 'name'")
                continue

            name = storage["name"]
            if name in storage_names:
                self.errors.append(f"Cache '{cache_name}': Duplicate storage name: {name}")
            storage_names.add(name)

            if "type" not in storage:
                self.errors.append(f"Cache '{cache_name}': Storage '{name}' is missing required field 'type'")
                continue

            # Check storage type
            storage_type = storage["type"]
            storage_class = StorageRegistry.get_class(storage_type)

            if not storage_class:
                supported_types = ", ".join(StorageRegistry.get_all_types())
                self.errors.append(f"Cache '{cache_name}': Storage '{name}' has unknown type '{storage_type}'. Supported types: {supported_types}")
                continue


            # Validate storage root
            if "root" not in storage:
                self.errors.append(f"Cache '{cache_name}': Storage '{name}' is missing required field 'root'")
                continue

            root = storage["root"]
            if not isinstance(root, str):
                self.errors.append(f"Cache '{cache_name}': Storage '{name}' root must be a string")
                continue

            config_requirements = storage_class.get_config_requirements()
            prefix = config_requirements.prefix

            config = {}
            required_keys = [f"{prefix}{key}" for key in config_requirements.required]
            for key in required_keys:
                if key not in storage:
                    self.errors.append(f"Cache '{cache_name}': Storage '{name}' is missing required configuration '{key}'")
                config[key] = storage[key]

            # Validate storage class
            if not storage_class.valid_config(config):
                self.errors.append(f"Cache '{cache_name}': Storage '{name}' has invalid configuration for type '{storage_type}'")
                continue

    def _validate_workspaces(self, workspaces: List[Dict], caches: List[Dict]) -> None:
        """Validate workspace configurations."""
        workspace_names = set()
        cache_names = {cache["name"] for cache in caches if isinstance(cache, dict) and "name" in cache}

        for i, workspace in enumerate(workspaces):
            if "name" not in workspace:
                self.errors.append(f"Workspace at index {i} is missing required field 'name'")
                continue

            name = workspace["name"]
            if name in workspace_names:
                self.errors.append(f"Duplicate workspace name: {name}")
            workspace_names.add(name)

            if "cache" not in workspace:
                self.errors.append(f"Workspace '{name}' is missing required field 'cache'")
                continue

            cache_name = workspace["cache"]
            if cache_name not in cache_names:
                self.errors.append(f"Workspace '{name}' references unknown cache: {cache_name}")

    def _validate_agents(self, agents: List[Dict], workspaces: List[Dict]) -> None:
        """Validate agent configurations."""
        agent_names = set()
        workspace_names = {workspace["name"] for workspace in workspaces if isinstance(workspace, dict) and "name" in workspace}

        for i, agent in enumerate(agents):
            if "name" not in agent:
                self.errors.append(f"Agent at index {i} is missing required field 'name'")
                continue

            name = agent["name"]
            if name in agent_names:
                self.errors.append(f"Duplicate agent name: {name}")
            agent_names.add(name)

            if "workspace" not in agent:
                self.errors.append(f"Agent '{name}' is missing required field 'workspace'")
                continue

            workspace_name = agent["workspace"]
            if workspace_name not in workspace_names:
                self.errors.append(f"Agent '{name}' references unknown workspace: {workspace_name}")

