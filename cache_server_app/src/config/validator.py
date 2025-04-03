#!/usr/bin/env python3.12
"""
Validator for the cache-server application configuration.

This module validates the configuration.

Author: Radim Mifka
Date: 02.04.2025
"""

from typing import Dict, List, Tuple

import cache_server_app.src.config.base as config
from cache_server_app.src.commands.registry import CommandRegistry
from cache_server_app.src.storage.registry import StorageRegistry


class ConfigValidator:
    """Manages loading and applying configurations from the config file."""

    def __init__(self):
        self.registry = CommandRegistry()
        self.errors = []

    def validate_configuration(self) -> Tuple[bool, List[str]]:
        """
        Validate the configuration before applying it.

        Returns:
            Tuple of (is_valid, errors)
        """
        self.errors = []

        self._validate_caches(config.caches)
        self._validate_workspaces(config.workspaces, config.caches)
        self._validate_agents(config.agents, config.workspaces)

        is_valid = len(self.errors) == 0
        return is_valid, self.errors

    def _validate_caches(self, caches: List[Dict]) -> None:
        """Validate cache configurations."""
        if not isinstance(caches, list):
            self.errors.append("'caches' must be a list")
            return

        cache_names = set()

        for i, cache in enumerate(caches):
            if not isinstance(cache, dict):
                self.errors.append(f"Cache at index {i} must be an object")
                continue

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

            if "retention" in cache:
                retention = cache["retention"]
                if not isinstance(retention, int) or retention < 0:
                    self.errors.append(f"Cache '{name}': retention must be a non-negative integer")

            if "storages" in cache:
                self._validate_storages(cache["storages"], name)

    def _validate_storages(self, storages: List[Dict], cache_name: str) -> None:
        """Validate storage configurations for a cache."""
        if not isinstance(storages, list):
            self.errors.append(f"Cache '{cache_name}': 'storages' must be a list")
            return

        storage_names = set()

        for i, storage in enumerate(storages):
            if not isinstance(storage, dict):
                self.errors.append(f"Cache '{cache_name}': Storage at index {i} must be an object")
                continue

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

            config_requirements = storage_class.get_config_requirements()
            prefix = config_requirements.prefix

            required_keys = [f"{prefix}{key}" for key in config_requirements.required]
            for key in required_keys:
                if key not in storage:
                    self.errors.append(f"Cache '{cache_name}': Storage '{name}' is missing required configuration '{key}'")

    def _validate_workspaces(self, workspaces: List[Dict], caches: List[Dict]) -> None:
        """Validate workspace configurations."""
        if not isinstance(workspaces, list):
            self.errors.append("'workspaces' must be a list")
            return

        workspace_names = set()
        cache_names = {cache["name"] for cache in caches if isinstance(cache, dict) and "name" in cache}

        for i, workspace in enumerate(workspaces):
            if not isinstance(workspace, dict):
                self.errors.append(f"Workspace at index {i} must be an object")
                continue

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
        if not isinstance(agents, list):
            self.errors.append("'agents' must be a list")
            return

        agent_names = set()
        workspace_names = {workspace["name"] for workspace in workspaces if isinstance(workspace, dict) and "name" in workspace}

        for i, agent in enumerate(agents):
            if not isinstance(agent, dict):
                self.errors.append(f"Agent at index {i} must be an object")
                continue

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

