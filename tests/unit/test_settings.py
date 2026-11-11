"""Unit tests for loading and validating boxes.json."""

import json
from pathlib import Path

import pytest

from easy_fritz_control.settings import ConfigError, load_config

BOX = {"name": "main", "url": "http://192.168.178.1/", "username": "u", "password": "p"}


def _write(tmp_path: Path, data: object) -> Path:
    path = tmp_path / "boxes.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_load_config_resolves_blacklist_next_to_config_and_strips_url_slash(
    tmp_path: Path,
) -> None:
    config = load_config(_write(tmp_path, {"boxes": [BOX]}))

    assert config.blacklist_file == tmp_path / "blacklist.txt"
    assert config.boxes[0].url == "http://192.168.178.1"
    assert config.boxes[0].password.get_secret_value() == "p"


def test_password_is_hidden_in_repr(tmp_path: Path) -> None:
    config = load_config(_write(tmp_path, {"boxes": [BOX]}))

    assert "'p'" not in repr(config.boxes[0])


@pytest.mark.parametrize(
    "data",
    [
        {"boxes": []},
        {"boxes": [{**BOX, "url": "192.168.178.1"}]},
        {"boxes": [BOX, BOX]},
        {"boxes": [{**BOX, "name": ""}]},
    ],
    ids=["no-boxes", "url-without-scheme", "duplicate-names", "empty-name"],
)
def test_invalid_config_raises_config_error(tmp_path: Path, data: object) -> None:
    with pytest.raises(ConfigError):
        load_config(_write(tmp_path, data))


def test_missing_config_file_raises_config_error(tmp_path: Path) -> None:
    with pytest.raises(ConfigError, match="not found"):
        load_config(tmp_path / "boxes.json")


def test_select_boxes_by_name(tmp_path: Path) -> None:
    other = {**BOX, "name": "repeater"}
    config = load_config(_write(tmp_path, {"boxes": [BOX, other]}))

    assert [b.name for b in config.select_boxes("repeater")] == ["repeater"]
    assert len(config.select_boxes(None)) == 2
    with pytest.raises(ConfigError, match="unknown"):
        config.select_boxes("nope")
