#!/usr/bin/env python3.12
"""
store_path

Parser for store path arguments

Author: Radim Mifka

Date: 21.12.2024
"""

from argparse import _SubParsersAction


# store-path
def add_store_path_parser(
    subparsers: _SubParsersAction,
) -> None:

    store_path_parser = subparsers.add_parser(
        "store-path", description="Manage store paths", help="Manage store paths"
    )

    store_path_subparser = store_path_parser.add_subparsers(dest="store_path_command")

    add_store_path_list_parser(store_path_subparser)
    add_store_path_delete_parser(store_path_subparser)
    add_store_path_info_parser(store_path_subparser)


# store-path list
def add_store_path_list_parser(
    subparsers: _SubParsersAction,
) -> None:
    store_path_list_parser = subparsers.add_parser(
        "list", description="List store paths", help="List store paths"
    )
    store_path_list_parser.add_argument("cache", type=str, help="Binary cache name")


# store-path delete
def add_store_path_delete_parser(
    subparsers: _SubParsersAction,
) -> None:
    store_path_delete_parser = subparsers.add_parser(
        "delete", description="Delete store path", help="Delete store path"
    )

    store_path_delete_parser.add_argument("hash", type=str, help="Store path hash")
    store_path_delete_parser.add_argument("cache", type=str, help="Binary cache name")


# store-path info
def add_store_path_info_parser(
    subparsers: _SubParsersAction,
) -> None:
    store_path_info_parser = subparsers.add_parser(
        "info",
        help="Display info about store path",
        description="Display info about store path",
    )

    store_path_info_parser.add_argument("hash", help="Store path hash")
    store_path_info_parser.add_argument("cache", type=str, help="Binary cache name")
