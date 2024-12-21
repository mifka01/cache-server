from argparse import ArgumentParser, _SubParsersAction


# agent
def get_agent_parser(subparsers: _SubParsersAction) -> ArgumentParser:

    agent_parser = subparsers.add_parser(
        "agent", description="Manage deployment agents", help="Manage deployment agents"
    )

    agent_subparser = agent_parser.add_subparsers(dest="agent_command")

    get_agent_add_parser(agent_subparser)
    get_agent_delete_parser(agent_subparser)
    get_agent_list_parser(agent_subparser)
    get_agent_info_parser(agent_subparser)

    return agent_parser


# agent add
def get_agent_add_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    agent_add_parser = subparsers.add_parser(
        "add", description="Create agent", help="Create agent"
    )

    agent_add_parser.add_argument("name", type=str, help="Agent name")
    agent_add_parser.add_argument("workspace", type=str, help="Workspace name")

    return agent_add_parser


# agent delete
def get_agent_delete_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    agent_delete_parser = subparsers.add_parser(
        "delete", description="Delete agent", help="Delete agent"
    )

    agent_delete_parser.add_argument("name", type=str, help="Agent name")

    return agent_delete_parser


def get_agent_list_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    agent_list_parser = subparsers.add_parser(
        "list", description="List agents", help="List agents"
    )

    agent_list_parser.add_argument("workspace", type=str, help="Workspace name")

    return agent_list_parser


# agent info
def get_agent_info_parser(
    subparsers: _SubParsersAction,
) -> ArgumentParser:
    agent_info_parser = subparsers.add_parser(
        "info", description="Agent info", help="Agent info"
    )

    agent_info_parser.add_argument("name", type=str, help="Agent name")

    return agent_info_parser
