import argparse
import importlib.metadata
import json
import os

DEFAULT_DATA_PATH = os.path.expanduser("~/.lockey")
CONFIG_PATH = os.path.expanduser("~/.config/lockey/config.json")
VERSION_FALLBACK = "0.1.0"


ConfigMetadata = dict[str, str]
SecretMetadata = dict[str, dict[str, str]]
ConfigSchema = dict[str, ConfigMetadata | SecretMetadata]


def get_version() -> str:
    _DISTRIBUTION_METADATA = importlib.metadata.metadata("lockey")
    return _DISTRIBUTION_METADATA["Version"]

def get_ansi_red(s: str) -> str:
    return f"\033[31m{s}\033[0m"

def get_ansi_green(s: str) -> str:
    return f"\033[32m{s}\033[0m"

def execute_init(args: argparse.Namespace) -> None:
    # Make sure lockey directories are not already initialized
    config_head, _ = os.path.split(CONFIG_PATH)
    if os.path.exists(args.PATH):
        print(f"{get_ansi_red("error:")} directory {args.PATH} already exists")
        exit(1)
    if os.path.exists(config_head):
        print(f"{get_ansi_red("error:")} directory {config_head} already exists")
        exit(1)

    # Make sure the directory passed exists
    headdir, _ = os.path.split(args.PATH)
    if not os.path.exists(headdir):
        print(f"{get_ansi_red("error:")} head of supplied path {headdir} does not exist")
        exit(1)

    # Create ~/.lockey and .config/lockey/config.json
    config_contents: ConfigSchema = {
        "config": {"data_path": args.PATH},
    }
    os.mkdir(config_head)
    with open(CONFIG_PATH, "w") as f:
        json.dump(config_contents, f)
    print(f"{get_ansi_green("success:")} initialized config file in {CONFIG_PATH}")
    os.mkdir(args.PATH)
    print(f"{get_ansi_green("success:")} initialized secret vault in {args.PATH}")
    exit(0)


def execute_configure(args: argparse.Namespace) -> None:
    raise NotImplementedError


def execute_ls(args: argparse.Namespace) -> None:
    raise NotImplementedError


def execute_add(args: argparse.Namespace) -> None:
    raise NotImplementedError


def execute_get(args: argparse.Namespace) -> None:
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

    # add subcommand
    parser_init = subparsers.add_parser(
        name="add",
        help="add a new password to the vault",
        description=(
            "Add a new password to the vault. It's description, if supplied, is saved "
            "in lockeyconfig.json."
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

    # ls subcommand
    parser_init = subparsers.add_parser(
        name="ls",
        help="list the passwords you currently have saved",
        description=(
            "List all of the passwords saved in lockey's vault along with their "
            "description if they exist."
        ),
    )

    # rm subcommand
    parser_init = subparsers.add_parser(
        name="rm",
        help="delete a password from the vault",
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
    elif args.command == "configure":
        execute_configure(args)
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
