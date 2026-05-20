# RFC: <Title>

**Author:** <name / github handle>
**Date:** YYYY-MM-DD
**Status:** Draft | Open | Accepted | Rejected | Withdrawn
**Target version:** v0.x

---

## Summary

One paragraph: what change, why now.

## Motivation

Real-world problem that requires this change. Cite usage data if available — telemetry corpus rows, log.jsonl evidence, multi-vendor test results.

## Detailed design

New slot / new operator / new halt category / new convention. Show diff vs current spec.

### Before
```
V:0.1.r1; ...current packet shape...
```

### After
```
V:0.x.r1; ...packet shape with proposed change...
```

## Examples

3 realistic packets using the new feature.

```
Example 1: ...
```

```
Example 2: ...
```

```
Example 3: ...
```

## Backward compatibility

What breaks? Migration path? Can v0.1 parsers ignore the new slot/operator safely, or does it require parser update?

## Multi-vendor test

Required: test new feature across at least 3 LLM families.

Suggested matrix:
- [ ] Anthropic family — Claude Sonnet/Opus
- [ ] OpenAI family — GPT-5.x or Codex
- [ ] Google family — Gemini Pro/Flash
- [ ] Open-weight family — Gemma / Llama / Qwen / DeepSeek / Mistral

For each: paste bootstrap + your proposed extension → emit a packet → parse via reference parser → roundtrip check.

Attach results inline below.

## Adoption / use case evidence

Who already does this informally?
Who would benefit?
Has anyone shipped this in a fork?

## Open questions

Things unresolved before merge. Tagged with `?` so they're easy to find.

- ?
- ?

## Risks

What could go wrong?

---

## Voting record (filled by maintainers after window closes)

| Family | Voter | Vote | Comment |
|--------|-------|------|---------|
| Anthropic | | | |
| OpenAI | | | |
| Google | | | |
| Open-weight | | | |
| Maintainer 1 | | | |
| Maintainer 2 | | | |

Acceptance threshold: 7 of 10 jury votes (per `VOTING_RULES.md`).

## Decision

[Accepted / Rejected / Withdrawn] on YYYY-MM-DD.
