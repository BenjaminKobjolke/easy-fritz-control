# Version
3

# Coding Rules (Pointer)

This project's rules live in two files in the project root:

- `CODING_RULES.md` — code quality and conventions. BINDING for all code work in
  this repository, always.
- `IMPLEMENTATION_FLOW.md` — the end-to-end flow to follow when planning and
  implementing a change (checks, gates, Definition of Done).

MANDATORY: Before writing or editing ANY code, you MUST Read BOTH files in full
**in the current session**. Do not rely on memory of a previous session, a
summary, or partial reads.

If you are about to make a code change and have not read both files in this
session: STOP, read them, then continue.

An external tool may orchestrate the implementation itself. When a skill or run
states that the implementation is orchestrated, ignore `IMPLEMENTATION_FLOW.md`
entirely — the orchestrator runs those steps as its own phases. `CODING_RULES.md`
stays binding either way.

Next to `CODING_RULES.md`, apply also writes `CODING_RULES_PLAN.md`,
`CODING_RULES_REVIEW.md` and `CODING_RULES_CODE.md`. When an orchestrator's run
instructions name one of these step files, that file replaces `CODING_RULES.md`
for that run; without such an instruction, `CODING_RULES.md` stays binding in full.

Do not inline rules back into this file and do not use `@import` for either file —
they are intentionally referenced, not imported.

## graphify

This project's graphify code directory is src/.

## Code Analysis

Copy `tools/analyze_code_config.example.bat` to `tools/analyze_code_config.bat`
and set `CLI_ANALYZER_PATH` to your local CLI Code Analyzer checkout. Run `uv sync`
to install the project's locked Ruff version. The analyzer needs its own
`venv\Scripts\python.exe` installed in that checkout.

Run `tools\analyze_changed_and_new_files.bat` after a feature or bug fix. It uses
`--only-changed` to check new and modified files against Git HEAD, including
untracked files. Tickets Watcher can set `CLI_ANALYZER_CHANGED_SINCE` to include
committed changes since a specified commit. Run `tools\analyze_code.bat` for an
explicit whole-project audit or when no source files differ from HEAD.

Both commands return non-zero for any findings (including warnings and errors) or analyzer failures and
write per-rule CSV reports to `code_analysis_results/`. A missing CSV means that
rule found nothing; there is no Markdown report. Fix reported findings before
committing. `tools\fix_ruff_issues_dry_run.bat` previews Ruff fixes;
`tools\fix_ruff_issues.bat` applies them.

PMD duplicate detection is disabled because PMD is not configured on this
machine. Configure `pmd_path` in the analyzer's `settings.ini` and enable
`pmd_duplicates` in `code_analysis_rules.json` to use it. Structural similarity
detection stays disabled by default.
