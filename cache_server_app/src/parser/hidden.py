#!/usr/bin/env python3.12
"""
hidden

Parser for hidden arguments

Author: Radim Mifka

Date: 21.12.2024
"""

from argparse import ArgumentParser, _SubParsersAction


# hidden-start
def get_hidden_parser(subparsers: _SubParsersAction) -> ArgumentParser:
    start_parser = subparsers.add_parser("hidden-start")

    start_subparser = start_parser.add_subparsers(dest="start_command")

    start_subparser.add_parser(
        "server", description="Start cache server", help="Start cache server"
    )

    start_cache_parser = start_subparser.add_parser(
        "cache", description="Start binary cache", help="Start binary cache"
    )
    start_cache_parser.add_argument("name", type=str, help="Binary cache name")
    start_cache_parser.add_argument("port", type=int, help="Binary cache port")

    return start_parser
