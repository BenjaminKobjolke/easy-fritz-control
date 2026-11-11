"""Unit tests for SyncService: per-box read, diff, write, verify, error isolation."""

from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from unittest.mock import MagicMock

from pydantic import SecretStr

from easy_fritz_control.blacklist import Blacklist
from easy_fritz_control.fritz_blacklist_client import FritzBlacklistClient
from easy_fritz_control.fritz_session import FritzAuthError
from easy_fritz_control.settings import FritzBoxConfig
from easy_fritz_control.sync_service import SyncService

TARGET = Blacklist.from_lines(["a.com", "b.com"])


def _box(name: str) -> FritzBoxConfig:
    return FritzBoxConfig(name=name, url="http://box.test", password=SecretStr("p"))


def _client(*reads: Blacklist) -> MagicMock:
    client = MagicMock(spec=FritzBlacklistClient)
    client.read.side_effect = list(reads)
    return client


def _opener(clients: dict[str, MagicMock | Exception]):  # type: ignore[no-untyped-def]
    @contextmanager
    def open_client(box: FritzBoxConfig) -> Iterator[MagicMock]:
        client = clients[box.name]
        if isinstance(client, Exception):
            raise client
        yield client

    def opener(box: FritzBoxConfig) -> AbstractContextManager[MagicMock]:
        return open_client(box)

    return opener


def test_dry_run_reports_diff_and_never_writes() -> None:
    client = _client(Blacklist.from_lines(["a.com", "old.com"]))

    [result] = SyncService(_opener({"main": client})).run([_box("main")], TARGET, write=False)

    assert result.ok
    assert result.diff is not None
    assert result.diff.added == ("b.com",)
    assert result.diff.removed == ("old.com",)
    assert not result.written
    client.write.assert_not_called()


def test_sync_writes_target_and_verifies_by_reading_back() -> None:
    client = _client(Blacklist.from_lines(["old.com"]), TARGET)

    [result] = SyncService(_opener({"main": client})).run([_box("main")], TARGET, write=True)

    assert result.ok and result.written
    client.write.assert_called_once_with(TARGET)
    assert client.read.call_count == 2


def test_sync_skips_write_when_box_already_matches() -> None:
    client = _client(TARGET)

    [result] = SyncService(_opener({"main": client})).run([_box("main")], TARGET, write=True)

    assert result.ok and not result.written
    client.write.assert_not_called()


def test_sync_fails_when_box_did_not_store_all_entries() -> None:
    client = _client(Blacklist.from_lines(["old.com"]), Blacklist.from_lines(["a.com"]))

    [result] = SyncService(_opener({"main": client})).run([_box("main")], TARGET, write=True)

    assert not result.ok
    assert result.error is not None and "b.com" in result.error


def test_one_failing_box_does_not_stop_the_others() -> None:
    good = _client(Blacklist.from_lines([]), TARGET)
    opener = _opener({"broken": FritzAuthError("login failed"), "good": good})

    results = SyncService(opener).run([_box("broken"), _box("good")], TARGET, write=True)

    assert [r.ok for r in results] == [False, True]
    assert results[0].error == "login failed"
    good.write.assert_called_once_with(TARGET)
