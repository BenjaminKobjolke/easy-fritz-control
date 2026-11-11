"""End-to-end: CLI against two fake FRITZ!Boxes over real HTTP."""

import json
from pathlib import Path

import pytest

from easy_fritz_control.cli import EXIT_BAD_INPUT, EXIT_BOX_FAILED, EXIT_OK, main
from tests.integration.fake_fritzbox import FakeFritzBox

BLACKLIST = "# kids\nhttps://www.heise.de/\nweb.de\n"


def _setup(tmp_path: Path, urls: list[str], passwords: list[str]) -> Path:
    (tmp_path / "blacklist.txt").write_text(BLACKLIST, encoding="utf-8")
    boxes = [
        {"name": f"box{i}", "url": url, "username": "admin", "password": pw}
        for i, (url, pw) in enumerate(zip(urls, passwords, strict=True))
    ]
    config = tmp_path / "boxes.json"
    config.write_text(json.dumps({"boxes": boxes}), encoding="utf-8")
    return config


def test_sync_makes_both_boxes_match_blacklist_file(tmp_path: Path) -> None:
    first = FakeFritzBox("pw1", ["old.example"])
    second = FakeFritzBox("pw2", [])
    with first.serve() as url1, second.serve() as url2:
        config = _setup(tmp_path, [url1, url2], ["pw1", "pw2"])

        assert main(["--config", str(config), "sync"]) == EXIT_OK

    assert sorted(first.entries) == ["https://www.heise.de/", "web.de"]
    assert sorted(second.entries) == ["https://www.heise.de/", "web.de"]
    assert first.logged_out and second.logged_out


def test_diff_writes_nothing(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    box = FakeFritzBox("pw", ["old.example"])
    with box.serve() as url:
        config = _setup(tmp_path, [url], ["pw"])

        assert main(["--config", str(config), "diff"]) == EXIT_OK

    assert box.entries == ["old.example"]
    output = capsys.readouterr().out
    assert "+ web.de" in output and "- old.example" in output


def test_wrong_password_on_one_box_still_syncs_the_other(tmp_path: Path) -> None:
    broken = FakeFritzBox("right", [])
    good = FakeFritzBox("pw", [])
    with broken.serve() as url1, good.serve() as url2:
        config = _setup(tmp_path, [url1, url2], ["wrong", "pw"])

        assert main(["--config", str(config), "sync"]) == EXIT_BOX_FAILED

    assert broken.entries == []
    assert sorted(good.entries) == ["https://www.heise.de/", "web.de"]


def test_missing_config_returns_bad_input(tmp_path: Path) -> None:
    assert main(["--config", str(tmp_path / "nope.json"), "sync"]) == EXIT_BAD_INPUT
