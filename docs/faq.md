---
layout: default
title: FAQ
---

# FAQ

## Why not just JSON?

JSON-RPC envelopes for the same state are 50–70% larger than MLLANG packets. At scale (multi-agent loops, RAG state, frequent handoffs), this matters for token cost + latency.

JSON example for same content:
```json
{"version": "0.1.r1", "thread_id": "demo", "goal": {"task": "classify"}, ...}
```
~140 chars.

MLLANG equivalent:
```
V:0.1.r1; I:demo; G:{task=classify}; ...
```
~50 chars.

## Why not YAML?

YAML is 2D / multi-line. MLLANG is single-line. Fits cleaner inside markdown fenced blocks. Also: YAML has implicit type coercion footguns (`yes` → bool, `1.0` → float, etc.) that MLLANG sidesteps.

## How is this different from MCP / A2A / ACP?

| Standard | Layer |
|----------|-------|
| MCP | Agent ↔ Tool (vertical) |
| A2A / ACP | Agent ↔ Agent transport (horizontal) |
| MLLANG | **Runtime state payload INSIDE** above transports |

MLLANG sits inside MCP tool payloads or A2A message bodies as the structured state content. Doesn't compete — composes with.

## Is this a new standard war?

No. MLLANG is a convention, not infrastructure. It rides on:
- Markdown (universal)
- MCP / A2A (existing transports)
- AGENTS.md / llms.txt (existing agent context formats)

Pitch is: "tiny syntax convention for state in markdown blocks", not "new protocol stack".

## Will it be a standard like JSON or HTTP?

Unlikely at that scale. Realistic outcome = niche convention, AsciiDoc-tier adoption — loved by people running multi-agent workflows in production, ignored by everyone else.

## Why locked to v0.1 for 4 weeks?

Spec stability matters more than features. v0.1 ratified across 6+ LLM families with mean confidence 0.95. Changing it before real-world drift evidence accumulates = bad. v0.2 RFC window opens after locked period.

## What's the "EN: shadow line"?

Every MLLANG packet should be followed by one English sentence summarizing intent:

```
V:0.1.r1; ...; H:<=>; P:0.85;
EN: Refactor auth sessions→JWT, preserve DB.
```

Reasons:
1. Humans can scan packets quickly
2. Other AI can sanity-check without parsing every slot
3. Audit trail readable without tooling

Optional during refinement phase (early weeks). Recommended always in production.

## Can I extend MLLANG for my domain?

Yes. Domain-specific extensions live in `lib_<domain>.mllang` packs. Core spec stays small. Examples:

- `lib_codereview.mllang` — PR review detector ids, review verbs
- `lib_medical.mllang` — clinical note slots, HIPAA-aware redaction patterns
- `lib_legal.mllang` — contract clause types, jurisdiction tags

Your `lib_*.mllang` stays in your repo (or private). Core spec doesn't change for domain features.

## Why 9-way halt enum?

| Halt | Use |
|------|-----|
| `accept` | output good, move on |
| `repair` | local fix only |
| `regen` | full regenerate |
| `escalate@H` | hand to human |
| `after-N-rounds` | round cap reached |
| `test=pass` | deterministic check green |
| `test=fail` | deterministic check red |
| `risk!high` | abort + escalate |
| `<=>` | all agents agreed (terminal lock) |

Covers retry policy, escalation, agreement, and deterministic gates in 9 values. Multi-value via `|` for compound conditions.

## Telemetry?

Library has zero default telemetry. Future opt-in corpus (Phase F) requires explicit `MLLANG_TELEMETRY=on`. All values sanitized client-side before leaving your machine.

## Where do I report bugs?

[github.com/jakeliu/mllang/issues](https://github.com/jakeliu/mllang/issues)

## Where do I propose spec changes?

See [CONTRIBUTING.md](https://github.com/jakeliu/mllang/blob/main/CONTRIBUTING.md). Quarterly RFC windows.
