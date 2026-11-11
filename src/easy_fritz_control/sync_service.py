"""Compares every box's blacklist with the target list and (optionally) overwrites it."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from contextlib import AbstractContextManager
from dataclasses import dataclass

import requests

from easy_fritz_control.app_logger import AppLogger
from easy_fritz_control.blacklist import Blacklist, BlacklistDiff
from easy_fritz_control.fritz_blacklist_client import FritzBlacklistClient
from easy_fritz_control.fritz_session import FritzError
from easy_fritz_control.settings import FritzBoxConfig

ClientOpener = Callable[[FritzBoxConfig], AbstractContextManager[FritzBlacklistClient]]


@dataclass(frozen=True)
class BoxResult:
    """Outcome for one box. `error` is set when the box could not be read or written."""

    box_name: str
    current: Blacklist | None = None
    diff: BlacklistDiff | None = None
    written: bool = False
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None


class SyncService:
    """Runs read -> diff -> write -> verify per box; one failing box never stops the others."""

    def __init__(self, open_client: ClientOpener) -> None:
        self._open_client = open_client
        self._log = AppLogger("sync")

    def run(
        self, boxes: Sequence[FritzBoxConfig], target: Blacklist, write: bool
    ) -> list[BoxResult]:
        return [self._run_box(box, target, write) for box in boxes]

    def _run_box(self, box: FritzBoxConfig, target: Blacklist, write: bool) -> BoxResult:
        try:
            with self._open_client(box) as client:
                current = client.read()
                diff = current.changes_to(target)
                written = write and not diff.is_empty
                if written:
                    client.write(target)
                    _verify(client.read(), target)
                return BoxResult(box.name, current=current, diff=diff, written=written)
        except (FritzError, requests.RequestException) as error:
            self._log.debug(f"{box.name}: {type(error).__name__}")
            return BoxResult(box.name, error=str(error))


def _verify(stored: Blacklist, target: Blacklist) -> None:
    mismatch = stored.changes_to(target)
    if not mismatch.is_empty:
        raise FritzError(
            "box did not store the list as sent; "
            f"missing: {', '.join(mismatch.added) or '-'}; "
            f"unexpected: {', '.join(mismatch.removed) or '-'}"
        )
