#!/usr/bin/env python3.12
"""
agent

Parser for agent arguments

Author: Radim Mifka

Date: 21.12.2024
"""

from argparse import _SubParsersAction


# agent
def add_agent_parser(subparsers: _SubParsersAction) -> None:

    agent_parser = subparsers.add_parser(
        "agent", description="Manage deployment agents", help="Manage deployment agents"
    )

    agent_subparser = agent_parser.add_subparsers(dest="agent_command")

    add_agent_add_parser(agent_subparser)
    add_agent_delete_parser(agent_subparser)
    add_agent_list_parser(agent_subparser)
    add_agent_info_parser(agent_subparser)

# agent add
def add_agent_add_parser(
    subparsers: _SubParsersAction,
) -> None:
    agent_add_parser = subparsers.add_parser(
        "add", description="Create agent", help="Create agent"
    )

    agent_add_parser.add_argument("name", type=str, help="Agent name")
    agent_add_parser.add_argument("workspace", type=str, help="Workspace name")


# agent delete
def add_agent_delete_parser(
    subparsers: _SubParsersAction,
) -> None:
    agent_delete_parser = subparsers.add_parser(
        "delete", description="Delete agent", help="Delete agent"
    )

    agent_delete_parser.add_argument("name", type=str, help="Agent name")

def add_agent_list_parser(
    subparsers: _SubParsersAction,
) -> None:
    agent_list_parser = subparsers.add_parser(
        "list", description="List agents", help="List agents"
    )

    agent_list_parser.add_argument("workspace", type=str, help="Workspace name")

# agent info
def add_agent_info_parser(
    subparsers: _SubParsersAction,
) -> None:
    agent_info_parser = subparsers.add_parser(
        "info", description="Agent info", help="Agent info"
    )

    agent_info_parser.add_argument("name", type=str, help="Agent name")
