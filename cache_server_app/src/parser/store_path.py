from argparse import ArgumentParser, _SubParsersAction


# store-path
def get_store_path_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:

    store_path_parser = subparsers.add_parser(
        "store-path", description="Manage store paths", help="Manage store paths"
    )

    store_path_subparser = store_path_parser.add_subparsers(dest="store_path_command")

    get_store_path_list_parser(store_path_subparser)
    get_store_path_delete_parser(store_path_subparser)
    get_store_path_info_parser(store_path_subparser)

    return store_path_parser


# store-path list
def get_store_path_list_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    store_path_list_parser = subparsers.add_parser(
        "list", description="List store paths", help="List store paths"
    )
    store_path_list_parser.add_argument("cache", type=str, help="Binary cache name")

    return store_path_list_parser


# store-path delete
def get_store_path_delete_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    store_path_delete_parser = subparsers.add_parser(
        "delete", description="Delete store path", help="Delete store path"
    )

    store_path_delete_parser.add_argument("hash", type=str, help="Store path hash")
    store_path_delete_parser.add_argument("cache", type=str, help="Binary cache name")

    return store_path_delete_parser


# store-path info
def get_store_path_info_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    store_path_info_parser = subparsers.add_parser(
        "info",
        help="Display info about store path",
        description="Display info about store path",
    )

    store_path_info_parser.add_argument("hash", help="Store path hash")
    store_path_info_parser.add_argument("cache", type=str, help="Binary cache name")
    return store_path_info_parser
