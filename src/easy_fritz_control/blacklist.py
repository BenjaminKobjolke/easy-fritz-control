"""Blacklist value object: parsing/validation of blacklist.txt and diffing against a box."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from pathlib import Path

from easy_fritz_control.app_logger import AppLogger
from easy_fritz_control.constants import COMMENT_PREFIX, MAX_BLACKLIST_ENTRIES

_log = AppLogger("blacklist")

# The box stores entries as typed (domain or full URL); only reject what would break the
# CRLF-joined list it is sent as.
_INVALID_CHARS_RE = re.compile(r"[\s\x00-\x1f\x7f]")
# AVM matches by domain: `bing.com` already covers http, https and `www.`.
_PREFIX_RE = re.compile(r"^(?:[a-z][a-z0-9+.-]*://)?(?:www\.)?", re.IGNORECASE)


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
        """Parse user-maintained lines; blank lines and `#` comments are ignored.

        Scheme, a leading `www.` and trailing `/` are stripped: `http://bing.com` -> `bing.com`.
        """
        return cls._parse(lines)[0]

    @classmethod
    def _parse(cls, lines: Iterable[str]) -> tuple[Blacklist, list[str]]:
        """Return the blacklist plus the file lines with entries cleaned and duplicates dropped."""
        entries: set[str] = set()
        cleaned: list[str] = []
        for number, raw in enumerate(lines, start=1):
            entry = raw.strip()
            if not entry or entry.startswith(COMMENT_PREFIX):
                cleaned.append(raw)
                continue
            if _INVALID_CHARS_RE.search(entry):
                raise BlacklistError(
                    f"line {number}: '{entry}' contains whitespace or control characters"
                )
            domain = _PREFIX_RE.sub("", entry).rstrip("/")
            if not domain:
                raise BlacklistError(f"line {number}: '{entry}' has no domain")
            if domain not in entries:
                cleaned.append(domain)
                entries.add(domain)
        if len(entries) > MAX_BLACKLIST_ENTRIES:
            raise BlacklistError(
                f"{len(entries)} entries, the FRITZ!Box accepts at most {MAX_BLACKLIST_ENTRIES}"
            )
        return cls(frozenset(entries)), cleaned

    @classmethod
    def from_file(cls, path: Path) -> Blacklist:
        """Load blacklist.txt and rewrite it in place with cleaned, deduplicated entries."""
        try:
            text = path.read_text(encoding="utf-8")
        except FileNotFoundError as error:
            raise BlacklistError(f"blacklist file not found: {path}") from error
        lines = text.splitlines()
        blacklist, cleaned = cls._parse(lines)
        if cleaned != lines:
            path.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
            _log.info(f"cleaned {path}")
        return blacklist

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
