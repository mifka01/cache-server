#!/usr/bin/env python3.12
"""
types

Module containing custom type definitions for database

Author: Radim Mifka

Date: 3.4.2025
"""

from typing import TypeAlias, List, TypedDict


BinaryCacheRow: TypeAlias = tuple[str, str, str, str, str, int, int]  # id, name, url, token, access, port, retention
StorageRow: TypeAlias = tuple[str, str, str, str]  # id, name, type, cache_id
StorePathRow: TypeAlias = tuple[str, str, str, str, int, str, int, str, str, str]  # id, store_hash, store_suffix, file_hash, file_size, nar_hash, nar_size, deriver, refs, storage_id
WorkspaceRow: TypeAlias = tuple[str, str, str, str]  # id, name, token, cache_id
AgentRow: TypeAlias = tuple[str, str, str, str]  # id, name, token, workspace_id

NarInfoDict: TypeAlias = dict[str, str | List[str]]  # Dictionary containing NAR info
