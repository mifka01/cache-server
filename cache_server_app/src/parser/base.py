#!/usr/bin/env python3.12
"""
base

Base for parser

Author: Radim Mifka

Date: 21.12.2024
"""

from argparse import ArgumentParser, Namespace
from typing import Sequence

from cache_server_app.src.parser.agent import add_agent_parser
from cache_server_app.src.parser.cache import add_cache_parser
from cache_server_app.src.parser.server import add_server_parser
from cache_server_app.src.parser.store_path import add_store_path_parser
from cache_server_app.src.parser.workspace import add_workspace_parser


def parse(args: Sequence[str]) -> Namespace:
    parser = ArgumentParser(prog="cache-server", description="Cache server options")
    subparsers = parser.add_subparsers(dest="command", metavar="")

    add_server_parser(subparsers)
    add_cache_parser(subparsers)
    add_agent_parser(subparsers)
    add_workspace_parser(subparsers)
    add_store_path_parser(subparsers)

    return parser.parse_args(args)
