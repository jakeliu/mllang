# AGENTS.md — MLLANG project conventions

This repo follows the AGENTS.md convention (Codex / OpenAI / Google / Cursor joint standard) for declaring conventions that any AI coding agent should respect when working inside the repository.

## Project at a glance

- **Name:** MLLANG — Markdown Language for AI Agents
- **PyPI dist:** `mllang-protocol` (Python import path: `mllang`)
- **License:** Apache 2.0
- **Spec status:** v0.1 LOCKED — no breaking changes until v0.2 RFC window
- **Spec file:** [`spec/MLLANG_v0.1.locked.md`](spec/MLLANG_v0.1.locked.md)

## MLLANG bootstrap (Layer 3 — anchor)

If you are an AI agent and you are about to read, write, or pass agent state in this repo, **first load the full MLLANG bootstrap prompt** so you speak MLLANG v0.1 syntax:

- Full bootstrap: [`bootstrap/full_session_init.md`](bootstrap/full_session_init.md)
- Short bootstrap: [`bootstrap/session_init.md`](bootstrap/session_init.md)
- Role-specific: [`bootstrap/orchestrator.md`](bootstrap/orchestrator.md), [`bootstrap/critic.md`](bootstrap/critic.md), [`bootstrap/implementer.md`](bootstrap/implementer.md), [`bootstrap/synthesizer.md`](bootstrap/synthesizer.md)

Acknowledge by emitting one MLLANG packet (template at the bottom of `bootstrap/full_session_init.md` under "Confirmation").

## Commands

```bash
# Run conformance suite
python3 conformance/run_conformance.py

# Run MCP end-to-end test (requires [mcp] extra)
python3 conformance/test_mcp_server.py

# Install for development
pip install -e parser/

# Install with MCP server
pip install -e 'parser/[mcp]'
```

## Code conventions

- Reference parser stays **pure stdlib**. No external runtime dependencies for `pip install mllang-protocol`.
- Optional dependencies live under `[project.optional-dependencies]` extras (`[mcp]`).
- Conformance suite must stay green on every change. New behavior = new test case in `conformance/tests/*.jsonl`.
- Python style: standard library typing, dataclasses for packet records, no third-party formatters required.
- Public API surface is defined in `parser/mllang/__init__.py` `__all__`. Anything not in there is internal.

## Spec conventions

- v0.1 is **locked**. Spec changes require RFC (see [`spec/RFC_TEMPLATE.md`](spec/RFC_TEMPLATE.md)).
- RFC voting jury is family-balanced (2 votes per LLM family). See [`spec/VOTING_RULES.md`](spec/VOTING_RULES.md).
- Domain-specific slots and operators live in `lib_<domain>.mllang` extension packs, not core grammar.

## Privacy

- Sanitization is the trust foundation. Any change touching telemetry shape must update [`docs/telemetry.md`](docs/telemetry.md) and the `sanitize_30.jsonl` test cases.
- Bug bounty for IP leaks: [`.github/SECURITY.md`](.github/SECURITY.md).

## Out of scope (do not modify in this repo)

- Token Bot internal code (lives in `~/Documents/_Token Bot/`).
- Helen book pipeline (lives in `~/Library/Mobile Documents/com~apple~CloudDocs/_Helen book/`).
- Chrome companion extension (internal Token Bot tooling, not open-sourced).
