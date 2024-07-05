import argparse
import dataclasses
import getpass
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import typing
from contextlib import contextmanager
from typing import Any, Iterator, Literal, Optional, Tuple, Type, TypeVar

CommandType = Literal["init", "add", "ls", "get", "rm", "destroy"]
COMMANDS: Tuple[CommandType, ...] = typing.get_args(CommandType)

ConfigOption = Literal["data_path", "clipboard_timeout"]
CONFIG_OPTIONS: Tuple[ConfigOption, ...] = typing.get_args(ConfigOption)

DEFAULT_DATA_PATH = os.path.expanduser("~/.lockey")
CONFIG_PATH = os.path.expanduser("~/.config/lockey/")

SUCCESS = "\033[32msuccess:\033[0m"
WARNING = "\033[33mwarning:\033[0m"
ERROR = "\033[31merror:\033[0m"
NOTE = "\033[36mnote:\033[0m"

BUFSIZE = 65536

T = TypeVar("T")
SecretSchema = dict[str, dict[str, str]]
ConfigSchema = dict[str, str | int | SecretSchema]


class ChecksumVerificationError(Exception):
    def __init__(self, message: str = "Checksum could not be verified"):
        self.message = message
        super().__init__(self.message)


def get_version() -> str:
    _DISTRIBUTION_METADATA = importlib.metadata.metadata("lockey")
    return _DISTRIBUTION_METADATA["Version"]


def get_ansi_red(s: str) -> str:
    return f"\033[31m{s}\033[0m"


def get_ansi_green(s: str) -> str:
    return f"\033[32m{s}\033[0m"


def get_ansi_yellow(s: str) -> str:
    return f"\033[33m{s}\033[0m"


def command_requires_gpg(command: CommandType) -> bool:
    if command not in COMMANDS:
        raise ValueError(f"Invalid command {command}")
    if command in ["add", "get"]:
        return True
    else:
        return False


def is_gpg_installed(display_type: Literal["warning", "error"]):
    try:
        result = subprocess.run(
            ["gpg", "--version"],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if result.returncode == 0:
            return
    except (subprocess.CalledProcessError, FileNotFoundError):
        pass

    msg = (
        "{} gpg is not installed on this system and is a required dependency "
        "for lockey"
    )
    # TODO: use python's warnings library
    if display_type == "warning":
        print(msg.format(WARNING))
    elif display_type == "error":
        raise SystemExit(msg.format(ERROR))


def is_sha256_hash(s: str) -> bool:
    if len(s) != 64:
        return False
    try:
        int(s, 16)
        return True
    except ValueError:
        return False


def get_config_metadata(info_type: Literal["filepath", "filename"]) -> str:
    if not os.path.exists(CONFIG_PATH):
        raise SystemExit(f"{ERROR} config directory {CONFIG_PATH} not found")

    config_dir_files = [
        f
        for f in os.listdir(CONFIG_PATH)
        if os.path.isfile(os.path.join(CONFIG_PATH, f))
    ]
    if len(config_dir_files) > 1:
        raise SystemExit(f"{ERROR} unexpected config directory contents")
    elif len(config_dir_files) == 0:
        raise SystemExit(f"{ERROR} config directory is empty")

    config_filename = config_dir_files[0]
    if not is_sha256_hash(config_filename):
        raise SystemExit(
            f"{ERROR} config file name {config_filename} is invalid sha256 hash"
        )

    config_filepath = os.path.join(CONFIG_PATH, config_filename)
    try:
        with open(config_filepath, "rb") as f:
            _ = json.load(f)
    except json.decoder.JSONDecodeError:
        raise SystemExit(f"{ERROR} config file {config_filepath} not valid json")

    if info_type == "filepath":
        return config_filepath
    elif info_type == "filename":
        return config_filename
    else:
        raise ValueError(f"Invalid argument {info_type}")


def get_hash(filepath: str) -> str:
    if not os.path.isfile(filepath):
        raise SystemExit(f"{ERROR} file path to be hashed {filepath} is not file")

    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        while True:
            data = f.read(BUFSIZE)
            if not data:
                break
            sha256.update(data)

    return sha256.hexdigest()


@dataclasses.dataclass
class LockeySecret:
    name: str
    message: str | None
    is_unencrypted: bool | None


@dataclasses.dataclass
class LockeyConfig:
    data_path: str | os.PathLike[Any]
    clipboard_timeout: int = 45
    first_write: dataclasses.InitVar[bool] = False

    def __post_init__(self, first_write: bool):
        if first_write:
            if os.path.exists(self.data_path):
                raise SystemExit(f"{ERROR} directory {self.data_path} already exists")
            if os.path.exists(CONFIG_PATH):
                raise SystemExit(f"{ERROR} directory {CONFIG_PATH} already exists")

            # Make sure the directory passed exists
            data_head, _ = os.path.split(self.data_path)
            if not os.path.exists(data_head):
                raise SystemExit(f"{ERROR} supplied path {data_head} does not exist")
        else:
            if not os.path.exists(self.data_path):
                raise SystemExit(f"{ERROR} vault path {self.data_path} does not exist")
            if self.clipboard_timeout < 0:
                raise SystemExit(
                    f"{ERROR} invalid config value {self.clipboard_timeout} for "
                    "clipboard timeout"
                )


def from_dict(data: dict[Any, Any], data_class: Type[T]) -> T:
    if not dataclasses.is_dataclass(data_class):
        raise ValueError(f"{data_class} is not a dataclass")

    field_types = {f.name: f.type for f in dataclasses.fields(data_class)}

    kwargs = {}
    for field_name, field_type in field_types.items():
        if field_name not in data:
            if isinstance(field_type, Optional[Any]):
                data[field_name] = None
            else:
                raise SystemExit(
                    f"{ERROR} required field {field_name} not in lockey config"
                )

        if dataclasses.is_dataclass(field_type):
            kwargs[field_name] = from_dict(data[field_name], field_type)
        elif hasattr(field_type, "__origin__") and field_type.__origin__ is list:
            item_type = field_type.__args__[0]
            kwargs[field_name] = [
                (
                    from_dict(item, item_type)
                    if dataclasses.is_dataclass(item_type)
                    else item
                )
                for item in data[field_name]
            ]
        else:
            kwargs[field_name] = data[field_name]

    return data_class(**kwargs)


def get_config() -> LockeyConfig:
    config_filepath = get_config_metadata("filepath")
    old_hash = get_config_metadata("filename")
    cur_hash = get_hash(config_filepath)

    if old_hash != cur_hash:
        # TODO: Make sure the context manager doesn't recompute the hash
        raise ChecksumVerificationError
    else:
        with open(config_filepath, "r") as f:
            config = json.load(f)
        return from_dict(config, LockeyConfig)


@contextmanager
def get_verified_config(mode: Literal["r", "w"]) -> Iterator[LockeyConfig]:
    config = get_config()
    checksum_is_valid = True
    try:
        # New config written here
        yield config
    except ChecksumVerificationError:
        checksum_is_valid = False
        raise
    finally:
        if checksum_is_valid and mode == "w":
            config_dict = dataclasses.asdict(config)
            with open(get_config_metadata("filepath"), "w") as f:
                json.dump(config_dict, f, indent=2)

            # Recompute hash and save as filename
            config_filepath = get_config_metadata("filepath")
            new_config_hash = get_hash(config_filepath)
            new_config_filename = os.path.join(CONFIG_PATH, new_config_hash)
            os.rename(config_filepath, new_config_filename)


def get_secrets() -> list[LockeySecret]:
    with get_verified_config("r") as config:
        data_path = config.data_path

    secrets: list[LockeySecret] = []
    for name in os.listdir(data_path):
        secret_fp = os.path.join(data_path, name)
        is_unencrypted = not is_secret_encrypted(secret_fp)
        message = get_xattr("message", secret_fp)
        secret = LockeySecret(name=name, message=message, is_unencrypted=is_unencrypted)
        secrets.append(secret)

    return secrets


def get_secret_filepath_by_name(name: str) -> str | os.PathLike[Any] | None:
    with get_verified_config("r") as config:
        data_path = config.data_path

    for filename in os.listdir(data_path):
        basename, _ = os.path.splitext(filename)
        if basename == name:
            return os.path.join(data_path, filename)

    return None


def set_xattr(
    attr_name: str, attr_value: str, filepath: str | os.PathLike[Any]
) -> None:
    try:
        _ = subprocess.run(
            ["xattr", "-w", attr_name, attr_value, filepath],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError:
        raise SystemExit(
            f"{WARNING} unable to set xattr {attr_name} for secret {filepath}."
        )


def get_xattr(attr_name: str, filepath: str | os.PathLike[Any]) -> str | None:
    try:
        result = subprocess.run(
            ["xattr", "-p", attr_name, filepath],
            capture_output=True,
            text=True,
            check=True,
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return None
    except Exception as e:
        raise SystemExit(
            f"{ERROR} an unknown issue occured when getting xattr {attr_name} "
            f"for {filepath}: {e}"
        )


def encrypt_secret(
    secret: str, passphrase: str, data_path: str | os.PathLike[Any], name: str
) -> str | os.PathLike[Any]:
    output_filepath = os.path.join(data_path, name)
    try:
        command = [
            "gpg",
            "--output",
            output_filepath,
            "--passphrase",
            passphrase,
            "--cipher-algo",
            "AES256",
            "--batch",
            "--yes",
            "--armour",
            "--no-symkey-cache",
            "--symmetric",
        ]
        process = subprocess.Popen(
            command, stdin=subprocess.PIPE, stderr=subprocess.PIPE
        )
        _, stderr = process.communicate(secret.encode())
        if process.returncode != 0:
            error_msg = stderr.decode().strip()
            raise SystemExit(f"{ERROR} unable to encrypt secret: {error_msg}")

        os.chmod(output_filepath, 0o600)
        return output_filepath
    except Exception as e:
        raise SystemExit(
            f"{ERROR} an unknown issue occured while encrypting the secret: {str(e)}"
        )


def decrypt_secret(secret_filepath: str | os.PathLike[Any], passphrase: str) -> str:
    try:
        command = [
            "gpg",
            "--batch",
            "--yes",
            "--no-symkey-cache",
            "--passphrase-fd",
            "0",
            "--decrypt",
            secret_filepath,
        ]
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
        stdout, _ = process.communicate(passphrase.encode())
        if process.returncode != 0:
            raise SystemExit(f"{ERROR} gpg returned a non-zero status code")
        secret = stdout.decode().strip()
        return secret
    except Exception as e:
        raise SystemExit(
            f"{ERROR} an unknown issue occured while encrypting the secret: {str(e)}"
        )


def is_secret_encrypted(secret_fp: str | os.PathLike[Any]):
    MIMETYPE_PLAIN = "text/plain"
    MIMETYPE_ENCRYPTED = "application/pgp-encrypted"

    try:
        result = subprocess.run(
            ["file", "-b", "--mime-type", secret_fp],
            capture_output=True,
            text=True,
            check=True,
        )
        mime_type = result.stdout.strip()
        if mime_type == MIMETYPE_ENCRYPTED:
            return True
        elif mime_type == MIMETYPE_PLAIN:
            return False
        else:
            raise SystemExit(
                f"{ERROR} secret at filepath {secret_fp} has unexpected mime "
                f"type {mime_type}"
            )
    except subprocess.CalledProcessError:
        _, secret_name = os.path.split(secret_fp)
        raise SystemExit(
            f"{ERROR} issue calling `file` in subprocess when determining if "
            f"secret {secret_name} is encrypted"
        )


def send_secret_to_clipboard(secret: str) -> None:
    process = subprocess.Popen(
        "pbcopy", env={"LANG": "en_US.UTF-8"}, stdin=subprocess.PIPE
    )
    process.communicate(secret.encode("utf-8"))


def execute_init(args: argparse.Namespace) -> None:
    # TODO: Set default timeout?
    # https://unix.stackexchange.com/questions/395875/gpg-does-not-ask-for-password
    # Make sure lockey directories are not already initialized
    if args.PATH != DEFAULT_DATA_PATH:
        data_path = os.path.join(args.PATH, ".lockey")
    else:
        data_path = DEFAULT_DATA_PATH

    # Create ~/.lockey and .config/lockey/config.json
    config = LockeyConfig(data_path=data_path, first_write=True)
    os.mkdir(CONFIG_PATH)
    temp_config_filepath = os.path.join(CONFIG_PATH, "tempname.json")
    config_dict = dataclasses.asdict(config)
    with open(temp_config_filepath, "w") as f:
        json.dump(config_dict, f, indent=2)

    os.chmod(temp_config_filepath, 0o600)
    config_hash = get_hash(temp_config_filepath)
    config_filepath = os.path.join(CONFIG_PATH, config_hash)
    os.rename(temp_config_filepath, config_filepath)
    print(f"{SUCCESS} initialized config file in {CONFIG_PATH}")

    os.mkdir(data_path)
    print(f"{SUCCESS} initialized secret vault in {data_path}")


def execute_ls() -> None:
    secrets = get_secrets()
    if not secrets:
        print("no secrets stored")
        return None

    # If name is longer than first line of message will be on different line
    secret_names = [secret.name for secret in secrets]
    longest_name = max(len(name) for name in secret_names)
    max_name_len = min(30, longest_name)
    # Max length of each line of messages
    max_message_len = 40
    gap = " " * (max_name_len + 5)

    print("NAME" + gap[:-4] + "DESCRIPTION")

    for secret in sorted(secrets, key=lambda s: s.name):
        if not secret.message:
            print(secret.name)
            continue

        message_lines = [""]
        message_split = secret.message.split(" ")
        for word in message_split:
            if len(message_lines[-1]) + len(word) + 1 > max_message_len:
                message_lines.append(word + " ")
                continue
            message_lines[-1] = message_lines[-1] + word + " "

        message_lines = [line.strip() for line in message_lines]
        # First line may or may not have part of the description on it
        if len(secret.name) > max_name_len:
            first_line = secret.name
        else:
            first_line_gap = gap[len(secret.name) :]
            first_line = secret.name + first_line_gap + message_lines[0]

        print(first_line)
        if len(secret.name) > max_name_len:
            print(gap + message_lines[0])
        if len(message_lines) > 1:
            for line in message_lines[1:]:
                print(gap + line)


def execute_add(args: argparse.Namespace) -> None:
    # Make sure name is valid
    pattern = re.compile(r"^[a-zA-Z0-9\-_@.]+$")
    if not bool(pattern.match(args.NAME)):
        raise SystemExit(
            f"{ERROR} names must only consists of alphanumeric characters, hyphens, "
            "underscores, periods, or the @ symbol"
        )

    # Make sure secret with this name is not in config file or .lockey
    if get_secret_filepath_by_name(args.NAME) is not None:
        raise SystemExit(
            f"{ERROR} found existing secret in vault with base name {args.NAME}."
            "Please use another name."
        )

    with get_verified_config("r") as config:
        data_path = config.data_path

    if args.PLAIN:
        secret = input("secret: ")
        output_filepath = os.path.join(data_path, args.NAME)
        with open(output_filepath, "a") as f:
            f.write(secret)
    else:
        secret = getpass.getpass(prompt="secret: ")
        passphrase = getpass.getpass(prompt="passphrase: ")
        confirm_passphrase = getpass.getpass(prompt="confirm passphrase: ")
        if passphrase != confirm_passphrase:
            raise SystemExit(f"{ERROR} passphrases do not match")
        output_filepath = encrypt_secret(
            secret=secret, passphrase=passphrase, data_path=data_path, name=args.NAME
        )

    set_xattr(attr_name="message", attr_value=args.MSG, filepath=output_filepath)

    if args.PLAIN:
        print(
            f"{WARNING} secret stored as plaintext in {output_filepath} "
            "(ignore this if that is what was desired)"
        )
    else:
        print(f"{SUCCESS} secret encrypted in {output_filepath}")


def execute_get(args: argparse.Namespace) -> None:
    with get_verified_config("r") as config:
        data_path = config.data_path
        timeout = config.clipboard_timeout

    secret_fp = os.path.join(data_path, args.NAME)
    if not os.path.exists(secret_fp):
        raise SystemExit(f"{ERROR} secret {args.NAME} not found")

    if is_secret_encrypted(secret_fp):
        passphrase = getpass.getpass("passphrase: ")
        secret = decrypt_secret(secret_fp, passphrase)
    else:
        with open(secret_fp, "r") as f:
            secret = f.read()

    send_secret_to_clipboard(secret)

    # Get absolute path to where script is installed
    dirpath = os.path.dirname(os.path.realpath(__file__))
    script_filepath = os.path.join(dirpath, "clear_clipboard.sh")
    subprocess.Popen(["sh", f"{script_filepath}", f"{timeout}"], stdin=subprocess.PIPE)
    print(f"{SUCCESS} secret {args.NAME} copied to clipboard for {timeout} seconds.")


def execute_rm(args: argparse.Namespace) -> None:
    with get_verified_config("r") as config:
        data_path = config.data_path
    secret_fp = os.path.join(data_path, args.NAME)
    if not os.path.exists(secret_fp):
        raise SystemExit(f"{ERROR} secret {secret_fp} not found")
    os.remove(secret_fp)
    print(f"{SUCCESS} secret {args.NAME} removed from vault")


def execute_destroy(args: argparse.Namespace) -> None:
    with get_verified_config("r") as config:
        data_path = config.data_path

    while True:
        if args.skip_confirm == True:
            resp = "y"
            break
        else:
            resp = input("Delete all lockey data (y/n)? ")
        if resp not in ["y", "n"]:
            continue
        elif resp == "n":
            print(f"{NOTE} no data was deleted")
            return None
        else:
            break

    shutil.rmtree(data_path)
    print(f"{SUCCESS} deleted lockey data at {data_path}")
    shutil.rmtree(CONFIG_PATH)
    print(f"{SUCCESS} deleted lockey config at {data_path}")


def get_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lockey",
        description=(
            "A simple CLI password manager written in Python based on gpg."
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
        help="create directories where lockey stores data",
        description=(
            "Initialize the lockey vault in the location specified by the `--file` "
            "argument or in the default location of `$HOME/.lockey/`. Also initializes "
            "lockey's config file at `$HOME/.config/lockey/`. This command should only "
            "be run once when lockey is first installed."
        ),
    )
    parser_init.add_argument(
        "-f",
        "--file",
        required=False,
        help="path to the directory in which to store passwords",
        default=DEFAULT_DATA_PATH,
        dest="PATH",
    )

    # add subcommand
    parser_init = subparsers.add_parser(
        name="add",
        help="add a new password to the vault",
        description=(
            "Add a new password to the vault. Optionally specify a description that "
            "will get displayed with `lockey ls`."
        ),
    )
    parser_init.add_argument(
        "-n",
        "--name",
        required=True,
        type=str,
        help="the name with which you can reference the secret with `lockey get`",
        dest="NAME",
    )
    parser_init.add_argument(
        "-m",
        "--message",
        required=False,
        type=str,
        help="a description for the password (must be in double quotes)",
        dest="MSG",
    )
    parser_init.add_argument(
        "-p",
        "--plaintext",
        action="store_true",
        help=(
            "whether or not to encrypt the secret. unencrypted secrets are stored in "
            "plain text and do not require a passphrase to retrieve"
        ),
        dest="PLAIN",
    )

    # get subcommand
    parser_init = subparsers.add_parser(
        name="get",
        help="decrypt a secret",
        description=("Get a secret from the vault and copy it to your clipboard."),
    )
    parser_init.add_argument(
        "-n",
        "--name",
        required=True,
        type=str,
        help="the name used to encrypt the secret with `lockey add`",
        dest="NAME",
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
            "Delete a password from lockey's vault."
        ),
    )
    parser_init.add_argument(
        "-n",
        "--name",
        type=str,
        required=True,
        help="the name of the secret to delete as displayed in `lockey ls`",
        dest="NAME",
        action="store",
    )

    # destroy subcommand
    parser_init = subparsers.add_parser(
        name="destroy",
        help="delete all lockey data",
        description=(
            "Delete all passwords from lockey's vault and the directory "
            "`$HOME/.config.lockey`."
        ),
    )
    parser_init.add_argument(
        "-y",
        "--yes",
        required=False,
        help="assume yes to prompts and run non-interactively",
        action="store_const",
        const=True,
        dest="skip_confirm",
    )

    return parser


def main():
    parser = get_parser()
    args = parser.parse_args()
    if command_requires_gpg(args.command):
        display_type = "error"
    else:
        display_type = "warning"
    is_gpg_installed(display_type)

    if args.command == "init":
        execute_init(args)
    elif args.command == "add":
        execute_add(args)
    elif args.command == "get":
        execute_get(args)
    elif args.command == "ls":
        execute_ls()
    elif args.command == "rm":
        execute_rm(args)
    elif args.command == "destroy":
        execute_destroy(args)
    else:
        raise SystemExit(f"{ERROR} command {args.command} not recognized")
