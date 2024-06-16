import os
import lockey.main

COMMANDS = ["init", "add", "ls", "rm", "destroy"]

def test_command_names():
    for command in COMMANDS:
        parser = lockey.main.get_parser()
        args = parser.parse_args([command])
        assert args.command == command

def test_init_args():
    path = os.path.expanduser("~/Documents/.lockey/")
    parser = lockey.main.get_parser()
    args = parser.parse_args(["init"])
    assert args.PATH == lockey.main.DEFAULT_DATA_PATH
    args = parser.parse_args(["init", "-f", path])
    assert args.PATH == path
    args = parser.parse_args(["init", "--file", path])
    assert args.PATH == path

def test_destroy_args():
    parser = lockey.main.get_parser()
    args = parser.parse_args(["destroy"])
    assert not args.skip_confirm
    args = parser.parse_args(["destroy", "-y"])
    assert args.skip_confirm == True
    args = parser.parse_args(["destroy", "--yes"])
    assert args.skip_confirm == True
