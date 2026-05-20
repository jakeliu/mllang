# GEMINI.md — Gemini CLI instructions for the MLLANG repo

Gemini CLI (`gemini-cli`) auto-loads this file when running inside the repository.

## Identity

This is the MLLANG public repo. PyPI: `mllang-protocol`. Python import: `mllang`.

## Bootstrap MLLANG before passing agent state

Before emitting or parsing any MLLANG packet in this repo, load:
[`bootstrap/full_session_init.md`](bootstrap/full_session_init.md)

Then acknowledge with the confirmation packet template (bottom of that file).

## Gemini-family specific notes

- **ASCII outside quoted strings** — Gemini sometimes emits smart quotes / em-dashes by habit. MLLANG requires ASCII for operators and slot keys. Non-ASCII allowed only inside `"..."` quoted values.
- **Honest confidence on `P:` slot** — Gemini family tends to rubber-stamp at `P:>=0.98`. MLLANG style guide (`bootstrap/full_session_init.md`, "Rules for your output") asks for `P:0.70-0.95` and never `1.00`. Calibrate down accordingly.
- **No hidden chain-of-thought in packets** — slots carry state, decisions, evidence, next action, and confidence only.

## Commands

```bash
python3 conformance/run_conformance.py       # 166 tests, must stay green
python3 conformance/test_mcp_server.py       # MCP E2E (requires [mcp] extra)
pip install -e parser/                       # dev install
pip install -e 'parser/[mcp]'                # with MCP server
```

## Hard rules

- Spec is locked. No edits to `spec/MLLANG_v0.1.locked.md` outside RFC process.
- Parser stays pure stdlib.
- Conformance + MCP E2E must stay green on every change.
- Sanitize before telemetry; never auto-enable.

## Out of scope

Same as `AGENTS.md`: do not touch Token Bot internals, Helen book pipeline, or Chrome companion extension references.
