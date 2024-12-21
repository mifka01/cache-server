from argparse import ArgumentParser, _SubParsersAction

from cache_server_app.src.parser.hidden import get_hidden_parser


def get_server_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:

    server_parser = subparsers.add_parser(
        "listen", description="Start cache server", help="Start cache server"
    )
    subparsers.add_parser(
        "stop", description="Stop cache server", help="Stop cache server"
    )

    get_hidden_parser(subparsers)

    return server_parser
