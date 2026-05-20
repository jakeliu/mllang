---
layout: default
title: Markdown-embedded pattern
---

# Markdown-embedded MLLANG

The killer pattern: put MLLANG packets inside fenced code blocks in any markdown file. Humans read the prose. Agents parse the fenced blocks.

---

## Why this works

Markdown is the 2026 "AI mediation layer":

- llms.txt (Stripe, Anthropic, HuggingFace adopted)
- AGENTS.md (Google, OpenAI, Cursor joint standard)
- Cursor rules, .clinerules, CLAUDE.md — all markdown

LLMs already parse markdown by default. Adding a fenced `mllang` block costs nothing in attention and gives agents structured state to act on.

---

## Pattern

````markdown
# Task title (human reads this)

Plain prose describing what you want. Constraints, context, acceptance criteria.

```mllang
V:0.1.r1; I:<thread>; G:{<goal>}; S:{<state>};
D:[<decisions>]; R:[<risks>];
N:@<agent> -> <verb>; H:<halt>; P:<confidence>;
EN: <one-sentence English shadow>.
```

Optional more prose, notes, follow-ups.
````

---

## Real example

````markdown
# Refactor authentication module to JWT

We're switching from session-based auth to JWT tokens. Preserve all user DB
intact. No breaking API changes. Migration must complete in under 10 minutes
of downtime window.

## Acceptance criteria

- Existing sessions auto-migrate without re-login prompt
- All API endpoints return same response shape
- Rollback plan documented before deploy
- Token signing key rotation policy in place

```mllang
V:0.1.r1; I:auth-jwt-migration-001;
G:{task=refactor_auth, from=sessions, to=jwt, deadline=2026-06-15};
S:{users_table=preserve, api_compat=hard, downtime_budget_s=600};
D:[migration_plan, rollback_plan, no_breaking_api, RS256_24h_expiry];
R:[downtime_overrun, token_leak, session_migration_failure];
N:@K -> implement;
H:test=pass;
P:0.85;
EN: Auth refactor sessions→JWT, preserve users DB, no breaking API.
```

## Notes

Token signing key rotation policy: RS256 with 24h expiry. Refresh tokens
rotate every 30 days.
````

---

## Multiple packets in one file

```python
from mllang import extract_from_markdown

md = open("complex_task.md").read()
packets = extract_from_markdown(md)
for i, p in enumerate(packets):
    print(f"Packet {i}: thread={p.thread_id}, next={p.next_agent_code}, halt={p.halt}")
```

A single markdown file can carry multiple MLLANG packets — one per task, sub-task, or pipeline stage.

---

## Drop-in to existing AI rules files

### AGENTS.md

Add a runtime state section:

````markdown
# AGENTS.md

## Build commands
- `npm run build` — production build
- `npm test` — run tests

## Current task

```mllang
V:0.1.r1; I:current-sprint; G:{task=feature_x}; S:{progress=70};
N:@K -> finish; H:test=pass; P:0.75;
EN: Sprint task — finish feature X, target test=pass.
```
````

### CLAUDE.md / Cursor rules

Same pattern — fenced `mllang` block carries runtime state alongside human-readable rules.

---

## What agents do with the block

Any MLLANG-aware agent can:

1. **Route** — read `N:` slot, hand off to the named agent
2. **Halt-check** — if `H:test=pass` and tests pass, finalize; otherwise iterate
3. **Confidence-gate** — if `P:` below threshold, request human review
4. **Resume** — read `I:` thread-id + `^rN` parent ref, continue prior conversation
5. **Audit** — log packet to trail for later replay

---

## Why this is the killer pattern

Markdown files are already used for:
- READMEs
- Issue templates
- AGENTS.md / CLAUDE.md / Cursor rules
- llms.txt sitemaps
- Documentation

Adding MLLANG fenced blocks = **zero new file types**, **zero new infrastructure**, **immediate agent-readable runtime state**.

Drop-in for any project. No SDK install needed for the basics.
