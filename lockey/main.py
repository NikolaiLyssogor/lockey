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


def execute_add(args: argparse.Namespace) -> None:
    raise NotImplementedError


def execute_rm(args: argparse.Namespace) -> None:
    raise NotImplementedError


def execute_destroy(args: argparse.Namespace) -> None:
    raise NotImplementedError


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lockey",
        description=(
            "A simple dependency-free password manager written in Python based on gpg."
        ),
    )
    parser.add_argument(
        "-v",
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
        "-f",
        "--file",
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
        "-d",
        "--desc",
        required=False,
        type=str,
        help="a description for the password",
        dest="DESC",
    )

    # rm subcommand
    parser_init = subparsers.add_parser(
        name="rm",
        help="delete passwords from lockey's vault",
        description=(
            "Delete paswords from lockey's vault and their metadata in "
            "lockeyconfig.json."
        ),
    )
    parser_init.add_argument(
        "-n",
        "--name",
        nargs="+",
        type=str,
        required=False,
        help="the name of the password(s) to delete as displayed in `lockey ls`",
        dest="NAME",
        action="extend",
    )

    # destroy subcommand
    parser_init = subparsers.add_parser(
        name="destroy",
        help="delete all lockey data",
        description=(
            "Delete all paswords from lockey's vault and their metadata in "
            "lockeyconfig.json. Opposite of `lockey init`."
        ),
    )
    parser_init.add_argument(
        "-y",
        "--yes",
        required=False,
        help="assume yes to prompts and run non-interactively",
        action="store_const",
        const=True,
    )

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()
    print(args)
    if args.command == "init":
        execute_init(args)
    elif args.command == "add":
        execute_add(args)
    elif args.command == "ls":
        execute_ls(args)
    elif args.command == "rm":
        execute_rm(args)
    elif args.command == "destroy":
        execute_destroy(args)
    else:
        print(f"error: command {args.command} not recognized")


if __name__ == "__main__":
    main()
