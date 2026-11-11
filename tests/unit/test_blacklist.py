"""Unit tests for parsing, validating and diffing blacklists."""

from pathlib import Path

import pytest

from easy_fritz_control.blacklist import Blacklist, BlacklistError
from easy_fritz_control.constants import MAX_BLACKLIST_ENTRIES


def test_from_lines_strips_dedupes_and_skips_comments() -> None:
    blacklist = Blacklist.from_lines(
        ["  https://www.heise.de/ ", "", "# a comment", "ads.example.net", "ads.example.net"]
    )

    assert blacklist.sorted_entries() == ["ads.example.net", "https://www.heise.de/"]


@pytest.mark.parametrize("bad_entry", ["exa mple.com", "bad\tentry.com", "bad\x00.com"])
def test_from_lines_rejects_entries_with_whitespace_or_control_chars(bad_entry: str) -> None:
    with pytest.raises(BlacklistError, match="line 2"):
        Blacklist.from_lines(["good.com", bad_entry])


def test_from_lines_rejects_more_entries_than_the_box_accepts() -> None:
    lines = [f"host{i}.example.com" for i in range(MAX_BLACKLIST_ENTRIES + 1)]

    with pytest.raises(BlacklistError, match=str(MAX_BLACKLIST_ENTRIES)):
        Blacklist.from_lines(lines)


def test_from_file_reads_utf8_file(tmp_path: Path) -> None:
    path = tmp_path / "blacklist.txt"
    path.write_text("one.com\ntwo.com\n", encoding="utf-8")

    assert Blacklist.from_file(path).sorted_entries() == ["one.com", "two.com"]


def test_from_file_missing_file_raises_blacklist_error(tmp_path: Path) -> None:
    with pytest.raises(BlacklistError, match="not found"):
        Blacklist.from_file(tmp_path / "missing.txt")


def test_changes_to_lists_added_and_removed_sorted() -> None:
    current = Blacklist.from_lines(["keep.com", "old.com"])
    target = Blacklist.from_lines(["keep.com", "new.com", "another.com"])

    diff = current.changes_to(target)

    assert diff.added == ("another.com", "new.com")
    assert diff.removed == ("old.com",)
    assert not diff.is_empty


def test_changes_to_identical_list_is_empty() -> None:
    current = Blacklist.from_lines(["a.com"])

    assert current.changes_to(Blacklist.from_lines(["a.com"])).is_empty
