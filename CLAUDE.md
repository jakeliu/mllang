# CLAUDE.md — Claude Code instructions for the MLLANG repo

This file is the Claude-Code-specific anchor. It is auto-loaded by Claude Code when working in this repository. Conventions overlap with [`AGENTS.md`](AGENTS.md); when both apply, this file wins for Claude Code only.

## Identity

You are working in the **MLLANG public repo** (github.com/jakeliu/mllang). PyPI distribution name is `mllang-protocol`; Python import path is `mllang`.

## Before touching agent state in this repo

Load the bootstrap so you emit MLLANG v0.1 packets correctly:
[`bootstrap/full_session_init.md`](bootstrap/full_session_init.md)

After loading, acknowledge with the confirmation packet template at the bottom of that file. Verify your output parses with `python3 -c "from mllang import parse, validate; print(validate(parse(open('your_packet.txt').read())))"` (should return `[]`).

## Hard rules

- **Spec is locked.** Do not edit `spec/MLLANG_v0.1.locked.md`. Spec changes only via RFC in `rfc/` after the v0.2 RFC window opens.
- **Parser stays stdlib.** No new runtime deps in `parser/pyproject.toml` `dependencies` (extras under `[project.optional-dependencies]` are fine).
- **Conformance must stay green.** Every behavior change adds a test case to the matching `conformance/tests/*.jsonl`.
- **Markdown-embedded output uses the summary+packet pattern.** Title + one-line workflow summary + fenced ```mllang block. Long prose only for human-authored docs (PR descriptions, design notes). See [`docs/markdown-embedded.md`](docs/markdown-embedded.md).
- **Sanitize before telemetry.** Library never auto-enables telemetry. Any code touching telemetry shape must update `docs/telemetry.md` and `conformance/tests/sanitize_30.jsonl`.

## Commands you may run

```bash
# Local verification before commit
python3 conformance/run_conformance.py

# MCP end-to-end (requires [mcp] extra)
python3 conformance/test_mcp_server.py

# Local install for testing
pip install -e parser/
pip install -e 'parser/[mcp]'

# Build sdist + wheel
python3 -m build parser/
```

## Release flow

- Bump version in `parser/pyproject.toml` AND `parser/mllang/__init__.py`.
- Add CHANGELOG entry.
- Tag `vX.Y.Z`, push tag → release workflow uploads to PyPI automatically (PYPI_API_TOKEN secret required).
- Create GitHub release page via `gh release create vX.Y.Z`.

## Out of scope

- **Do not touch** Token Bot internals (`~/Documents/_Token Bot/`).
- **Do not touch** Helen book pipeline (`~/Library/Mobile Documents/com~apple~CloudDocs/_Helen book/`).
- **Do not modify** Chrome companion extension references — that's internal tooling, not open-source.

## Private-content guard (CRITICAL)

This repo is **public on github.com/jakeliu/mllang**. Token Bot mesh and orchestration internals are private. Never commit, suggest committing, or `git add` files matching these patterns:

- `examples/ml_*_harness.py` — ML method harness shims (private demonstrator mesh)
- `examples/ml_harness_base.py`, `harness_test_runner.py`, `spec_gate.py`, `hardware_harness.py`, `software_harness.py`, `_fix_error_codes.py`
- `examples/mllang_orchestrator.py`, `examples/mllang_sig.py`, `examples/ai_to_ai_demo.py`, `examples/sig_e2e_test.py`, `examples/*_round_trip.py`
- `docs/harness_test_brief.md`
- `PROGRESS.md`, `BLOCKED.md`, `temp_context-*.md`

Never include these strings in committed content: `Token Bot`, `_Token Bot`, `KASA_USER`, `KASA_PASS`, `kasa.txt`, `jliu@askuncleai.com`, `192.168.4.`, `127.0.0.1:1234`, `mllang-shim`.

A `.githooks/pre-commit` guard enforces this. Enable on fresh clone with:
```
git config core.hooksPath .githooks
```
If you hit the block, the right answer is **never** `git commit --no-verify`. Either:
1. The file/content should not be in this repo (move to `~/Documents/_Token Bot/`)
2. The pattern is a false positive (tell the user; do not edit the hook unilaterally)

Before suggesting `git add <files>` always check the file is not on the private list above, and the diff does not contain a forbidden string. Read `.gitignore` first; if a file is gitignored, do not bypass with `git add -f`.

## Style

- Default to writing no comments. Only add when the WHY is non-obvious.
- Identifier names carry the WHAT; comments carry the WHY.
- Match existing terse caveman tone in commit messages.
