# Changelog

All notable changes to MLLANG.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: MAJOR.MINOR.

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
