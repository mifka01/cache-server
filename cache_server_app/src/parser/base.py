from argparse import ArgumentParser, Namespace
from typing import Sequence

from cache_server_app.src.parser.agent import get_agent_parser
from cache_server_app.src.parser.cache import get_cache_parser
from cache_server_app.src.parser.server import get_server_parser
from cache_server_app.src.parser.store_path import get_store_path_parser
from cache_server_app.src.parser.workspace import get_workspace_parser


def parse(args: Sequence[str]) -> Namespace:
    parser = ArgumentParser(prog="cache-server", description="Cache server options")
    subparsers = parser.add_subparsers(dest="command", metavar="")

    get_server_parser(subparsers)
    get_cache_parser(subparsers)
    get_agent_parser(subparsers)
    get_workspace_parser(subparsers)
    get_store_path_parser(subparsers)

    return parser.parse_args(args)
