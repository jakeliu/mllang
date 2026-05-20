---
layout: default
title: Markdown-embedded pattern
---

# Markdown-embedded MLLANG

Pattern: a short workflow summary + one fenced ```mllang block. That's it. Humans glance at the summary, agents parse the packet.

The packet already carries the state. The `EN:` shadow line inside the packet is the 1-sentence human-readable channel. So the surrounding text stays tight.

---

## The default pattern (summary mode)

````markdown
# Refactor auth module

Workflow: switch sessions → JWT, gate on test=pass, rollback ready.

```mllang
V:0.1.r1; I:auth-jwt-001;
G:{task=refactor_auth, from=sessions, to=jwt};
S:{users_db=preserve, api_compat=hard};
D:[migration_plan, rollback_path];
R:[downtime, token_leak];
N:@K -> implement;
H:test=pass;
P:0.85;
EN: Refactor auth sessions → JWT, preserve DB, no breaking API.
```
````

Three lines outside the packet. The packet is the spec. The `EN:` line covers humans who skim. No content duplication.

---

## Why short beats long

Long prose duplicates packet content for a human reader who is rarely going to read it. For agent-loaded files (`AGENTS.md`, `llms.txt`, runtime-state docs) every duplicate token costs context budget.

Compact form:
- Smaller — less tokens per round
- Faster — less for the agent to parse before it acts
- One source of truth — packet is canonical, summary is a glance
- No drift — long prose can desync from the packet; a 1-line summary can't

`EN:` line inside the packet is the dual-channel. No separate long prose needed.

---

## Build it from Python

```python
from mllang import Packet, embed_in_markdown

p = Packet(
    version="0.1.r1",
    thread_id="auth-jwt-001",
    goal={"task": "refactor_auth", "from": "sessions", "to": "jwt"},
    state={"users_db": "preserve", "api_compat": "hard"},
    decisions=["migration_plan", "rollback_path"],
    risks=["downtime", "token_leak"],
    next_agent="@K -> implement",
    halt="test=pass",
    confidence=0.85,
    en_shadow="Refactor auth sessions → JWT, preserve DB, no breaking API.",
)

md = embed_in_markdown(
    p,
    title="Refactor auth module",
    summary="Workflow: switch sessions → JWT, gate on test=pass, rollback ready.",
)
print(md)
```

---

## Pull both channels back out

```python
from mllang import extract_summary_and_packet

summary, packet = extract_summary_and_packet(open("task.md").read())
print(summary)              # the workflow summary line(s)
print(packet.next_agent)    # @K -> implement
print(packet.halt)          # test=pass
```

`extract_summary_and_packet()` returns the text above the first fenced `mllang` block (minus any `# heading`) plus the parsed `Packet`.

---

## Verbose mode (opt-in)

Some files are written for humans first — design docs, PR descriptions, issues, AGENTS.md sections that explain *why*. Keep the long prose there with `mode="verbose"`:

```python
md = embed_in_markdown(
    p,
    title="Refactor auth module",
    prose=(
        "We are switching from session-based auth to JWT to support stateless "
        "multi-region deployments. Existing users must not be forced to re-login. "
        "Migration must complete inside the 10-minute deploy window. Rollback "
        "plan must be documented and tested before merge."
    ),
    mode="verbose",
)
```

This restores the prose-then-packet shape for cases where a human really will read the file end-to-end. Use it for documentation, not for runtime state.

---

## packet_only mode

When the file is purely agent-consumed and even a one-line summary is overhead:

```python
md = embed_in_markdown(p, mode="packet_only")
```

Just the fenced block. Cheapest.

---

## When to use which mode

| Mode          | When                                          |
|---------------|-----------------------------------------------|
| `summary`     | Default. Agent-loaded files. AGENTS.md, llms.txt, runtime-state notes. |
| `verbose`     | Human-authored docs. PR descriptions, design notes, onboarding docs. |
| `packet_only` | Pure agent pipelines, queue payloads, transport bodies. |

---

## What agents do with the block

Any MLLANG-aware consumer can:

1. **Route** — read `N:` slot, hand off to the named agent
2. **Halt-check** — if `H:test=pass` and tests pass, finalize; otherwise iterate
3. **Confidence-gate** — if `P:` below threshold, request human review
4. **Resume** — read `I:` thread-id + `^rN` parent ref, continue prior conversation
5. **Audit** — log packet to trail for later replay

The agent never has to parse the surrounding prose. The packet is enough.

---

## Drop-in to existing AI rules files

### AGENTS.md (summary mode)

````markdown
# AGENTS.md

## Build commands
- `npm run build` — production build
- `npm test` — run tests

## Current task

Workflow: finish feature X, target test=pass.

```mllang
V:0.1.r1; I:current-sprint; G:{task=feature_x}; S:{progress=70};
N:@K -> finish; H:test=pass; P:0.75;
EN: Sprint task — finish feature X, target test=pass.
```
````

### CLAUDE.md / Cursor rules

Same pattern. The runtime state block is independent of the human-readable rules above it.

---

## Multiple packets in one file

```python
from mllang import extract_from_markdown

packets = extract_from_markdown(open("complex_task.md").read())
for p in packets:
    print(p.thread_id, p.next_agent_code, p.halt)
```

A single markdown file can carry multiple MLLANG packets — one per sub-task or pipeline stage.

---

## Why this is the killer pattern

Markdown files already live in every project: READMEs, issue templates, AGENTS.md, CLAUDE.md, Cursor rules, llms.txt, docs.

Adding an MLLANG fenced block costs **zero new file types** and **zero new infrastructure**. The packet rides the existing markdown channel. Summary mode keeps the human-facing tax to one line. Verbose mode is there when humans really do read the page.
