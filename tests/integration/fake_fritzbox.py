"""Minimal fake FRITZ!Box: login_sid.lua v2 + data.lua kids_blacklist, as seen on FRITZ!OS 7.62."""

from __future__ import annotations

import json
import threading
from collections.abc import Iterator
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs

from easy_fritz_control.fritz_session import challenge_response

CHALLENGE = "2$1000$5A1711$200$5A1722"
VALID_SID = "abcdef0123456789"
INVALID_SID = "0000000000000000"


class FakeFritzBox:
    def __init__(self, password: str, entries: list[str]) -> None:
        self.password = password
        self.entries = list(entries)
        self.logged_out = False

    @contextmanager
    def serve(self) -> Iterator[str]:
        box = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args: object) -> None:  # keep test output clean
                pass

            def do_GET(self) -> None:  # noqa: N802
                self._xml(INVALID_SID)

            def do_POST(self) -> None:  # noqa: N802
                length = int(self.headers.get("Content-Length", "0"))
                form = {k: v[0] for k, v in parse_qs(self.rfile.read(length).decode()).items()}
                if self.path.startswith("/login_sid.lua"):
                    self._login(form)
                elif form.get("sid") != VALID_SID:
                    self._send(403, "text/html", "<html>login</html>")
                else:
                    self._data(form)

            def _login(self, form: dict[str, str]) -> None:
                if form.get("logout"):
                    box.logged_out = True
                    self._xml(INVALID_SID)
                    return
                ok = form.get("response") == challenge_response(CHALLENGE, box.password)
                self._xml(VALID_SID if ok else INVALID_SID)

            def _data(self, form: dict[str, str]) -> None:
                if form.get("apply") == "true":
                    urllist = form.get("urllist", "")
                    box.entries = urllist.split("\r\n") if urllist else []
                    payload: dict[str, object] = {"apply": "ok"}
                else:
                    payload = {
                        "list": [{"_node": f"url{i}", "url": u} for i, u in enumerate(box.entries)],
                        "listtype": "black",
                    }
                body = json.dumps({"pid": "kids_blacklist", "data": payload, "sid": VALID_SID})
                self._send(200, "application/json", body)

            def _xml(self, sid: str) -> None:
                self._send(
                    200,
                    "text/xml",
                    f"<SessionInfo><SID>{sid}</SID><Challenge>{CHALLENGE}</Challenge>"
                    "<BlockTime>0</BlockTime></SessionInfo>",
                )

            def _send(self, status: int, content_type: str, body: str) -> None:
                self.send_response(status)
                self.send_header("Content-Type", content_type)
                self.end_headers()
                self.wfile.write(body.encode())

        server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            yield f"http://127.0.0.1:{server.server_address[1]}"
        finally:
            server.shutdown()
            server.server_close()
