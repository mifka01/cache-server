#!/usr/bin/env python3.12
"""
cache

Parser for cache arguments

Author: Radim Mifka

Date: 21.12.2024
"""

from argparse import _SubParsersAction

import cache_server_app.src.config.base as config
from cache_server_app.src.cache.access import CacheAccess
from cache_server_app.src.storage.strategies import Strategy
from cache_server_app.src.storage.type import StorageType


# cache
def add_cache_parser(subparsers: _SubParsersAction) -> None:
    cache_parser = subparsers.add_parser(
        "cache", description="Manage caches", help="Manage caches"
    )
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command")
    add_cache_create_parser(cache_subparsers)
    add_cache_start_parser(cache_subparsers)
    add_cache_stop_parser(cache_subparsers)
    add_cache_delete_parser(cache_subparsers)
    add_cache_update_parser(cache_subparsers)
    add_cache_list_parser(cache_subparsers)
    add_cache_info_parser(cache_subparsers)


# cache create
def add_cache_create_parser(
    subparsers: _SubParsersAction,
) -> None:
    cache_create_parser = subparsers.add_parser(
        "create",
        description="Create binary cache with a single storage",
        help="Create binary cache",
    )

    cache_create_parser.add_argument("name", type=str, help="Binary cache name")
    cache_create_parser.add_argument(
        "-p", "--port", type=int, help="Binary cache port", default=config.default_port
    )
    cache_create_parser.add_argument(
        "-a", "--access", choices=CacheAccess.list(), help="Binary cache access", default=CacheAccess.PUBLIC.value
    )
    cache_create_parser.add_argument(
        "-r",
        "--retention",
        type=int,
        help="Number of days after which paths will be removed",
        default=config.default_retention,
    )
    cache_create_parser.add_argument(
        "--strategy",
        dest="storage_strategy",
        choices=[strategy.value for strategy in Strategy],
        help="Storage strategy",
        default=config.default_storage_strategy,
    )
    cache_create_parser.add_argument(
        "-s",
        "--storage",
        dest="storage_type",
        choices=StorageType.list(),
        help="Binary cache storage type",
        default=config.default_storage,
    )
    cache_create_parser.add_argument(
        "--root", required=True, help="Storage root directory (S3: key prefix)"
    )

    # S3-specific arguments
    cache_create_parser.add_argument("--bucket", help="S3 bucket name")
    cache_create_parser.add_argument("--region", help="S3 region")
    cache_create_parser.add_argument("--access-key", help="S3 access key")
    cache_create_parser.add_argument("--secret-key", help="S3 secret key")


# cache start
def add_cache_start_parser(
    subparsers: _SubParsersAction,
) -> None:
    cache_start_parser = subparsers.add_parser(
        "start", description="Start binary cache", help="Start binary cache"
    )
    cache_start_parser.add_argument("name", type=str, help="Binary cache name")

# cache stop
def add_cache_stop_parser(
    subparsers: _SubParsersAction,
) -> None:
    cache_stop_parser = subparsers.add_parser(
        "stop", description="Stop binary cache", help="Stop binary cache"
    )
    cache_stop_parser.add_argument("name", type=str, help="Binary cache name")

# cache delete
def add_cache_delete_parser(
    subparsers: _SubParsersAction,
) -> None:
    cache_delete_parser = subparsers.add_parser(
        "delete", description="Delete binary cache", help="Delete binary cache"
    )
    cache_delete_parser.add_argument("name", type=str, help="Binary cache name")

# cache update
def add_cache_update_parser(
    subparsers: _SubParsersAction,
) -> None:
    cache_update_parser = subparsers.add_parser(
        "update", description="Update binary cache", help="Update binary cache"
    )

    cache_update_parser.add_argument("name", type=str, help="Binary cache name")
    cache_update_parser.add_argument("--name", dest="new_name", help="New binary cache name")
    cache_update_parser.add_argument("-p", "--port", type=int, help="Binary cache port")
    cache_update_parser.add_argument(
        "-a", "--access", choices=CacheAccess.list(), help="Binary cache access"
    )
    cache_update_parser.add_argument(
        "-r",
        "--retention",
        type=int,
        help="Number of days after which paths will be removed",
    )
    cache_update_parser.add_argument(
        "--strategy",
        dest="storage_strategy",
        choices=[strategy.value for strategy in Strategy],
        help="Storage strategy",
    )


# cache list
def add_cache_list_parser(
    subparsers: _SubParsersAction,
) -> None:
    cache_list_parser = subparsers.add_parser(
        "list", description="List binary caches", help="List binary caches"
    )
    cache_list_group = cache_list_parser.add_mutually_exclusive_group()
    cache_list_group.add_argument(
        "-p", "--private", help="List private caches", action="store_true"
    )
    cache_list_group.add_argument(
        "-P", "--public", help="List public caches", action="store_true"
    )

# cache info
def add_cache_info_parser(
    subparsers: _SubParsersAction,
) -> None:
    cache_info_parser = subparsers.add_parser(
        "info", description="Get binary cache info", help="Get binary cache info"
    )
    cache_info_parser.add_argument("name", type=str, help="Binary cache name")
