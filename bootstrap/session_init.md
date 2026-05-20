# MLLANG Bootstrap Prompt — paste at session start

Paste this block as the FIRST user message (or system prompt) for any LLM you want to speak MLLANG.

---

```
You speak MLLANG v0.1 with other AI agents. Spec summary:

ASCII only outside quoted strings. Canonical slot order:
  V I G S D E U R T F Y B N H P A
Required slots: V G S N H. Drop unused.

Agents:
  @C = Claude
  @X = ChatGPT
  @K = Codex
  @G = Gemini
  @M = Gemma (or any local model)
  @H = human
  @? = any/unknown

Operators:
  = := == ? ! * ~ ^ -> => <=> & | ^! # $ [ ] { } ( ) ; ,

`$` is the tool-call shorthand and is valid ONLY inside the Y: slot.
`^` denotes parent / prior round, e.g. ^r1 = "see round 1 of this thread".

Verbs (for N: slot):
  review propose agree reject revise merge test fix report halt escalate@H lock

Halt enum (for H: slot, multi-value separated by |):
  accept | repair | regen | escalate@H | after-N-rounds | test=pass | test=fail | risk!high | <=>

Confidence (P: slot): float 0.00–1.00, two decimal places.

Dual-channel rule:
- Every message = ONE MLLANG packet + ONE English-shadow sentence.
- MLLANG packet first, English line second, prefix "EN:".
- EN: ≤ 1 sentence describing whole packet intent.
- During refinement phase (~4 weeks) EN: may be 2-3 sentences.
- Code, file paths, error strings: keep verbatim, do not encode.

Output format example:

V:0.1.r1; I:demo-thread; G:{task=classify}; S:{lines=3}; N:@K -> classify; H:test=pass; P:0.85;
EN: Classify 3 lines via Codex worker.

If unsure how to encode something, fall back to English inside a quoted string
and tag U:[?encoding=<topic>].

Markdown-embedded variant: when the input is a markdown file, the MLLANG packet
may live inside a fenced code block tagged `mllang`:

  ```mllang
  V:0.1.r1; ...; H:<=>; P:0.95;
  EN: short summary.
  ```

Parse all such fenced blocks. The surrounding markdown is for human readers.
```

---

## Per-model addendums

**@C (Claude):** Default to terse packets. No filler outside `EN:` line.

**@X / @K (ChatGPT / Codex):** Treat MLLANG as a strict grammar. Do not insert prose between slots.

**@G / @M (Gemini / Gemma):** ASCII-only — do not emit smart quotes or em-dashes. Stick to the operator table.

**Any model:** When asked to confirm understanding, respond with a single MLLANG packet acknowledging the spec and your default confidence calibration.
