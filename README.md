# easy-fritz-control

Keep the parental-control **website blacklist** (Internet > Filter > Listen >
"Gesperrte Internetseiten") identical on several FRITZ!Boxes. `blacklist.txt` in this
directory is the single source of truth; `sync` overwrites every box's blacklist with it.

## Requirements

- Windows, [uv](https://docs.astral.sh/uv/) (installs Python 3.11/3.12 itself)
- FRITZ!Box web UI reachable over the LAN, FRITZ!OS with `login_sid.lua?version=2`
  (7.24 or newer; developed against a FRITZ!Box 7490 with FRITZ!OS 7.62)

## Setup

```bat
install.bat
copy boxes.example.json boxes.json
copy blacklist.example.txt blacklist.txt
```

Edit `boxes.json`:

| Key              | Meaning                                                            |
|------------------|--------------------------------------------------------------------|
| `boxes[].name`   | Unique name, used for output and `--box`                           |
| `boxes[].url`    | Web UI address, e.g. `http://fritz.box` or `http://192.168.178.1`  |
| `boxes[].username` | FRITZ!Box user; leave empty for password-only boxes              |
| `boxes[].password` | Password of that user                                           |
| `blacklist_file` | Optional, default `blacklist.txt` (relative to `boxes.json`)       |
| `log_level`      | Optional, `DEBUG`/`INFO`/`WARNING`/`ERROR`, default `INFO`         |

`boxes.json` contains passwords and is gitignored. Use a different config file with
`--config PATH` or the env var `EASY_FRITZ_CONFIG`.

## blacklist.txt

One entry per line, exactly as you would type it in the web UI (`web.de` or
`https://www.heise.de/`). Blank lines and lines starting with `#` are ignored. Entries
must not contain spaces. The FRITZ!Box accepts at most 500 entries.

## Usage

```bat
start.bat show               :: list each box's current blacklist
start.bat diff               :: show what sync would change, writes nothing
start.bat sync               :: overwrite each box's blacklist with blacklist.txt
start.bat --box main sync    :: only one box
```

`sync` reads the list back after saving and reports an error if the box stored something
else. One unreachable box does not stop the others. Exit codes: `0` all boxes fine,
`1` at least one box failed, `2` invalid `boxes.json` or `blacklist.txt`.

## How it works

AVM offers no API for the blacklist (TR-064 does not expose it), so the tool uses the same
requests as the web UI: login via the documented `login_sid.lua?version=2` (PBKDF2), then
`data.lua` with `page=kids_blacklist` to read and `urllist=<CRLF-joined list>&apply=true`
to save. A FRITZ!OS update may change these requests; the request names live in
`src/easy_fritz_control/constants.py`.

## Development

```bat
tools\run_tests.bat              :: unit tests
tools\run_integration_tests.bat  :: CLI against fake FRITZ!Boxes over real HTTP
update.bat                       :: upgrade dependencies, lint, type-check, test
```

Dependencies: `requests`, `pydantic`; dev: `pytest`, `ruff`, `mypy`, `types-requests`.
