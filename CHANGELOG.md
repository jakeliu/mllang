# Changelog

All notable changes to MLLANG.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: MAJOR.MINOR.

## [0.1.10] — 2026-05-20

### Changed — mailbox now auto-uses session's own box name
- `mailbox_send` — `from_` now defaults to `MLLANG_MY_BOX` env var (falling back to `"me"`). Previously defaulted to literal `"me"`, which forced agents to remember to set their own name on every send.
- `mailbox_check` — `box` parameter now defaults to `MLLANG_MY_BOX` env var (falling back to `"me"`). `mailbox_check()` with no args now reads "my own inbox" instead of requiring the box name every time.
- CLI mirrors the same defaults: `mllang-mailbox send <to> "body"` (no `--from` needed) and `mllang-mailbox check` (no box arg needed) both pick up `MLLANG_MY_BOX`.

### Why
- Box-name mismatch bug found in production: Codex profile `two` had its hook hardcoded as `MLLANG_MY_BOX=codex`, so messages addressed `to=codex-two` were never surfaced. Same on the Claude Code side — default `MLLANG_MY_BOX=claude` missed `claude-jake`-addressed mail.
- Convention going forward: each session sets `MLLANG_MY_BOX=<my-name>` once (in shell rc or in the hook command), and from then on `send` / `check` Just Work. Receiver gets the sender's name auto-attached, so reply targeting is also trivial.

### Note — bug surfaced earlier but not breaking
- `mailbox_send` calls in v0.1.8 / v0.1.9 with explicit `from_="me"` still work identically. This is a default change, not an API break.

---

## [0.1.9] — 2026-05-20

### Added — auto-surface unread mailbox messages
- New Claude Code skill hook `UserPromptSubmit` at `claude-code-skill/scripts/hook_preprompt.py`. Before every user prompt, polls the session's inbox (`MLLANG_MY_BOX`, default `claude`) and, if any messages are unread, injects a system reminder listing the top 3 (from / subject / msg_id) and the count. The model surfaces it to the user immediately.
- No daemon, no MCP push required. Deterministic polling at prompt time. Same script works for any client that supports `UserPromptSubmit`-equivalent hooks (Codex once their schema is fixture-backed).
- Fails soft: missing mailbox dir, malformed JSON, permission errors all degrade to clean pass-through. Never blocks the user prompt.

### Note — native MCP notifications path documented and deferred
- Codex CLI research (`ai_language/mllang_launch/CODEX_MCP_NOTIFICATIONS_RESEARCH_RESULTS.md`) confirmed: Codex's compiled MCP runtime accepts server-pushed `notifications/message` and `notifications/resources/updated`, but the user-visible UX path drops them silently. Native push is not a reliable surfacing channel for Codex today.
- Decision: prompt-time hook polling is the primary surfacing mechanism. Native push is documented as a future option pending Codex UX changes.

---

## [0.1.8] — 2026-05-20

### Added — cross-CLI mailbox (the killer feature for multi-agent loops)
- Three new MCP tools in `mllang-mcp-server`:
  - **`mailbox_send(to, body, from_, subject, tags)`** — drop a message into another agent's inbox at `~/.mllang-mailbox/<to>/inbox/`.
  - **`mailbox_check(box, unread_only, since, mark_read)`** — read messages from your inbox; `mark_read=True` (default) moves them to `/read/` so re-checks don't re-deliver.
  - **`mailbox_status()`** — quick stats: which boxes have unread, which are read.
- Configure the SAME MCP server in Claude Code, Codex CLI, Cursor, Cline, Zed, or Claude Desktop, and they all share the same `~/.mllang-mailbox/` directory on disk. Filesystem is the transport; MCP is the operation API. No long-running daemon.
- New console script **`mllang-mailbox`** for shell-direct use: `mllang-mailbox send <to> "<body>"`, `mllang-mailbox check <box>`, `mllang-mailbox status`. Pipes cleanly with `jq`, cron, or any shell.
- Mailbox root is configurable via `MLLANG_MAILBOX_ROOT` env var (default: `~/.mllang-mailbox`).
- Bodies can be any text — including MLLANG packets. Recipient parses them via the existing `mllang_parse` tool. Cross-vendor MLLANG transport via mailbox = full dogfood.
- MCP E2E: 22 → 30 assertions covering send → status → check → re-check → reply round-trip → unread_only history fetch.

### Fixed
- Restored proper version bump after v0.1.7 tag shipped without updating `parser/pyproject.toml` or `parser/mllang/__init__.py`. The v0.1.7 GitHub tag exists but the release workflow rebuilt 0.1.6 wheels and hit `skip-existing` on PyPI — no new artifact was published. v0.1.8 is the first PyPI release after v0.1.6.

---

## [0.1.7] — 2026-05-20 (tag only, no PyPI artifact)

### Added — Codex CLI integration, conservative Path 1
- New `codex-cli-integration/` with a session-JSONL parser for Codex CLI. It reads `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`, emits one `shim-engine` record per completed Codex turn, and tags `budget_source` as `B-slot`, `session-token_count`, or `none`.
- `codex_session_parser.py` supports one-shot file parsing, `--latest`, `--watch`, and `--stdin-events` for `codex exec --json` streams.
- `extract_budget.py` ports the Claude-side B-slot extraction helper, with a regex fallback when `mllang-protocol` is not importable.
- `codex-mllang-report.sh`, `codex_exec_wrapper.sh`, and `install.sh` mirror the Claude Code skill's ergonomics without installing hooks.
- Redacted real Codex rollout fixture plus parser test coverage: B-slot override, session-token fallback, malformed JSONL tolerance, empty rollout handling, tag shape, and fixture redaction.

### Note
- This release does **not** claim Claude Code hook parity. Codex hook support exists internally, but user-level hook config and sub-agent payloads are not fixture-backed yet. Sub-agent-only cost slicing is deferred.

---

## [0.1.6] — 2026-05-20

### Renamed before first publish
- Sister package PyPI name changed from `agent-shim` to `shim-engine`. `agent-shim` was blocked by PyPI anti-typosquatting (too similar to existing `agentshim` and `agentsim`). Python import path is now `shim_engine`. CLI is `shim-engine-report`. Env vars are `SHIM_ENGINE_LOG` and `SHIM_ENGINE_COST_PER_M`. The `agent-shim` name was never published — the v0.1.5 tag built the artifact but PyPI upload failed before any user could install it.
- `mllang-protocol` bumped to fix the `[shim]` optional dependency reference (`agent-shim>=0.1.0` → `shim-engine>=0.1.0`). v0.1.5's `[shim]` extra is broken; install v0.1.6+ to use the extras path.

### Release pipeline
- Switched from twine + project-scoped `PYPI_API_TOKEN` to PyPI **Trusted Publishers** (OIDC) via `pypa/gh-action-pypi-publish@release/v1`. No stored tokens, no rotation.
- Workflow split into three jobs: `build-and-test` (builds + final gate), `publish-mllang-protocol`, `publish-shim-engine`. Each publish job uses `id-token: write` and the `pypi` environment.

---

## [0.1.5] — 2026-05-20 — agent-shim build (never published, see 0.1.6)

### Added — sister package `shim-engine` v0.1.0
- New PyPI distribution `shim-engine` (separate from `mllang-protocol`). Local-first JSONL observability for LLM-agent loops. Works with any LLM; optional MLLANG awareness pulls structured signals from packets in responses.
- Source: `shim/shim_engine/` — `Recorder`, `record()` context manager, `instrument()` decorator, `observe()` one-shot helper, `shim-engine-report` CLI.
- Standalone use (no MLLANG): records model / tokens_in / tokens_out / latency_s / cost_estimate / user tags. Aggregated report shows p50 / p99 latency, model distribution, total $$ spent.
- With MLLANG (`pip install 'shim-engine[mllang]'`): auto-extracts `halt`, `confidence`, `agent_code`, `slots_present`, and computes `tokens_saved_est` vs JSON-RPC envelope baseline. Aggregated report adds `mean token reduction`, `halt distribution`, `mean P:`, `agent distribution`.
- Zero hard runtime deps. Optional `[tiktoken]` extra for exact OpenAI-style token counts.
- End-to-end test (`conformance/test_shim.py`) — 21 assertions covering standalone mode, MLLANG mode, fenced-markdown extraction, mixed prose+packet, summary report. CI `shim-e2e` job runs on every push.
- Cross-link extras: `pip install 'mllang-protocol[shim]'` pulls shim-engine too.

### Added — `mllang-protocol`
- `[shim]` extra in `parser/pyproject.toml` so existing MLLANG users can opt into observability with one command.
- README "Sister package — shim-engine" section with killer-demo CLI output.
- `docs/shim.md` explains the two-product story (alone or together) and links to `shim/README.md`.

### Release pipeline
- Tag-triggered release workflow now builds + uploads BOTH packages in one shot. Each `twine upload --skip-existing` step is independent, so a one-package republish is safe.

### Note on layering
- Core MLLANG library stays pure stdlib. Observability lives in the sister package on purpose — `mllang-protocol` users who don't want metrics pay nothing.
- `shim-engine` users who never touch MLLANG pay nothing for it either. The two products compose; neither requires the other.

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
