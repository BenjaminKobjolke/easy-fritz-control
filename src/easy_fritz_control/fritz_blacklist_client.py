"""Reads and writes the parental-control website blacklist through the web UI's data.lua."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import requests
import urllib3

from easy_fritz_control.blacklist import Blacklist
from easy_fritz_control.constants import (
    APPLY_OK,
    BLACKLIST_LIST_TYPE,
    BLACKLIST_PAGE,
    BLACKLIST_SEPARATOR,
    UI_LANGUAGE,
)
from easy_fritz_control.fritz_session import FritzError, FritzSession
from easy_fritz_control.settings import FritzBoxConfig


class FritzBlacklistClient:
    """Blacklist access for one logged-in box. AVM documents no API for this list."""

    def __init__(self, session: FritzSession) -> None:
        self._session = session

    def read(self) -> Blacklist:
        data = self._post({"xhrId": "all"})
        entries = data.get("list")
        if not isinstance(entries, list):
            raise FritzError("unexpected blacklist response (no data.list)")
        return Blacklist.from_box_entries(str(item.get("url", "")) for item in entries)

    def write(self, blacklist: Blacklist) -> None:
        """Replace the whole list; the web UI always sends the complete list."""
        data = self._post(
            {
                "urllist": BLACKLIST_SEPARATOR.join(blacklist.sorted_entries()),
                "listtype": BLACKLIST_LIST_TYPE,
                "apply": "true",
            }
        )
        if data.get("apply") != APPLY_OK:
            raise FritzError(f"box rejected the blacklist (apply={data.get('apply')!r})")

    def _post(self, fields: dict[str, str]) -> dict[str, Any]:
        response = self._session.post_data(
            {"xhr": "1", "lang": UI_LANGUAGE, "page": BLACKLIST_PAGE, **fields}
        )
        try:
            payload = response.json()
        except ValueError as error:
            raise FritzError("unexpected blacklist response (not JSON)") from error
        data = payload.get("data") if isinstance(payload, dict) else None
        if not isinstance(data, dict):
            raise FritzError("unexpected blacklist response (no data object)")
        return data


@contextmanager
def open_client(box: FritzBoxConfig) -> Iterator[FritzBlacklistClient]:
    """Log in, hand out a client, always log out again (boxes limit concurrent sessions)."""
    if box.verify_tls is False:
        # Opted in per box in boxes.json; the per-request warning would only add noise.
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
    with requests.Session() as http:
        http.verify = box.verify_tls
        session = FritzSession(http, box.url)
        session.login(box.username, box.password.get_secret_value())
        try:
            yield FritzBlacklistClient(session)
        finally:
            session.logout()
