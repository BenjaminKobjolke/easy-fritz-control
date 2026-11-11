"""Login session against the FRITZ!Box web UI (login_sid.lua version 2, AVM-documented)."""

from __future__ import annotations

import hashlib
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests

from easy_fritz_control.constants import DATA_PATH, HTTP_TIMEOUT_SECONDS, INVALID_SID, LOGIN_PATH

_PBKDF2_PREFIX = "2$"
_MAX_LATIN1 = 255


class FritzError(Exception):
    """Base error for everything that goes wrong talking to a FRITZ!Box."""


class FritzAuthError(FritzError):
    """Login failed or no valid session."""


def challenge_response(challenge: str, password: str) -> str:
    """Answer a login challenge: PBKDF2 (FRITZ!OS >= 7.24) or legacy MD5."""
    if challenge.startswith(_PBKDF2_PREFIX):
        _, iter1, salt1, iter2, salt2 = challenge.split("$")
        hash1 = hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), bytes.fromhex(salt1), int(iter1)
        )
        hash2 = hashlib.pbkdf2_hmac("sha256", hash1, bytes.fromhex(salt2), int(iter2))
        return f"{salt2}${hash2.hex()}"
    # AVM: characters outside Latin-1 are replaced by "." before hashing.
    safe = "".join(c if ord(c) <= _MAX_LATIN1 else "." for c in password)
    digest = hashlib.md5(f"{challenge}-{safe}".encode("utf-16-le")).hexdigest()  # noqa: S324
    return f"{challenge}-{digest}"


class FritzSession:
    """Holds the session id (SID) of one FRITZ!Box and posts authenticated data.lua forms."""

    def __init__(self, http: requests.Session, base_url: str) -> None:
        self._http = http
        self._base_url = base_url
        self._sid: str | None = None

    @property
    def sid(self) -> str | None:
        return self._sid

    def login(self, username: str, password: str) -> None:
        info = self._session_info(
            self._http.get(self._url(LOGIN_PATH), timeout=HTTP_TIMEOUT_SECONDS)
        )
        form = {
            # Password-only boxes still expect the name of their default user.
            "username": username or info.last_user,
            "response": challenge_response(info.challenge, password),
        }
        result = self._session_info(
            self._http.post(self._url(LOGIN_PATH), data=form, timeout=HTTP_TIMEOUT_SECONDS)
        )
        if result.sid == INVALID_SID:
            raise FritzAuthError(
                f"login to {self._base_url} failed (wrong user/password?), "
                f"box blocks new logins for {result.block_time} s"
            )
        self._sid = result.sid

    def logout(self) -> None:
        if self._sid is None:
            return
        self._http.post(
            self._url(LOGIN_PATH),
            data={"logout": "1", "sid": self._sid},
            timeout=HTTP_TIMEOUT_SECONDS,
        )
        self._sid = None

    def post_data(self, form: dict[str, str]) -> requests.Response:
        if self._sid is None:
            raise FritzAuthError(f"not logged in to {self._base_url}")
        response = self._http.post(
            self._url(DATA_PATH), data={**form, "sid": self._sid}, timeout=HTTP_TIMEOUT_SECONDS
        )
        response.raise_for_status()
        return response

    def _url(self, path: str) -> str:
        return f"{self._base_url}{path}"

    def _session_info(self, response: requests.Response) -> _SessionInfo:
        try:
            root = ET.fromstring(response.text)
        except ET.ParseError as error:
            raise FritzAuthError(f"{self._base_url} returned no SessionInfo XML") from error
        return _SessionInfo(
            sid=root.findtext("SID", INVALID_SID),
            challenge=root.findtext("Challenge", ""),
            block_time=int(root.findtext("BlockTime", "0")),
            last_user=root.findtext("Users/User[@last='1']", ""),
        )


@dataclass(frozen=True)
class _SessionInfo:
    sid: str
    challenge: str
    block_time: int
    last_user: str
