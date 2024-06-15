import argparse
import importlib.metadata
import json
import os
from typing import AnyStr

DEFAULT_DATA_PATH = os.path.expanduser("~/.lockey")
DEFAULT_CONFIG_PATH = os.path.expanduser("~/.config/lockey/config.json")
VERSION_FALLBACK = "0.1.0"


def get_data_path() -> "str | os.PathLike[AnyStr]":
    if os.path.exists(DEFAULT_CONFIG_PATH):
        with open(DEFAULT_CONFIG_PATH) as f:
            config_file = json.load(f)
        return config_file.get("data_path", DEFAULT_DATA_PATH)
    return DEFAULT_DATA_PATH


def get_version() -> str:
    try:
        _DISTRIBUTION_METADATA = importlib.metadata.metadata("MyProjectName")
        return _DISTRIBUTION_METADATA["Version"]
    except:
        return VERSION_FALLBACK


def execute_init(args: argparse.Namespace) -> None:
    raise NotImplementedError


def execute_ls(args: argparse.Namespace) -> None:
    raise NotImplementedError


def router(args: argparse.Namespace) -> None:
    if args.command == "init":
        execute_init(args)
    elif args.command == "ls":
        execute_ls(args)
    else:
        print(f"error: command {args.command} not recognized")


def main():
    parser = argparse.ArgumentParser(
        prog="lockey",
        description=(
            "A simple dependency-free password manager written in Python based on gpg."
        ),
    )
    parser.add_argument(
        "--version",
        help="print the version and exit",
        action="version",
        version=get_version(),
    )
    subparsers = parser.add_subparsers(dest="command")

    # init subcommand
    parser_init = subparsers.add_parser(
        name="init",
        help="initialize a lockey vault in a new location",
        description=(
            "Initialize the lockey vault in the location specified with the --dir flag "
            "or in the default location of $HOME/.lockey/. Also initializes lockey's "
            "config file at $HOME/.config/lockey/lockey.json."
        ),
    )
    parser_init.add_argument(
        "--dir",
        required=False,
        help="the path in which to store passwords",
        default=DEFAULT_DATA_PATH,
        dest="PATH",
    )

    # ls subcommand
    parser_init = subparsers.add_parser(
        name="ls",
        help="list the passwords you currently have saved",
        description=(
            "List all of the passwords saved in lockey's vault along with their "
            "description if they exist."
        ),
    )
    parser_init.add_argument(
        "--desc",
        required=False,
        type=str,
        help="a description for the password",
        dest="DESC",
    )

    router(parser.parse_args())


if __name__ == "__main__":
    main()
