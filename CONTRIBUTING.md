# Contributing to MLLANG

Thanks for considering a contribution.

---

## Quick guidelines

- Bugs / parser issues → open an issue with the failing packet text + expected behavior
- Doc improvements → PR welcome, small ones merge fast
- Spec changes (new slot, operator, halt value) → require an RFC (see below)

---

## RFC process

MLLANG v0.1 is locked. New spec features go through quarterly RFC review windows.

### Quarterly windows

- Q1: Jan 1 — Mar 31
- Q2: Apr 1 — Jun 30
- Q3: Jul 1 — Sep 30
- Q4: Oct 1 — Dec 31

### How to propose

1. Read the [spec](spec/MLLANG_v0.1.locked.md) fully
2. Open an issue using the `RFC Proposal` template
3. Follow [`spec/RFC_TEMPLATE.md`](spec/RFC_TEMPLATE.md)
4. 30 days community discussion
5. Multi-vendor test required: 3+ LLM families with packet emission + parse round-trip
6. Family-balanced jury vote (see `spec/VOTING_RULES.md`)
7. If accepted: PR merges into `spec/MLLANG_v0.x.draft.md`
8. End of quarter: draft locks → release v0.(x+1)

### Acceptance threshold

- 7 of 10 jury votes + ≥10 community 👍 = ACCEPT into next minor version
- Backward-incompatible changes = major version bump, ≥9 jury votes required

---

## Code contributions

### Parser changes

- Must pass full conformance suite
- New features need new conformance tests
- Pure stdlib only — no external deps

```bash
pip install -e parser/
python conformance/run_conformance.py
```

### Style

- Black-formatted Python (when CI adds it)
- Type hints on public API
- Docstrings on public functions

---

## Multi-vendor ratification

If you propose a spec change, you must demonstrate it works across at least 3 LLM families. Suggested test:

1. Paste [`bootstrap/session_init.md`](bootstrap/session_init.md) into 3 different LLM chats
2. Have each emit a packet using your proposed feature
3. Verify all 3 parse cleanly via reference parser
4. Attach results to your RFC

Families counted: Anthropic (Claude), OpenAI (GPT/Codex), Google (Gemini), open-weight (Llama, Gemma, Qwen, DeepSeek, Mistral, etc.)

---

## Code of Conduct

Respectful, honest, focused on the work. Bad-faith arguments, gatekeeping, or hostile critique = banned.

If a discussion gets heated, walk away for 24 hours. Real consensus takes time.

---

## License

By contributing, you agree your work is licensed under Apache 2.0 (see [LICENSE](LICENSE)).
