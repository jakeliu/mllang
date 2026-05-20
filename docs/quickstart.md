---
layout: default
title: Quickstart
---

# Quickstart

## Install

```bash
git clone https://github.com/jakeliu/mllang.git
cd mllang
pip install -e parser/
```

(PyPI release coming after v0.1.0 git tag.)

---

## Parse a packet

```python
from mllang import parse

p = parse("V:0.1.r1; I:demo; G:{task=test}; S:{x=1}; N:@K -> classify; H:<=>; P:0.85;")
print(p.next_agent)    # @K -> classify
print(p.next_agent_code)  # @K
print(p.halt)          # <=>
print(p.confidence)    # 0.85
```

---

## Compose a packet

```python
from mllang import Packet, compose

p = Packet(
    version="0.1.r1",
    thread_id="auth-refactor-001",
    goal={"task": "refactor_auth", "from": "sessions", "to": "jwt"},
    state={"users_db": "preserve", "api_compat": "hard"},
    decisions=["migration_plan", "rollback_path"],
    risks=["downtime", "token_leak"],
    next_agent="@K -> implement",
    halt="test=pass",
    confidence=0.85,
    en_shadow="Refactor auth sessions→JWT, preserve DB + API.",
)
print(compose(p))
```

Output:
```
V:0.1.r1; I:auth-refactor-001; G:{task=refactor_auth, from=sessions, to=jwt}; S:{users_db=preserve, api_compat=hard}; D:[migration_plan, rollback_path]; R:[downtime, token_leak]; N:@K -> implement; H:test=pass; P:0.85;
EN: Refactor auth sessions→JWT, preserve DB + API.
```

---

## Extract packets from markdown

```python
from mllang import extract_from_markdown

md = open("task.md").read()
packets = extract_from_markdown(md)
for p in packets:
    print(p.thread_id, p.next_agent_code, p.halt, p.confidence)
```

This finds every fenced ` ```mllang ` block in the markdown and parses each into a `Packet`.

---

## Validate a packet

```python
from mllang import parse

p = parse("V:0.1.r1; G:{task=t}; H:<=>;")  # missing required slots
errors = p.validate()
for e in errors:
    print(e)
```

Output:
```
missing required slot S (state)
missing required slot N (next agent)
```

---

## Bootstrap an LLM

Want an LLM (Claude, GPT, Gemini, etc.) to speak MLLANG? Paste [`bootstrap/session_init.md`](https://github.com/jakeliu/mllang/blob/main/bootstrap/session_init.md) into a fresh chat as the first message.

After that, the LLM will emit MLLANG packets in its responses.

---

## Run conformance suite

```bash
python conformance/run_conformance.py
```

Should output:
```
PARSE tests:      50 passed, 0 failed
HALT tests:       15 passed, 0 failed
ROUNDTRIP tests:  50 passed, 0 failed
MARKDOWN tests:   1 passed, 0 failed
--- TOTAL: 116 passed, 0 failed ---
```
