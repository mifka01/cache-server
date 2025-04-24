#!/usr/bin/env python3.12
"""
workspace

Parser for workspace arguments

Author: Radim Mifka

Date: 21.12.2024
"""

from argparse import _SubParsersAction


# workspace
def add_workspace_parser(
    subparsers: _SubParsersAction,
) -> None:

    workspace_parser = subparsers.add_parser(
        "workspace",
        description="Manage deployment workspaces",
        help="Manage deployment workspaces",
    )

    workspace_subparser = workspace_parser.add_subparsers(dest="workspace_command")

    add_workspace_create_parser(workspace_subparser)
    add_workspace_delete_parser(workspace_subparser)
    add_workspace_list_parser(workspace_subparser)
    add_workspace_info_parser(workspace_subparser)
    add_workspace_cache_parser(workspace_subparser)


# workspace add
def add_workspace_create_parser(
    subparsers: _SubParsersAction,
) -> None:
    workspace_create_parser = subparsers.add_parser(
        "add", description="Create workspace", help="Create workspace"
    )

    workspace_create_parser.add_argument("name", type=str, help="Workspace name")
    workspace_create_parser.add_argument("cache", type=str, help="Binary cache name")


# workspace delete
def add_workspace_delete_parser(
    subparsers: _SubParsersAction,
) -> None:
    workspace_delete_parser = subparsers.add_parser(
        "delete", description="Delete workspace", help="Delete workspace"
    )

    workspace_delete_parser.add_argument("name", type=str, help="Workspace name")


# workspace list
def add_workspace_list_parser(
    subparsers: _SubParsersAction,
) -> None:
    workspace_list_parser = subparsers.add_parser(
        "list", description="List workspaces", help="List workspaces"
    )

# workspace info
def add_workspace_info_parser(
    subparsers: _SubParsersAction,
) -> None:
    workspace_info_parser = subparsers.add_parser(
        "info", description="workspace info", help="workspace info"
    )

    workspace_info_parser.add_argument("name", type=str, help="workspace name")

# workspace cache
def add_workspace_cache_parser(
    subparsers: _SubParsersAction,
) -> None:
    workspace_cache_parser = subparsers.add_parser(
        "cache",
        description="Change workspace binary cache",
        help="Change workspace binary cache",
    )
    workspace_cache_parser.add_argument("name", help="Workspace name")
    workspace_cache_parser.add_argument("cache", help="New workspace binary cache")
