"""AppLogger: the only place that touches `logging`; also carries the CLI's user output."""

from __future__ import annotations

import logging
import sys

_ROOT = "easy_fritz_control"


class AppLogger:
    """Thin wrapper so level and sink are configured once, never at call sites."""

    def __init__(self, name: str) -> None:
        self._logger = logging.getLogger(f"{_ROOT}.{name}")

    @staticmethod
    def configure(level: str) -> None:
        root = logging.getLogger(_ROOT)
        root.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        root.addHandler(handler)
        root.setLevel(level.upper())

    def debug(self, message: str) -> None:
        self._logger.debug(message)

    def info(self, message: str) -> None:
        self._logger.info(message)

    def warning(self, message: str) -> None:
        self._logger.warning(message)

    def error(self, message: str) -> None:
        self._logger.error(message)
