#!/usr/bin/env python3.12
"""
server

Parser for server arguments

Author: Radim Mifka

Date: 21.12.2024
"""

from argparse import _SubParsersAction

from cache_server_app.src.parser.hidden import add_hidden_parser


def add_server_parser(
    subparsers: _SubParsersAction,
) -> None:

    subparsers.add_parser(
        "listen", description="Start cache server", help="Start cache server"
    )

    subparsers.add_parser(
        "stop", description="Stop cache server", help="Stop cache server"
    )

    add_hidden_parser(subparsers)
