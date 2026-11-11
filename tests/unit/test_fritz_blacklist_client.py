"""Unit tests for the data.lua blacklist requests (shapes captured from FRITZ!OS 7.62)."""

import json
from unittest.mock import MagicMock

import pytest
import requests

from easy_fritz_control import fritz_blacklist_client
from easy_fritz_control.blacklist import Blacklist
from easy_fritz_control.fritz_blacklist_client import FritzBlacklistClient, open_client
from easy_fritz_control.fritz_session import FritzError, FritzSession
from easy_fritz_control.settings import FritzBoxConfig


def _response(payload: object) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.json.return_value = payload
    return response


def test_read_returns_urls_from_data_list() -> None:
    session = MagicMock(spec=FritzSession)
    session.post_data.return_value = _response(
        {
            "pid": "kids_blacklist",
            "data": {
                "list": [
                    {"_node": "url0", "url": "https://www.heise.de/"},
                    {"_node": "url1", "url": "https://web.de/"},
                ],
                "listtype": "black",
            },
        }
    )

    blacklist = FritzBlacklistClient(session).read()

    assert blacklist.sorted_entries() == ["https://web.de/", "https://www.heise.de/"]
    form = session.post_data.call_args.args[0]
    assert form["page"] == "kids_blacklist"
    assert form["xhrId"] == "all"


def test_read_empty_list() -> None:
    session = MagicMock(spec=FritzSession)
    session.post_data.return_value = _response({"data": {"list": [], "listcount": 0}})

    assert FritzBlacklistClient(session).read().entries == frozenset()


def test_read_unexpected_json_raises_fritz_error() -> None:
    session = MagicMock(spec=FritzSession)
    session.post_data.return_value = _response({"pid": "login"})

    with pytest.raises(FritzError, match="unexpected"):
        FritzBlacklistClient(session).read()


def test_read_non_json_raises_fritz_error() -> None:
    session = MagicMock(spec=FritzSession)
    response = MagicMock(spec=requests.Response)
    response.json.side_effect = json.JSONDecodeError("x", "", 0)
    session.post_data.return_value = response

    with pytest.raises(FritzError, match="unexpected"):
        FritzBlacklistClient(session).read()


def test_write_sends_crlf_joined_sorted_list_and_apply() -> None:
    session = MagicMock(spec=FritzSession)
    session.post_data.return_value = _response({"data": {"apply": "ok"}})

    FritzBlacklistClient(session).write(Blacklist.from_lines(["https://web.de/", "a.com"]))

    form = session.post_data.call_args.args[0]
    assert form["urllist"] == "a.com\r\nweb.de"
    assert form["listtype"] == "black"
    assert form["apply"] == "true"
    assert form["page"] == "kids_blacklist"


def test_write_without_apply_ok_raises_fritz_error() -> None:
    session = MagicMock(spec=FritzSession)
    session.post_data.return_value = _response({"data": {"apply": "error"}})

    with pytest.raises(FritzError, match="rejected"):
        FritzBlacklistClient(session).write(Blacklist.from_lines(["a.com"]))


def test_open_client_applies_verify_tls_to_http_session(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[object] = []

    def fake_session(http: requests.Session, base_url: str) -> MagicMock:
        seen.append(http.verify)
        return MagicMock(spec=FritzSession)

    monkeypatch.setattr(fritz_blacklist_client, "FritzSession", fake_session)
    box = FritzBoxConfig(name="b", url="https://192.168.178.1", password="p", verify_tls=False)

    with open_client(box):
        pass

    assert seen == [False]
