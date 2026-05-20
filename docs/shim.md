---
layout: default
title: agent-shim
---

# agent-shim — observability for agent loops

`agent-shim` is the sister package to `mllang-protocol`. Same repo, separate PyPI listing, separate install path.

It records every LLM call in your agent loop to a local JSONL file and aggregates the result. Works **with or without** MLLANG.

```bash
pip install agent-shim                  # standalone observability
pip install 'agent-shim[mllang]'        # + MLLANG signal extraction
pip install 'agent-shim[tiktoken]'      # + exact OpenAI-style token counts
```

---

## Two products, one repo

| Need | Install |
|------|---------|
| Just the MLLANG parser | `pip install mllang-protocol` |
| Just LLM observability (any model, any framework) | `pip install agent-shim` |
| Both together | `pip install agent-shim[mllang]` or `pip install mllang-protocol[shim]` |

The two packages are kept separate on PyPI so you can drop `agent-shim` into a project that has nothing to do with MLLANG — its own value stands alone (token / cost / latency / outcome tracking, local JSONL log, CLI aggregator). When you also have MLLANG packets in your responses, agent-shim auto-extracts the slot signals and the report gains a token-reduction-vs-JSON-RPC column.

See [`shim/README.md`](https://github.com/jakeliu/mllang/blob/main/shim/README.md) for the full API.

---

## What the CLI report looks like

```text
200 packets logged (calls.jsonl)
mean token reduction:  56.8% vs JSON-RPC equivalent  (200/200 packets MLLANG-tagged)
estimated tokens saved: 9,536
estimated $$ saved:    $0.05 @ $5.00/M tokens
tokens in/out:         76,425 / 26,167
estimated $$ spent:    $0.5130
p50 latency:           4.32s    p99: 7.92s
mean P:                0.81
halt distribution:     test=pass 62% | <=> 18% | accept 9% | escalate@H 7% | risk!high 4%
model distribution:    gpt-5.5-thinking 42% | claude-opus-4-7 32% | gemini-pro 13% | gemma-4-26b 10% | deepseek-v3 4%
agent distribution:    @G 23% | @X 21% | @K 20% | @M 19% | @C 17%
```

This is the headline value of pairing MLLANG with agent-shim — without MLLANG packets you'd still get tokens / latency / models, but `mean token reduction`, `halt distribution`, `mean P:`, and `agent distribution` rely on parsing the structured slots out of each response.

---

## Killer-app example: validate the 50-70% claim with your own data

```python
from agent_shim import record

# Run your normal multi-agent loop, but wrap each call:
with record("week.jsonl", parser="mllang") as r:
    for task in tasks:
        out = run_critic(task)            # returns text containing MLLANG packet
        r.observe(response=out.text, model=out.model,
                  tokens_in=out.usage.input, tokens_out=out.usage.output,
                  latency_s=out.elapsed,
                  tags={"phase": "critic", "thread": task.thread_id})
        out = run_solver(task)
        r.observe(response=out.text, model=out.model,
                  tokens_in=out.usage.input, tokens_out=out.usage.output,
                  latency_s=out.elapsed,
                  tags={"phase": "solver", "thread": task.thread_id})

# Then, at the end of the week:
#   agent-shim-report week.jsonl
```

If your `mean token reduction` is consistently ~50-70% across the family of models you actually use, you have empirical confirmation of the MLLANG selling point. If it isn't, that's a useful surprise — the report shows you where (which model? which phase?) it isn't pulling its weight.

---

## When NOT to use agent-shim

- You already pay for LangSmith / Helicone / Langfuse and trust their hosted store. No reason to switch.
- Your loop is a one-off script you'll throw away after the demo. Skip it.
- You need real-time dashboards. agent-shim is local JSONL + a batch CLI; for streaming UI use a hosted vendor or build your own on top of the JSONL.

---

## Tags — a sneaky-useful feature

`observe(..., tags={...})` lets you attach arbitrary key/value labels to each call. The CLI doesn't currently group by tag, but the JSONL is easy to filter with `jq`:

```bash
jq -c 'select(.tags.phase=="critic")' week.jsonl | agent-shim-report /dev/stdin
```

Slice by phase, thread, experiment id, A/B variant, etc.

---

## Status

- **Version:** 0.1.0
- **License:** Apache 2.0
- **PyPI:** [`agent-shim`](https://pypi.org/project/agent-shim/)
- **Source:** [`shim/agent_shim/`](https://github.com/jakeliu/mllang/tree/main/shim/agent_shim)
- **Tests:** [`conformance/test_shim.py`](https://github.com/jakeliu/mllang/blob/main/conformance/test_shim.py) — 21 end-to-end assertions
- **Privacy:** no phone-home. No HTTP egress. Local JSONL only.
