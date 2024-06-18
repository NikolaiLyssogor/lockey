import json
import os

import pytest

import lockey.main

# TODO: Add warning with manual confirmation that these tests will override
# data in default lockey locations. It would be easier to maybe only run these
# using github actions?

COMMANDS = ["init", "add", "ls", "rm", "destroy"]


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


def test_init_destroy_basic():
    parser = lockey.main.get_parser()
    args = parser.parse_args(["init"])
    lockey.main.execute_init(args)

    assert os.path.exists(lockey.main.DEFAULT_DATA_PATH)
    config_dir_files = os.listdir(lockey.main.CONFIG_PATH)
    assert len(config_dir_files) == 1
    config_filename = config_dir_files[0]
    config_filepath = os.path.join(lockey.main.CONFIG_PATH, config_filename)
    assert os.path.isfile(config_filepath)
    assert lockey.main.is_sha256_hash(config_filename)
    with open(config_filepath, "r") as f:
        config = json.load(f)
    data_path = config["data_path"]
    assert "data_path" in config.keys()
    assert data_path == lockey.main.DEFAULT_DATA_PATH

    args = parser.parse_args(["destroy", "-y"])
    lockey.main.execute_destroy(args)
    assert not os.path.exists(lockey.main.DEFAULT_DATA_PATH)
    assert not os.path.exists(lockey.main.CONFIG_PATH)


def test_init_custom_destroy_basic():
    parser = lockey.main.get_parser()
    data_path_head_spec = os.getcwd()
    data_path_spec = os.path.join(data_path_head_spec, ".lockey")
    args = parser.parse_args(["init", "-f", data_path_head_spec])
    lockey.main.execute_init(args)
    assert os.path.exists(data_path_spec)
    assert os.path.exists(lockey.main.CONFIG_PATH)
    config_filepath = lockey.main.get_config_metadata("filepath")
    with open(config_filepath, "r") as f:
        config = json.load(f)
    data_path = config["data_path"]
    assert "data_path" in config.keys()
    assert data_path == data_path_spec

    args = parser.parse_args(["destroy", "-y"])
    lockey.main.execute_destroy(args)
    assert not os.path.exists(data_path_spec)
    assert not os.path.exists(lockey.main.CONFIG_PATH)


def test_destroy_unexpected_config_files():
    parser = lockey.main.get_parser()
    args = parser.parse_args(["init"])
    lockey.main.execute_init(args)

    extra_filepath = os.path.join(lockey.main.CONFIG_PATH, "extra.txt")
    open(extra_filepath, "a").close()
    args = parser.parse_args(["destroy", "-y"])

    error_msg = r".* unexpected config directory contents"
    with pytest.raises(SystemExit, match=error_msg):
        lockey.main.execute_destroy(args)

    os.remove(extra_filepath)
    lockey.main.execute_destroy(args)


def test_destroy_missing_data_path():
    parser = lockey.main.get_parser()
    args = parser.parse_args(["init"])
    lockey.main.execute_init(args)

    config_filepath = lockey.main.get_config_metadata("filepath")
    with open(config_filepath, "rb") as f:
        config = json.load(f)
    data_path = config["data_path"]
    os.rmdir(data_path)

    args = parser.parse_args(["destroy", "-y"])
    error_msg = r".* secrets directory .* specified in .* not found"
    with pytest.raises(SystemExit, match=error_msg):
        lockey.main.execute_destroy(args)

    os.remove(config_filepath)
    os.rmdir(lockey.main.CONFIG_PATH)


def test_destroy_missing_config():
    parser = lockey.main.get_parser()
    args = parser.parse_args(["init"])
    lockey.main.execute_init(args)

    os.remove(lockey.main.get_config_metadata("filepath"))

    args = parser.parse_args(["destroy", "-y"])
    error_msg = r".* config directory is empty"
    with pytest.raises(SystemExit, match=error_msg):
        lockey.main.execute_destroy(args)

    os.rmdir(lockey.main.CONFIG_PATH)
    os.rmdir(lockey.main.DEFAULT_DATA_PATH)
