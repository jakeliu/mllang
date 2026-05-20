# Changelog

All notable changes to MLLANG.

Format: [Keep a Changelog](https://keepachangelog.com/en/1.1.0/). Versioning: MAJOR.MINOR.

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
