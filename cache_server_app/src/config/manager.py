#!/usr/bin/env python3.12
"""
manager

Configuration manager for the cache-server application.

Author: Radim Mifka

Date: 3.4.2025
"""

from typing import Dict, Set, Optional, List, Tuple
from dataclasses import dataclass
import os

import cache_server_app.src.config.base as config
from cache_server_app.src.commands.registry import CommandRegistry
from cache_server_app.src.storage.registry import StorageRegistry
from cache_server_app.src.cache.base import BinaryCache, CacheAccess
from cache_server_app.src.config.validator import ConfigValidator
from cache_server_app.src.storage.strategies import Strategy
from cache_server_app.src.workspace import Workspace
from cache_server_app.src.agent import Agent


@dataclass
class ResourceState:
    """Represents the current state of a resource in the system."""
    name: str
    exists: bool
    needs_update: bool = False
    current_config: Optional[Dict] = None


class ConfigManager:
    """Manages loading and applying configurations from the config file."""

    def __init__(self) -> None:
        self.registry = CommandRegistry()
        self.existing_caches: Set[str] = set()
        self.existing_storages: Set[str] = set()
        self.existing_workspaces: Set[str] = set()
        self.existing_agents: Set[str] = set()

    def load_configuration(self, validate_first: bool = True) -> Tuple[bool, List[str]]:
        """
        Load and apply all configurations from the config file.

        Args:
            validate_first: Whether to validate before applying changes

        Returns:
            Tuple of (success, errors)
        """
        self.existing_caches = set()
        self.existing_storages = set()
        self.existing_workspaces = set()
        self.existing_agents = set()

        validator = ConfigValidator()

        if validate_first:
            is_valid, errors = validator.validate_configuration()
            if not is_valid:
                return False, errors

        try:
            self._handle_caches()
            self._handle_workspaces()
            self._handle_agents()
            self._remove_orphaned_resources()

            return True, []
        except Exception as e:
            validator.errors.append(f"Error applying configuration: {str(e)}")
            return False, validator.errors

    def _handle_caches(self) -> None:
        """Handle cache configurations."""
        for cache_config in config.caches:
            name = cache_config.get("name")
            if not name:
                continue  # Already validated, so this shouldn't happen

            self.existing_caches.add(name)
            state = self._get_cache_state(name, cache_config)

            if state.exists:
                if state.needs_update:
                    self._update_cache(name, cache_config)
            else:
                self._create_cache(name, cache_config)

            self._handle_storages(name, cache_config.get("storages", {}))

    def _handle_storages(self, cache_name: str, storages: List[Dict]) -> None:
        """Handle storage configurations for a cache."""

        cache = BinaryCache.get(name=cache_name)


        if not cache:
            return

        splits = []

        for storage in storages:
            storage_name = str(storage.get("name"))
            storage_type = str(storage.get("type"))
            storage_root = os.path.join(str(storage.get("root")), cache_name)

            if cache.storage.strategy == Strategy.SPLIT.value:
                split = storage.get(Strategy.SPLIT.value)
                if split is not None:
                    splits.append(split)

            self.existing_storages.add(storage_name)

            storage_config = self._get_storage_config(storage, storage_type)
            existing_storage = cache.storage.get_storage(name=storage_name)

            if existing_storage is not None:
                if existing_storage.type != storage_type or existing_storage.config != storage_config or existing_storage.root != storage_root:
                    cache.storage.update_storage(storage_name, storage_type, storage_root, storage_config)

            else:
                cache.storage.add_storage(storage_name, storage_type, storage_root, storage_config)

        if cache.storage.strategy == Strategy.SPLIT.value and splits != cache.storage.strategy_state.get(Strategy.SPLIT.value, []):
            cache.storage.strategy_state[Strategy.SPLIT.value] = splits
            cache.update()

    def _handle_workspaces(self) -> None:
        """Handle workspace configurations."""
        for workspace_config in config.workspaces:
            name = workspace_config.get("name")
            cache_name = workspace_config.get("cache")

            if name and cache_name:
                self.existing_workspaces.add(name)
                state = self._get_workspace_state(name, workspace_config)

                if state.exists:
                    if state.needs_update:
                        self._update_workspace(name, workspace_config)
                else:
                    self._create_workspace(name, workspace_config)

    def _handle_agents(self) -> None:
        """Handle agent configurations."""
        for agent_config in config.agents:
            name = agent_config.get("name")
            workspace_name = agent_config.get("workspace")

            if name and workspace_name:
                self.existing_agents.add(name)
                state = self._get_agent_state(name, agent_config)

                if state.exists:
                    if state.needs_update:
                        self._update_agent(name, agent_config)
                else:
                    self._create_agent(name, agent_config)

    def _remove_orphaned_resources(self) -> None:
        """Remove resources that are no longer defined in the configuration."""
        for cache in BinaryCache.get_rows():
            name = cache[1]
            cache_instance = BinaryCache.get(name=name)
            if not cache_instance:
                continue

            if name not in self.existing_caches:
                cache_instance.delete()
            else:
                for storage in cache_instance.storage.storages:
                    if storage.name not in self.existing_storages:
                        cache_instance.storage.remove_storage(name=storage.name)

        for workspace in Workspace.get_rows():
            name = workspace[1]
            if name not in self.existing_workspaces:
                workspace_instance = Workspace.get(name=name)
                if workspace_instance:
                    workspace_instance.delete()

        for agent in Agent.get_rows():
            name = agent[1]
            if name not in self.existing_agents:
                agent_instance = Agent.get(name=name)
                if agent_instance:
                    agent_instance.delete()

    def _get_cache_state(self, name: str, cache_config: Dict) -> ResourceState:
        """Get the current state of a cache."""
        existing_cache = BinaryCache.get(name=name)
        if not existing_cache:
            return ResourceState(name=name, exists=False)

        port = cache_config.get("port", config.default_port)
        retention = cache_config.get("retention", config.default_retention)
        access = cache_config.get("access", CacheAccess.PUBLIC.value)
        storage_strategy = cache_config.get("storage-strategy", config.default_storage_strategy)

        needs_update = (
            existing_cache.port != port or
            existing_cache.retention != retention or
            existing_cache.access != access or
            existing_cache.storage.strategy != storage_strategy
        )

        return ResourceState(
            name=name,
            exists=True,
            needs_update=needs_update,
            current_config={"port": port, "retention": retention, "access": access, "storage-strategy": storage_strategy}
        )

    def _get_workspace_state(self, name: str, workspace_config: Dict) -> ResourceState:
        """Get the current state of a workspace."""
        existing_workspace = Workspace.get(name=name)
        if not existing_workspace:
            return ResourceState(name=name, exists=False)

        cache_name = workspace_config.get("cache")
        needs_update = existing_workspace.cache != cache_name

        return ResourceState(
            name=name,
            exists=True,
            needs_update=needs_update,
            current_config={"cache": cache_name}
        )

    def _get_agent_state(self, name: str, agent_config: Dict) -> ResourceState:
        """Get the current state of an agent."""
        existing_agent = Agent.get(name=name)
        if not existing_agent:
            return ResourceState(name=name, exists=False)

        workspace_name = agent_config.get("workspace")
        needs_update = existing_agent.workspace!= workspace_name

        return ResourceState(
            name=name,
            exists=True,
            needs_update=needs_update,
            current_config={"workspace": workspace_name}
        )

    def _get_storage_config(self, storage: Dict, storage_type:str) -> Dict[str, str]:
        """Get the storage configuration for a given storage type."""
        storage_class = StorageRegistry.get_class(storage_type)
        if not storage_class:
            return {}

        config = storage_class.get_config_requirements()
        storage_config = {}

        for key, value in storage.items():
            if key.startswith(config.prefix) and key.replace(config.prefix, "") in config.required:
                storage_config[key] = value

        return storage_config

    def _create_cache(self, name: str, cache_config: Dict) -> None:
        """Create a new cache."""
        port = cache_config.get("port", config.default_port)
        retention = cache_config.get("retention", config.default_retention)
        access = cache_config.get("access", CacheAccess.PUBLIC.value)
        storage_strategy = cache_config.get("storage-strategy", config.default_storage_strategy)
        storages = []

        for storage in cache_config.get("storages", []):
            storage_name = storage.get("name")
            storage_type = storage.get("type")
            storage_root = storage.get("root")
            storage_config = self._get_storage_config(storage, storage_type)
            storages.append({"name": storage_name, "type": storage_type, "root": storage_root, Strategy.SPLIT.value: storage.get(Strategy.SPLIT.value, None), "config": storage_config})

        self.registry.execute("cache", "create", name, port, access, retention, storage_strategy, storages)

    def _update_cache(self, name: str, cache_config: Dict) -> None:
        """Update an existing cache."""
        port = cache_config.get("port", config.default_port)
        retention = cache_config.get("retention", config.default_retention)
        access = cache_config.get("access", CacheAccess.PUBLIC.value)
        storage_strategy = cache_config.get("storage-strategy", config.default_storage_strategy)

        self.registry.execute("cache", "update", name, None, port, access, retention, storage_strategy)

    def _create_workspace(self, name: str, workspace_config: Dict) -> None:
        """Create a new workspace."""
        cache_name = workspace_config.get("cache")
        self.registry.execute("workspace", "create", name, cache_name)

    def _update_workspace(self, name: str, workspace_config: Dict) -> None:
        """Update an existing workspace."""
        cache_name = workspace_config.get("cache")
        self.registry.execute("workspace", "cache", name, cache_name)

    def _create_agent(self, name: str, agent_config: Dict) -> None:
        """Create a new agent."""
        workspace_name = agent_config.get("workspace")
        self.registry.execute("agent", "add", name, workspace_name)

    def _update_agent(self, name: str, agent_config: Dict) -> None:
        """Update an existing agent."""
        workspace_name = agent_config.get("workspace")
        self.registry.execute("agent", "workspace", name, workspace_name)
