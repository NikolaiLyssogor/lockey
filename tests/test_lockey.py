import json
import os

import pytest

import lockey.main

# TODO: Add warning with manual confirmation that these tests will override
# data in default lockey locations. It would be easier to maybe only run these
# using github actions?

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


def test_init_destroy():
    parser = lockey.main.get_parser()
    args = parser.parse_args(["init"])
    lockey.main.execute_init(args)
    assert os.path.exists(lockey.main.DEFAULT_DATA_PATH)
    assert os.path.exists(lockey.main.CONFIG_PATH)
    with open(lockey.main.CONFIG_PATH, "r") as f:
        config = json.load(f)
    data_path = config["data_path"]
    assert "data_path" in config.keys()
    assert data_path == lockey.main.DEFAULT_DATA_PATH

    args = parser.parse_args(["destroy", "-y"])
    lockey.main.execute_destroy(args)
    assert not os.path.exists(lockey.main.DEFAULT_DATA_PATH)
    config_head, _ = os.path.split(lockey.main.CONFIG_PATH)
    assert not os.path.exists(config_head)


def test_init_custom_destroy():
    parser = lockey.main.get_parser()
    data_path_head_spec = os.getcwd()
    data_path_spec = os.path.join(data_path_head_spec, ".lockey")
    args = parser.parse_args(["init", "-f", data_path_head_spec])
    lockey.main.execute_init(args)
    assert os.path.exists(data_path_spec)
    assert os.path.exists(lockey.main.CONFIG_PATH)
    with open(lockey.main.CONFIG_PATH, "r") as f:
        config = json.load(f)
    data_path = config["data_path"]
    assert "data_path" in config.keys()
    assert data_path == data_path_spec

    args = parser.parse_args(["destroy", "-y"])
    lockey.main.execute_destroy(args)
    assert not os.path.exists(data_path_spec)
    config_head, _ = os.path.split(lockey.main.CONFIG_PATH)
    assert not os.path.exists(config_head)


def test_abort_destroy_unexpected_config_files():
    parser = lockey.main.get_parser()
    args = parser.parse_args(["init"])
    lockey.main.execute_init(args)

    config_head, _ = os.path.split(lockey.main.CONFIG_PATH)
    extra_filepath = os.path.join(config_head, "extra.txt")
    open(extra_filepath, "a").close()
    args = parser.parse_args(["destroy", "-y"])

    error_msg = r".* found unexpected file .* in config directory"
    with pytest.raises(SystemExit, match=error_msg):
        lockey.main.execute_destroy(args)
    
    os.remove(extra_filepath)
    lockey.main.execute_destroy(args)
