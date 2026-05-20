# shim-engine

Local-first observability for LLM-agent loops. Wrap any LLM call, get a JSONL log of token counts, latency, cost, and outcome. Aggregate with the bundled CLI. No SaaS, no hosted UI, no telemetry sent anywhere.

Optional MLLANG awareness for 5x more signal — install with `[mllang]` extra.

```bash
pip install shim-engine
# or, with MLLANG signal extraction:
pip install 'shim-engine[mllang]'
```

## 60-second example

```python
from shim_engine import record

with record("calls.jsonl", parser="mllang") as r:
    response = llm_client.chat(prompt)
    r.observe(
        response=response.text,
        model="claude-opus-4-7",
        tokens_in=response.usage.input,
        tokens_out=response.usage.output,
        latency_s=elapsed,
        tags={"call_type": "critic", "thread_id": "abc"},
    )
```

Then:

```bash
$ shim-engine-report calls.jsonl
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

## Use without MLLANG

`shim-engine` works just fine on plain LLM responses. Drop the `parser="mllang"` and you still get:

- Token in/out counts
- Latency
- Cost estimate ($5/M tokens default; override via `cost_per_M=` or `SHIM_ENGINE_COST_PER_M` env)
- Model distribution
- p50 / p99 latency
- Arbitrary user tags (`call_type`, `thread_id`, etc.) for slicing

The only thing you lose by skipping MLLANG: the slot-structured signals (`halt` distribution, `confidence` calibration, `agent_code` routing graph) and the JSON-RPC token-reduction comparison.

## Use with MLLANG

When `parser="mllang"` is set and `shim-engine[mllang]` (or `mllang-protocol`) is installed, shim-engine looks at each response for an MLLANG packet (either as a bare line or inside a ```mllang fenced block). When found, it extracts:

| Field | Meaning |
|-------|---------|
| `halt` | The `H:` slot value (e.g. `test=pass`, `<=>`, `risk!high`) |
| `confidence` | The `P:` slot float |
| `agent_code` | The agent in `N:` slot (e.g. `@K`, `@C`) |
| `slots_present` | Uppercase slot keys actually populated |
| `json_rpc_chars` | Size of a JSON-RPC envelope with the same content |
| `reduction_pct` | `(json_rpc_tokens - response_tokens) / json_rpc_tokens * 100` |
| `tokens_saved_est` | Tokens-in-JSON-RPC minus tokens-in-response |

These flow straight into the report.

## API

```python
# Context manager — preferred for batches:
with record(path, parser="none") as r:
    r.observe(response="...", model="...", tokens_in=N, tokens_out=N, latency_s=N)

# Decorator — preferred for already-wrapped functions:
from shim_engine import instrument

@instrument(path="calls.jsonl", parser="mllang")
def critique(prompt):
    out = llm.chat(prompt)
    return {"response": out.text, "model": out.model,
            "tokens_in": out.usage.input, "tokens_out": out.usage.output}

# One-shot — preferred for ad-hoc:
from shim_engine import observe
observe(response="...", model="...", tokens_in=N, tokens_out=N, latency_s=N,
        parser="none", path="calls.jsonl")
```

## Environment variables

| Variable | Default | What |
|----------|---------|------|
| `SHIM_ENGINE_LOG` | `shim_engine.jsonl` | Default log path when no path is passed |
| `SHIM_ENGINE_COST_PER_M` | `5.0` | USD per 1M tokens for cost estimate |

## Privacy posture

- shim-engine does not phone home. No HTTP egress. Logs are local JSONL.
- When used with `parser="mllang"`, the captured signals are slot SHAPES (halt, confidence, agent code) — NOT slot values. The same redaction posture as `mllang.sanitize()` (off-by-default values, defense-in-depth leak detection) applies if you choose to ship the log onward.
- Free-form `tags` you pass are stored verbatim. Don't put secrets in tags.

## Why local-first

Hosted observability (LangSmith / Helicone / Langfuse) is great when you trust the vendor with your prompts. For everything else — proprietary agent loops, security-sensitive workflows, offline experiments, students on free tiers — a 250-LOC stdlib library that writes JSONL is the simpler answer. shim-engine ships zero hard runtime dependencies. tiktoken is an optional extra for exact OpenAI-style token counts; without it the library uses a `len(text) // 4` heuristic.

## License

Apache 2.0. Same as `mllang-protocol`. Same repo: github.com/jakeliu/mllang.
