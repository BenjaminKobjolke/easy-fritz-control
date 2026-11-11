"""Unit tests for the FRITZ!Box login (login_sid.lua, version 2)."""

from unittest.mock import MagicMock

import pytest
import requests

from easy_fritz_control.constants import INVALID_SID
from easy_fritz_control.fritz_session import FritzAuthError, FritzSession, challenge_response

BASE_URL = "http://box.test"
CHALLENGE = "2$10000$5A1711$2000$5A1722"


def _session_info(sid: str, challenge: str = CHALLENGE, block_time: int = 0) -> str:
    return (
        f"<SessionInfo><SID>{sid}</SID><Challenge>{challenge}</Challenge>"
        f"<BlockTime>{block_time}</BlockTime></SessionInfo>"
    )


def _response(text: str) -> MagicMock:
    response = MagicMock(spec=requests.Response)
    response.text = text
    return response


def test_challenge_response_pbkdf2_matches_avm_example() -> None:
    # Example vector from AVM's "Session-IDs im FRITZ!Box Webinterface" paper.
    assert challenge_response(CHALLENGE, "1example!") == (
        "5A1722$1798a1672bca7c6463d6b245f82b53703b0f50813401b03e4045a5861e689adb"
    )


def test_challenge_response_md5_fallback_matches_avm_example() -> None:
    assert challenge_response("1234567z", "äbc") == "1234567z-9e224a41eeefa284df7bb0f26c2913e2"


def test_login_posts_username_and_response_and_stores_sid() -> None:
    http = MagicMock(spec=requests.Session)
    http.get.return_value = _response(_session_info(INVALID_SID))
    http.post.return_value = _response(_session_info("abcdef0123456789"))
    session = FritzSession(http, BASE_URL)

    session.login("admin", "1example!")

    assert session.sid == "abcdef0123456789"
    form = http.post.call_args.kwargs["data"]
    assert form["username"] == "admin"
    assert form["response"].startswith("5A1722$1798a167")


def test_login_without_username_uses_last_user_offered_by_box() -> None:
    challenge_xml = _session_info(INVALID_SID).replace(
        "</SessionInfo>",
        '<Users><User>other</User><User last="1">fritz1234</User></Users></SessionInfo>',
    )
    http = MagicMock(spec=requests.Session)
    http.get.return_value = _response(challenge_xml)
    http.post.return_value = _response(_session_info("abcdef0123456789"))

    FritzSession(http, BASE_URL).login("", "pw")

    assert http.post.call_args.kwargs["data"]["username"] == "fritz1234"


def test_login_with_wrong_password_raises_auth_error_with_block_time() -> None:
    http = MagicMock(spec=requests.Session)
    http.get.return_value = _response(_session_info(INVALID_SID))
    http.post.return_value = _response(_session_info(INVALID_SID, block_time=8))
    session = FritzSession(http, BASE_URL)

    with pytest.raises(FritzAuthError, match="8 s"):
        session.login("admin", "wrong")


def test_post_data_without_login_raises_auth_error() -> None:
    session = FritzSession(MagicMock(spec=requests.Session), BASE_URL)

    with pytest.raises(FritzAuthError):
        session.post_data({"page": "x"})


def test_post_data_adds_sid_to_form() -> None:
    http = MagicMock(spec=requests.Session)
    http.get.return_value = _response(_session_info(INVALID_SID))
    http.post.return_value = _response(_session_info("abcdef0123456789"))
    session = FritzSession(http, BASE_URL)
    session.login("admin", "pw")

    session.post_data({"page": "x"})

    assert http.post.call_args.kwargs["data"] == {"page": "x", "sid": "abcdef0123456789"}


def test_logout_posts_logout_and_forgets_sid() -> None:
    http = MagicMock(spec=requests.Session)
    http.get.return_value = _response(_session_info(INVALID_SID))
    http.post.return_value = _response(_session_info("abcdef0123456789"))
    session = FritzSession(http, BASE_URL)
    session.login("admin", "pw")

    session.logout()

    assert http.post.call_args.kwargs["data"]["logout"] == "1"
    assert session.sid is None
