---
layout: default
title: MLLANG
---

# MLLANG — Markdown Language for AI Agents

Compact text-surface protocol for AI-agent state. Lives inside markdown fenced blocks. Cross-vendor ratified across 6+ LLM families.

[GitHub repo →](https://github.com/jakeliu/mllang)
[Spec (v0.1 locked) →](https://github.com/jakeliu/mllang/blob/main/spec/MLLANG_v0.1.locked.md)
[Quickstart →](quickstart.html)
[Markdown-embedded pattern →](markdown-embedded.html)

---

## 30-second example

```markdown
# Refactor auth module to JWT

We're switching from sessions to JWT. Preserve user DB.

​```mllang
V:0.1.r1; I:auth-001; G:{task=refactor}; S:{users_db=preserve};
N:@K -> implement; H:test=pass; P:0.85;
EN: Refactor auth sessions→JWT.
​```
```

Humans read the markdown. Agents parse the fenced `mllang` block.

---

## Why it exists

Multi-agent workflows need state handoff. Existing options:

- **JSON-RPC** (MCP / A2A) — verbose, ~200-500 token envelope overhead per call
- **Plain prose** — drifts, no shared structure, hard to validate
- **YAML frontmatter** — better, but per-file only, not multi-block
- **Each team rolls own slot syntax** — fragmentation

MLLANG = small shared convention. Sits inside existing standards as runtime state payload.

---

## What it's not

- Not a programming language
- Not a competing transport (MCP / A2A own that)
- Not a vendor lock-in (works with any LLM)
- Not Turing-complete

It's a **convention**, not new infrastructure. 200-line spec, parses in 50 LOC.

---

## Where it fits

| Layer | Standard | MLLANG role |
|-------|----------|-------------|
| Docs / agent rules | AGENTS.md, llms.txt | host fenced MLLANG blocks |
| Tool transport | MCP | carry MLLANG in tool payload |
| Agent transport | A2A, ACP | carry MLLANG in message body |
| Runtime state | **MLLANG** | slot grammar, halt enum, confidence |

---

## License

Apache 2.0.
