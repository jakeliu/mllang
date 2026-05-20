# Changelog

All notable changes to MLLANG.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: MAJOR.MINOR.

## [0.1.5] — 2026-05-20

### Added — sister package `agent-shim` v0.1.0
- New PyPI distribution `agent-shim` (separate from `mllang-protocol`). Local-first JSONL observability for LLM-agent loops. Works with any LLM; optional MLLANG awareness pulls structured signals from packets in responses.
- Source: `shim/agent_shim/` — `Recorder`, `record()` context manager, `instrument()` decorator, `observe()` one-shot helper, `agent-shim-report` CLI.
- Standalone use (no MLLANG): records model / tokens_in / tokens_out / latency_s / cost_estimate / user tags. Aggregated report shows p50 / p99 latency, model distribution, total $$ spent.
- With MLLANG (`pip install 'agent-shim[mllang]'`): auto-extracts `halt`, `confidence`, `agent_code`, `slots_present`, and computes `tokens_saved_est` vs JSON-RPC envelope baseline. Aggregated report adds `mean token reduction`, `halt distribution`, `mean P:`, `agent distribution`.
- Zero hard runtime deps. Optional `[tiktoken]` extra for exact OpenAI-style token counts.
- End-to-end test (`conformance/test_shim.py`) — 21 assertions covering standalone mode, MLLANG mode, fenced-markdown extraction, mixed prose+packet, summary report. CI `shim-e2e` job runs on every push.
- Cross-link extras: `pip install 'mllang-protocol[shim]'` pulls agent-shim too.

### Added — `mllang-protocol`
- `[shim]` extra in `parser/pyproject.toml` so existing MLLANG users can opt into observability with one command.
- README "Sister package — agent-shim" section with killer-demo CLI output.
- `docs/shim.md` explains the two-product story (alone or together) and links to `shim/README.md`.

### Release pipeline
- Tag-triggered release workflow now builds + uploads BOTH packages in one shot. Each `twine upload --skip-existing` step is independent, so a one-package republish is safe.

### Note on layering
- Core MLLANG library stays pure stdlib. Observability lives in the sister package on purpose — `mllang-protocol` users who don't want metrics pay nothing.
- `agent-shim` users who never touch MLLANG pay nothing for it either. The two products compose; neither requires the other.

---

## [0.1.4] — 2026-05-20

### Fixed
- Parser correctly handles `EN:` shadow line emitted inline (same line as the packet, after the final `;`), not only on its own line. Affected any model that returns one-line packets — surfaced when ratifying DeepSeek V3 / Kimi K2.6 / Qwen 3.6, all of which emit single-line output by default. 3 new parse-suite test cases lock the fix.

### Added — Chinese-family ratification pass
- DeepSeek V3 — ratified (P:0.92, 1 round)
- Kimi K2.6 (Moonshot) — ratified (P:0.88, 1 round)
- Qwen 3.6 (Alibaba) — ratified (P:0.85, 1 round)
- Tested via krater.ai (multi-vendor chat router). All three converged in **1 round per backend** because the spec is locked — each needed only to acknowledge and emit a valid packet, not negotiate the grammar.
- Mean across all 9 ratified vendors: 0.93 confidence.
- Audit trail: `examples/ratification_chinese_2026-05-20.jsonl`.
- README ratification table updated. Badge bumped from `vendors-6+` to `vendors-9+`.

### Conformance
- Parse tests: 50 → 53 (3 inline-EN cases added).
- Total suite: 160 → 166 passed, 0 failed.

---

## [0.1.3] — 2026-05-20

### Added
- **MCP server** (`mllang.mcp_server`). Exposes the library as 7 Model Context Protocol tools (`mllang_parse`, `mllang_compose`, `mllang_validate`, `mllang_embed_in_markdown`, `mllang_extract_summary`, `mllang_sanitize`, `mllang_spec`). Pluggable into Claude Desktop, Cline, Zed, or any MCP-aware client.
- Optional dependency `[mcp]` extra: `pip install 'mllang-protocol[mcp]'`.
- Console script `mllang-mcp-server` (stdio transport).
- End-to-end test (`conformance/test_mcp_server.py`) — spawns the server as a subprocess and drives every tool over real MCP stdio. 22 assertions.
- CI `mcp-e2e` job runs the end-to-end test on every push.
- `docs/mcp.md` — install, Claude Desktop config snippet, tool table, end-to-end test instructions.
- README — new MCP server section.

### Note
- Core install (`pip install mllang-protocol`) stays pure stdlib. The `mcp` SDK only loads when the server is invoked.

---

## [0.1.2] — 2026-05-20

### Changed
- **PyPI distribution renamed `mllang` → `mllang-protocol`**. Existing PyPI name `mllang` is held by an unrelated 2021 ML library (`mlLang` by Stefan Feuerriegel, case-insensitive collision). Install command becomes `pip install mllang-protocol`. **Python import path is unchanged** — code keeps using `from mllang import ...`.

### Note
- v0.1.1 was tagged but never published to PyPI (403 from name collision). v0.1.2 is the first PyPI release.

---

## [0.1.1] — 2026-05-20

### Added
- `sanitize()` and `sanitize_to_json()` — library-side telemetry redaction with 4 levels (`off` / `shape` / `structured` / `full`) controlled by `MLLANG_TELEMETRY` env var. Slot SHAPES public, slot VALUES private. Thread ids hashed (sha256_12). File paths and tool-call args never logged.
- Defense-in-depth leak detector (email / file path / API-key / long-quote regex). Refuses payloads instead of redacting.
- `embed_in_markdown()` and `extract_summary_and_packet()` helpers with three modes:
  - `summary` (default) — title + 1-line workflow summary + fenced packet block. For agent-loaded files.
  - `verbose` — long prose + packet. For human-authored docs.
  - `packet_only` — block alone. For pipelines.
- `docs/telemetry.md` — slot-by-slot redaction rules, before/after examples, opt-in flow.
- `.github/SECURITY.md` — disclosure policy + IP-leak bug bounty.
- 34 sanitize conformance tests + 10 embed conformance tests (total suite now 160 packets, was 116).

### Changed
- `docs/markdown-embedded.md` — rewritten around `summary` mode (compact 1-line workflow summary + packet) as the primary pattern. `verbose` mode is opt-in for human-read docs. EN: line is the dual-channel.
- README — new 30-second example uses `embed_in_markdown()` + summary mode end to end. Status counts updated.
- `parser/pyproject.toml` — dropped `../README.md` and `../LICENSE` file references that broke editable install on CI. Inline SPDX `Apache-2.0` license string.

### Fixed
- CI green on Python 3.9 / 3.10 / 3.11 / 3.12 after pyproject.toml fix (prior v0.1.0 tag had failing CI).

---

## [0.1.0] — 2026-05-20

### Added
- Initial public release.
- v0.1 spec locked (16 slots, 19 operators, 9-way halt enum).
- Cross-vendor ratification across 6+ LLM families:
  - Claude (Anthropic): Sonnet 4.6, Opus 4.7
  - GPT (OpenAI): 5.5 Thinking, Codex
  - Gemini (Google): Pro web, Flash CLI
  - Gemma (Google local): 26B (AIR), 4B (small-model test PASS)
- Reference Python parser (pure stdlib, ~200 LOC core).
- 116-packet conformance test suite.
- Markdown-embedded usage pattern (`​```mllang ... ​``` ` fenced blocks).
- Bootstrap prompts for 4 roles: orchestrator, critic, implementer, synthesizer.
- 5 generic example packets (debug, code-review, classify, markdown-embedded, ratification trace).
- Telemetry sanitization script (for future opt-in corpus).
- RFC process documentation.
- Apache 2.0 license.

### Spec
- v0.1 LOCKED — no breaking changes until v0.2 RFC window.
- v0.2 deferred items documented in spec section 17.

---

## [Unreleased — v0.2 draft]

### Under RFC consideration
- `P:` banding `low|med|high` alongside float
- Compression-tier slot (`std|mini|ultra`)
- Macro references beyond `^rN` (e.g. `^@C` last-from-Claude)
- Optional 4-way `H:` simplification

(RFC window status: see `rfc/` directory.)
