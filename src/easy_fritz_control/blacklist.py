"""Blacklist value object: parsing/validation of blacklist.txt and diffing against a box."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from easy_fritz_control.constants import COMMENT_PREFIX, MAX_BLACKLIST_ENTRIES

# The box stores entries as typed (domain or full URL); only reject what would break the
# CRLF-joined list it is sent as.
_INVALID_CHARS_RE = re.compile(r"[\s\x00-\x1f\x7f]")


class BlacklistError(Exception):
    """blacklist.txt is missing or contains an entry the FRITZ!Box would reject."""


@dataclass(frozen=True)
class BlacklistDiff:
    """Changes needed to turn one blacklist into another."""

    added: tuple[str, ...]
    removed: tuple[str, ...]

    @property
    def is_empty(self) -> bool:
        return not self.added and not self.removed


@dataclass(frozen=True)
class Blacklist:
    """A set of blocked domains or URLs, exactly as the box stores them."""

    entries: frozenset[str]

    @classmethod
    def from_lines(cls, lines: Iterable[str]) -> Blacklist:
        """Parse user-maintained lines; blank lines and `#` comments are ignored."""
        entries: set[str] = set()
        for number, raw in enumerate(lines, start=1):
            entry = raw.strip()
            if not entry or entry.startswith(COMMENT_PREFIX):
                continue
            if _INVALID_CHARS_RE.search(entry):
                raise BlacklistError(
                    f"line {number}: '{entry}' contains whitespace or control characters"
                )
            entries.add(entry)
        if len(entries) > MAX_BLACKLIST_ENTRIES:
            raise BlacklistError(
                f"{len(entries)} entries, the FRITZ!Box accepts at most {MAX_BLACKLIST_ENTRIES}"
            )
        return cls(frozenset(entries))

    @classmethod
    def from_file(cls, path: Path) -> Blacklist:
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise BlacklistError(f"blacklist file not found: {path}") from error
        return cls.from_lines(text.splitlines())

    @classmethod
    def from_box_entries(cls, entries: Iterable[str]) -> Blacklist:
        """Wrap entries read from a box without validation: the box already accepted them."""
        return cls(frozenset(e.strip() for e in entries if e.strip()))

    def sorted_entries(self) -> list[str]:
        return sorted(self.entries)

    def changes_to(self, target: Blacklist) -> BlacklistDiff:
        return BlacklistDiff(
            added=tuple(sorted(target.entries - self.entries)),
            removed=tuple(sorted(self.entries - target.entries)),
        )
