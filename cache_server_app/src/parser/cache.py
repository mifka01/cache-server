#!/usr/bin/env python3.12
"""
cache

Parser for cache arguments

Author: Radim Mifka

Date: 21.12.2024
"""

from argparse import ArgumentParser, _SubParsersAction

import cache_server_app.src.config.base as config
from cache_server_app.src.storage.type import StorageType


# cache
def get_cache_parser(subparsers: _SubParsersAction) -> ArgumentParser:
    cache_parser = subparsers.add_parser(
        "cache", description="Manage caches", help="Manage caches"
    )
    cache_subparsers = cache_parser.add_subparsers(dest="cache_command")
    get_cache_create_parser(cache_subparsers)
    get_cache_start_parser(cache_subparsers)
    get_cache_stop_parser(cache_subparsers)
    get_cache_delete_parser(cache_subparsers)
    get_cache_update_parser(cache_subparsers)
    get_cache_list_parser(cache_subparsers)
    get_cache_info_parser(cache_subparsers)

    return cache_parser


# cache create
def get_cache_create_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    cache_create_parser = subparsers.add_parser(
        "create", description="Create binary cache", help="Create binary cache"
    )

    cache_create_parser.add_argument("name", type=str, help="Binary cache name")
    cache_create_parser.add_argument(
        "-p", "--port", type=int, help="Binary cache port", default=config.default_port
    )
    cache_create_parser.add_argument(
        "-r",
        "--retention",
        type=int,
        help="Number of weeks after which paths will be removed",
        default=config.default_retention,
    )
    cache_create_parser.add_argument(
        "-s",
        "--storage",
        choices=["local", "s3"],
        help="Binary cache storage type",
        default=config.default_storage,
    )

    # S3-specific arguments
    cache_create_parser.add_argument(
        "--bucket",
        help="S3 bucket name",
    )
    cache_create_parser.add_argument(
        "--region",
        help="S3 region",
    )
    cache_create_parser.add_argument(
        "--access-key",
        help="S3 access key",
    )
    cache_create_parser.add_argument(
        "--secret-key",
        help="S3 secret key",
    )

    return cache_create_parser


# cache create name port -r retention local
def get_cache_local_storage_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    storage_parser = subparsers.add_parser(
        StorageType.LOCAL.value, description="Local storage", help="Local storage"
    )
    return storage_parser


# cache create name port -r retention s3
def get_cache_s3_storage_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    storage_parser = subparsers.add_parser(
        StorageType.S3.value, description="S3 storage", help="S3 storage"
    )

    storage_parser.add_argument("bucket", type=str, help="S3 bucket name")
    storage_parser.add_argument("access_key", type=str, help="S3 access key")
    storage_parser.add_argument("secret_key", type=str, help="S3 secret key")
    storage_parser.add_argument("--region", type=str, help="S3 region")
    return storage_parser


# cache start
def get_cache_start_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    cache_start_parser = subparsers.add_parser(
        "start", description="Start binary cache", help="Start binary cache"
    )
    cache_start_parser.add_argument("name", type=str, help="Binary cache name")
    return cache_start_parser


# cache stop
def get_cache_stop_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    cache_stop_parser = subparsers.add_parser(
        "stop", description="Stop binary cache", help="Stop binary cache"
    )
    cache_stop_parser.add_argument("name", type=str, help="Binary cache name")
    return cache_stop_parser


# cache delete
def get_cache_delete_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    cache_delete_parser = subparsers.add_parser(
        "delete", description="Delete binary cache", help="Delete binary cache"
    )
    cache_delete_parser.add_argument("name", type=str, help="Binary cache name")
    return cache_delete_parser


# cache update
def get_cache_update_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    cache_update_parser = subparsers.add_parser(
        "update", description="Update binary cache", help="Update binary cache"
    )

    cache_update_parser.add_argument("name", type=str, help="Binary cache name")
    cache_update_parser.add_argument("port", type=int, help="Binary cache port")
    cache_update_parser.add_argument(
        "-r",
        "--retention",
        help="Number of weeks after which paths will be removed",
        dest="retention",
    )
    cache_update_subparsers = cache_update_parser.add_subparsers(
        dest="cache_update_storage"
    )

    get_cache_local_storage_parser(cache_update_subparsers)
    get_cache_s3_storage_parser(cache_update_subparsers)

    return cache_update_parser


# cache list
def get_cache_list_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
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
    return cache_list_parser


# cache info
def get_cache_info_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    cache_info_parser = subparsers.add_parser(
        "info", description="Get binary cache info", help="Get binary cache info"
    )
    cache_info_parser.add_argument("name", type=str, help="Binary cache name")
    return cache_info_parser
