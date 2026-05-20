# Telemetry & Privacy

MLLANG ships with a built-in `sanitize()` function. Telemetry is **opt-in only**, **off by default**, and the library never auto-enables it.

This page is what you'd want to read before turning anything on.

---

## TL;DR

- **Default:** nothing sent. `MLLANG_TELEMETRY` is unset → `sanitize()` returns `None`.
- **Opt-in levels:** `shape` (recommended), `structured`, `full`.
- **Slot shapes** can go public. **Slot values** stay private.
- **Defense in depth:** payloads containing email / file path / API-key / long-quoted-string patterns are refused, not just redacted.

---

## What is logged at each level

| Slot              | Logged? | What is logged                                  |
|-------------------|---------|-------------------------------------------------|
| `V` (version)     | yes     | as-is (e.g. `0.1.r1`)                           |
| `I` (thread-id)   | hashed  | replaced with `<I:hash:<sha256_12>>`            |
| `G` (goal-map)    | partial | keys only at `structured`; `<REDACTED:N-chars>` at `full` |
| `S` (state-map)   | partial | keys only at `structured`; `<REDACTED:N-chars>` at `full` |
| `D` (decisions)   | no      | array length only                               |
| `E` (evidence)    | no      | array length only                               |
| `U` (unknowns)    | no      | array length only                               |
| `R` (risks)       | no      | array length only                               |
| `T` (test)        | partial | keys + `pass`/`fail` values only                |
| `F` (files)       | no      | array length only; paths NEVER                  |
| `Y` (tool-calls)  | partial | verb names only; args NEVER                     |
| `B` (budget)      | no      | not exposed                                     |
| `N` (next-agent)  | partial | agent code only (e.g. `@K`); verb dropped       |
| `H` (halt)        | yes     | as-is + halt categories                         |
| `P` (confidence)  | yes     | float as-is                                     |
| `A` (assumptions) | partial | count + first 20 chars per item (`full` only)   |
| `EN:` shadow      | no      | character length only                           |

`shape` skips the `partial` slots entirely and only ships top-level signals. `structured` adds keys / verb names / counts. `full` adds the redacted values.

---

## Example: before / after

**Input packet (your machine):**

```
V:0.1.r1; I:project-acme-q3-2026; G:{task=refactor_auth, deadline=Q3, internal_id=ACME-1234};
S:{db_password=correcthorse, env=prod}; D:[migration_plan, rollback_path];
F:[/Users/jane/proj/secret.py]; Y:[$shell(rm -rf /tmp), $curl(api.acme.com/keys)];
N:@K -> ship_to_prod; H:test=pass; P:0.85;
EN: Refactor auth to JWT, preserve user DB.
```

**At `MLLANG_TELEMETRY=shape`:**

```json
{
  "v": "0.1.r1",
  "slots_present": ["V","I","G","S","D","F","Y","N","H","P"],
  "operators_used": ["->","$"],
  "halt": "test=pass",
  "halt_categories": ["test=pass"],
  "confidence": 0.85,
  "next_agent": "@K",
  "thread_hash": "<I:hash:e0d4c2f1a8b7>",
  "level": "shape"
}
```

Zero IP leaked. Thread identity hashed. Goal/state/decisions/files/tool args all gone. The verb `ship_to_prod` is not present — only the agent code `@K`.

**At `MLLANG_TELEMETRY=structured`** — adds the *shape* of the work:

```json
{
  "...": "(everything from shape, plus:)",
  "goal_keys": ["task","deadline","internal_id"],
  "state_keys": ["db_password","env"],
  "test_results": {},
  "tool_verbs": ["shell","curl"],
  "decisions_count": 2,
  "evidence_count": 0,
  "unknowns_count": 0,
  "risks_count": 0,
  "files_count": 1,
  "tool_calls_count": 2,
  "assumptions_count": 0,
  "en_shadow_length": 35
}
```

Still no values, no paths, no tool args, no thread id. Note: this payload above is illustrative — the actual library refuses to ship this exact input because `/Users/jane/proj/secret.py` is a path pattern and `api.acme.com/keys` triggers the `api_*` detector. The refusal returns `None` and nothing leaves the machine.

**At `MLLANG_TELEMETRY=full`** — adds redacted values:

```json
{
  "...": "(everything from structured, plus:)",
  "goal_values_redacted": {
    "task": "<REDACTED:13-chars>",
    "deadline": "<REDACTED:2-chars>",
    "internal_id": "<REDACTED:9-chars>"
  },
  "state_values_redacted": {
    "db_password": "<REDACTED:12-chars>",
    "env": "<REDACTED:4-chars>"
  },
  "assumptions_prefix": []
}
```

Even at `full`, values are length-hints only. The actual strings never leave the machine.

---

## Defense-in-depth: leak detectors

`sanitize()` runs a final scan with `reject_leaks=True` (default). If the raw packet matches any of these patterns, the function returns `None` instead of a payload:

- Email regex: `\b[\w.+-]+@[\w-]+\.[\w.-]+\b`
- File path regex: `(?:/[A-Za-z0-9._-]+){2,}`
- API-key regex: `\b(?:sk|pk|api|key|token|secret|bearer)[-_=][A-Za-z0-9_-]{16,}`
- Long quoted string: `"..."` 60+ chars

A user who flips on `full` and accidentally puts a path or API key into a `G:` value will *not* leak it — the function silently refuses to produce a payload.

You can disable this scan with `sanitize(packet, reject_leaks=False)`, but the default is safe.

---

## How to opt in

**Environment variable (recommended):**

```bash
# Off by default — leave unset for no telemetry
export MLLANG_TELEMETRY=shape          # minimal, recommended
export MLLANG_TELEMETRY=structured     # add keys + counts
export MLLANG_TELEMETRY=full           # research consent only
```

**Per-call override:**

```python
from mllang import sanitize

# Always shape regardless of env
payload = sanitize(packet, level="shape")

# Always off regardless of env
payload = sanitize(packet, level="off")  # returns None
```

**JSON-encoded output:**

```python
from mllang import sanitize_to_json
line = sanitize_to_json(packet)  # one-line JSON or None
if line:
    open("telemetry.jsonl", "a").write(line + "\n")
```

---

## Where the data goes (when you ship it)

The library does **not** send telemetry anywhere — it only produces the sanitized payload. Shipping is the application's choice.

If a hosted endpoint becomes available at `mllang.com/api/log`, it will:

- accept JSON-line payloads from `sanitize()` only
- validate slot shapes server-side (defense in depth)
- refuse any payload that matches the same leak detectors
- batch into Hugging Face Datasets for public audit (no private endpoints)

Status as of 2026-05: no endpoint exists yet. Library-side `sanitize()` is the foundation; the endpoint is deferred until library adoption proves the privacy posture works.

---

## Auditability

- `sanitize()` is open source: see [`parser/mllang/sanitize.py`](../parser/mllang/sanitize.py).
- Conformance suite verifies redaction rules: 34 test cases in `conformance/tests/sanitize_30.jsonl`.
- Any future public corpus on Hugging Face will be downloadable for IP-leak audit.

If you find IP leaking through a published corpus or through `sanitize()` output, please report it. See [`.github/SECURITY.md`](../.github/SECURITY.md) for the disclosure path.

---

## FAQ

**Why hash thread ids instead of dropping them?**
Joining rounds from the same thread is useful for analysis (e.g. confidence trajectory across a multi-round negotiation). The hash provides that linkage without exposing the human-meaningful thread label.

**Why keep `H:` (halt) raw?**
The 9-way halt enum is public spec, not user IP. Knowing the distribution of halts across packets is the central signal a corpus is meant to capture.

**Why log `P:` (confidence)?**
Calibration across LLM families is a public-good signal. The confidence value itself carries no user IP.

**Can I disable the leak scan?**
Yes — `sanitize(packet, reject_leaks=False)`. But the default is on, and there's no good reason to turn it off for production telemetry.

**Where do `K:` and `PRESERVE:` go?**
These are domain-extension slots (e.g. Helen book pack). They are not part of the core spec, so the core sanitizer doesn't track them. Domain packs should ship their own slot-by-slot rules for any extension slots they add.
