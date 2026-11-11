"""Command line entry point: `show`, `diff` and `sync`; central error handling and exit codes."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from enum import StrEnum
from pathlib import Path

from easy_fritz_control.app_logger import AppLogger
from easy_fritz_control.blacklist import Blacklist, BlacklistError
from easy_fritz_control.constants import DEFAULT_LOG_LEVEL
from easy_fritz_control.fritz_blacklist_client import open_client
from easy_fritz_control.settings import ConfigError, default_config_path, load_config
from easy_fritz_control.sync_service import BoxResult, SyncService

EXIT_OK = 0
EXIT_BOX_FAILED = 1
EXIT_BAD_INPUT = 2


class Command(StrEnum):
    SHOW = "show"
    DIFF = "diff"
    SYNC = "sync"


_HELP = {
    Command.SHOW: "list each box's current blacklist",
    Command.DIFF: "show what sync would change (writes nothing)",
    Command.SYNC: "overwrite each box's blacklist with blacklist.txt",
}

_log = AppLogger("cli")


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    command = Command(args.command)
    AppLogger.configure(DEFAULT_LOG_LEVEL)
    try:
        config = load_config(args.config)
        AppLogger.configure(config.log_level)
        target = Blacklist.from_file(config.blacklist_file)
        boxes = config.select_boxes(args.box)
    except (ConfigError, BlacklistError) as error:
        _log.error(f"ERROR: {error}")
        return EXIT_BAD_INPUT
    results = SyncService(open_client).run(boxes, target, write=command is Command.SYNC)
    for result in results:
        _report(result, command)
    return EXIT_OK if all(r.ok for r in results) else EXIT_BOX_FAILED


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="easy-fritz-control", description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config_path())
    parser.add_argument("--box", help="only this box (name from boxes.json)")
    commands = parser.add_subparsers(dest="command", required=True)
    for command in Command:
        commands.add_parser(command.value, help=_HELP[command])
    return parser


def _report(result: BoxResult, command: Command) -> None:
    if result.error is not None or result.current is None or result.diff is None:
        _log.error(f"[{result.box_name}] FAILED: {result.error}")
        return
    if command is Command.SHOW:
        _log.info(f"[{result.box_name}] {len(result.current.entries)} entries")
        for entry in result.current.sorted_entries():
            _log.info(f"  {entry}")
        return
    if result.diff.is_empty:
        _log.info(f"[{result.box_name}] up to date")
        return
    verb = "updated" if result.written else "would change"
    _log.info(f"[{result.box_name}] {verb}:")
    for entry in result.diff.added:
        _log.info(f"  + {entry}")
    for entry in result.diff.removed:
        _log.info(f"  - {entry}")
