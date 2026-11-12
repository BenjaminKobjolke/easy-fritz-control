"""Exercise batch control flow with external work replaced by bounded exit stubs."""

import os
import subprocess
import tomllib
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
pytestmark = pytest.mark.skipif(os.name != "nt", reason="Windows batch control flow")


def _run_batch(script: Path, lines: list[str]) -> subprocess.CompletedProcess[str]:
    script.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return subprocess.run(
        ["cmd", "/d", "/c", str(script)],
        cwd=script.parent,
        capture_output=True,
        text=True,
        timeout=5,
        check=False,
    )


@pytest.mark.parametrize("failed_stage", [0, 1, 2, 3, None])
@pytest.mark.parametrize("watcher_run", ["0", "1"])
def test_graphify_returns_first_failure(
    tmp_path: Path, failed_stage: int | None, watcher_run: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    tools = tmp_path / "tools"
    tools.mkdir()
    graph = tmp_path / "graphify-out"
    graph.mkdir()
    (graph / "graph.json").write_text("{}", encoding="utf-8")
    (graph / ".graphify_python").write_text("unused-python.exe", encoding="utf-8")
    source = (ROOT / "tools/graphify_update.bat").read_text(encoding="utf-8")
    lines = []
    stage = 0
    for line in source.splitlines():
        stripped = line.strip()
        if stripped.startswith('"%GRAPHIFY%"') or stripped.startswith('"!GPY2!"'):
            code = 17 if stage == failed_stage else 0
            line = f'echo STAGE-{stage}\ncmd /d /c exit {code}'
            stage += 1
        elif stripped.startswith("where graphify"):
            line = "cmd /d /c exit 0"
        lines.append(line)
    assert stage == 4
    script = tools / ".tw-run-example.bat"
    monkeypatch.setenv("TICKETS_WATCHER_COMMAND_RUN", watcher_run)
    result = _run_batch(script, lines)
    assert result.returncode == (0 if failed_stage is None else 17), result.stdout
    if failed_stage is not None and failed_stage < 3:
        assert f"STAGE-{failed_stage + 1}" not in result.stdout


@pytest.mark.parametrize("name", ["run_tests.bat", "run_integration_tests.bat"])
@pytest.mark.parametrize("exit_code", [0, 5])
def test_test_runners_preserve_exit_codes(tmp_path: Path, name: str, exit_code: int) -> None:
    source = (ROOT / "tools" / name).read_text(encoding="utf-8")
    lines = []
    for line in source.splitlines():
        if line.startswith("where uv"):
            line = "cmd /d /c exit 0"
        elif line.startswith("uv run pytest"):
            line = f"cmd /d /c exit {exit_code}"
        lines.append(line)
    script = tmp_path / ".tw-run-example.bat"
    result = _run_batch(script, lines)
    assert result.returncode == exit_code, result.stdout


def test_pytest_has_enforced_per_test_timeout(pytestconfig: pytest.Config) -> None:
    config = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    options = config["tool"]["pytest"]["ini_options"]
    assert 0 < options.get("timeout", 0) < 540
    assert any(item.startswith("pytest-timeout") for item in config["dependency-groups"]["dev"])
    assert pytestconfig.pluginmanager.hasplugin("timeout")


@pytest.mark.parametrize(
    ("name", "failed_stage"),
    [
        ("install.bat", 1),
        ("install.bat", None),
        ("update.bat", 2),
        ("update.bat", 3),
        ("update.bat", 4),
        ("update.bat", None),
    ],
)
def test_declared_setup_commands_report_failed_checks(
    tmp_path: Path, name: str, failed_stage: int | None
) -> None:
    lines = []
    stage = 0
    for line in (ROOT / name).read_text(encoding="utf-8").splitlines():
        if line.startswith("where uv"):
            line = "cmd /d /c exit 0"
        elif line.startswith("uv "):
            code = 17 if stage == failed_stage else 0
            line = f"cmd /d /c exit {code}"
            stage += 1
        lines.append(line)
    script = tmp_path / ".tw-run-example.bat"
    result = _run_batch(script, lines)
    assert result.returncode == (0 if failed_stage is None else 17), result.stdout
