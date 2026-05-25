# Inter-vendor MLLANG round-trip notes — 2026-05-24

## Codex (OpenAI gpt-5.5) ✓
- Composed RFC vote packet correctly on first try (clean `@CODEX -> rfc.vote` target).
- Composed follow-up `@ML_CLF -> clf.predict` packet correctly on first try.
- Round-trip via `examples/ai_to_ai_demo.py` executed end-to-end: parse → execute → preserve TR.
- Verdict: production-ready for v0.2.

## Gemini (Gemini 2.5 Pro) — FIXED via map-form N: slot
- Initial bug: `N:@ML_CLF -> verb` and even `N:"@ML_CLF -> verb"` both got rewritten by Gemini to file paths (`@.mllang-shim/ml_clf.pkl`, etc). Reproduced across 3 prompts.
- Root cause: Gemini's tokenizer treats unquoted `@<word>` as a tool-path reference and rewrites it; quoting at the slot level did NOT help (Gemini rewrote inside the quotes too).
- **Fix (RFC 0001 addendum):** v0.2 accepts `N:{agent:"@AGENT", verb:"verb_name"}` as an equivalent encoding. The `@` token now sits inside a quoted dict value, which Gemini preserves.
- Verified 2026-05-24: Gemini composed `N:{agent:" @ML_CLF", verb:"clf.predict"}` (added one space — `.strip()` in our parser handled it), and the harness executed end-to-end. `label:spam` returned, TR slot preserved.
- Backward compat: original `N:@AGENT -> verb` arrow form still parses. Both forms officially supported in v0.2.

## Claude Sonnet 4.6 / Opus 4.7 ✓ (self)
- Compose + parse both clean. Used as reference implementation.

## Open-weight (Gemma) ✓
- Tested on two local LM Studio endpoints, 2026-05-24:
  - Smaller open-weight model (`google/gemma-4-e4b`) on localhost — vote+follow-up round-trip 22.9s total
  - Larger open-weight model (`gemma-4-26b-a4b-it`) on a separate LAN host — vote+follow-up round-trip 7.2s total (3.2× faster)
- Both emit valid v0.2 packets first try using map-form `N:{agent:"@X", verb:"y"}`
- Both votes parse cleanly: approve, with structurally identical RFC commentary
- Both follow-up packets executed end-to-end through `@ML_CLF` harness (`label:spam`, TR preserved)
- Verdict: open-weight family supports MLLANG v0.2 without modification. Local-only inference is fully viable — zero cloud dependency for the protocol layer.

## Overall

2 of 4 vendor families fully round-trip without manual intervention (Anthropic, OpenAI). 1 of 4 partially (Google; vote intent extractable, N: target needs scrub). 1 pending (open-weight).
