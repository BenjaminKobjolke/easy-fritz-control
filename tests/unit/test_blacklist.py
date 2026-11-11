"""Unit tests for parsing, validating and diffing blacklists."""

from pathlib import Path

import pytest

from easy_fritz_control.blacklist import Blacklist, BlacklistError
from easy_fritz_control.constants import MAX_BLACKLIST_ENTRIES


def test_from_lines_strips_dedupes_and_skips_comments() -> None:
    blacklist = Blacklist.from_lines(
        ["  https://www.heise.de/ ", "", "# a comment", "ads.example.net", "ads.example.net"]
    )

    assert blacklist.sorted_entries() == ["ads.example.net", "heise.de"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("http://bing.com", "bing.com"),
        ("https://bing.com/", "bing.com"),
        ("HTTPS://WWW.bing.com", "bing.com"),
        ("www.bing.com", "bing.com"),
        ("https://x.com/a/", "x.com/a"),
    ],
)
def test_from_lines_strips_scheme_www_and_trailing_slash(raw: str, expected: str) -> None:
    assert Blacklist.from_lines([raw]).sorted_entries() == [expected]


def test_from_lines_dedupes_after_normalizing() -> None:
    assert Blacklist.from_lines(["bing.com", "http://bing.com"]).sorted_entries() == ["bing.com"]


def test_from_lines_rejects_entry_without_domain() -> None:
    with pytest.raises(BlacklistError, match="line 1"):
        Blacklist.from_lines(["https://"])


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


def test_from_file_rewrites_cleaned_entries_keeping_comments(tmp_path: Path) -> None:
    path = tmp_path / "blacklist.txt"
    path.write_text("# c\n\nhttp://bing.com\nbing.com\nwww.x.de/\n", encoding="utf-8")

    blacklist = Blacklist.from_file(path)

    assert blacklist.sorted_entries() == ["bing.com", "x.de"]
    assert path.read_text(encoding="utf-8").splitlines() == ["# c", "", "bing.com", "x.de"]


def test_from_file_leaves_clean_file_untouched(tmp_path: Path) -> None:
    path = tmp_path / "blacklist.txt"
    path.write_bytes(b"one.com\ntwo.com")

    Blacklist.from_file(path)

    assert path.read_bytes() == b"one.com\ntwo.com"


def test_from_file_invalid_entry_does_not_rewrite(tmp_path: Path) -> None:
    path = tmp_path / "blacklist.txt"
    path.write_bytes(b"http://bing.com\nbad entry\n")

    with pytest.raises(BlacklistError, match="line 2"):
        Blacklist.from_file(path)
    assert path.read_bytes() == b"http://bing.com\nbad entry\n"


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
