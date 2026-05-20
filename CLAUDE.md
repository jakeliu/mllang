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

## Style

- Default to writing no comments. Only add when the WHY is non-obvious.
- Identifier names carry the WHAT; comments carry the WHY.
- Match existing terse caveman tone in commit messages.
