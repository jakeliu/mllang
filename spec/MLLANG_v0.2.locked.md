# MLLANG v0.2 — LOCKED

Status: **LOCKED** 2026-05-24. Round-trip clean on 9 model instances across 5 LLM families.

**Inspiration credit:** the core idea (multi-agent state exchange) is inspired by [RecursiveMAS](https://github.com/RecursiveMAS/RecursiveMAS) (arXiv 2604.25917). RecursiveMAS exchanges latent vectors between agents; MLLANG is the text-surface approximation that works for closed APIs where latent access is not available. Full credit to the RecursiveMAS team for the underlying multi-agent recursion idea.

ASCII-only. Tokenizer-stable across Claude / GPT / Gemini / Codex / Gemma.

v0.2 is a **strict superset** of v0.1. Every v0.1 packet is a valid v0.2 packet.
v0.1 parsers ignore unknown v0.2 slots and continue parsing the rest of the packet correctly.

For v0.1 base definitions (agent codes, slot order, operators, halt values, verbs,
budget, tool calls, grammar, output format, markdown embedding), see
[`MLLANG_v0.1.locked.md`](MLLANG_v0.1.locked.md). This document specifies only
the v0.2 deltas.

---

## 1. New slots

### 1.1 `CAP:` — structured capability payload

Used together with `T:cap` (see §2). Required when `T:cap` is present, forbidden
otherwise. Format:

```
CAP:{agent_id:@<AGENT>, family:<canonical_family>, algorithm:<short_str>,
     verbs:[{name:<verb>, required:[<slot>...], optional:[<slot>...], side_effects:<bool>}, ...],
     runtime:{<lib>:<version>, ...},
     state:{trained:<bool>} | {stateless:true}}
```

Constraints:
- `agent_id` MUST equal the harness's `@TARGET` identity.
- `family` MUST come from the canonical family enum (see §4).
- `verbs[].name` MUST be addressable via `N:@target -> verb`.
- `verbs[].side_effects` MUST accurately report state mutation.
- `runtime` is optional; include if reproducibility matters.

### 1.2 `TR:` — multi-hop trace

Optional. Carries chain identity across packet hops:

```
TR:{root:<root_id>, parent:<parent_id>, depth:<int>}
```

- `root` is the conversation/chain root id (constant across all hops).
- `parent` is the immediate sender's packet `I:` (the upstream caller).
- `depth` starts at 0 for the root request, increments by 1 per hop.

Receivers MUST preserve a received `TR:` slot in their response. Composers SHOULD
inject `TR:` when initiating a multi-step chain.

### 1.3 `SIG:` — HMAC-SHA256 packet signature

Optional. When present:

```
SIG:<hex_lowercase>
```

`SIG` is HMAC-SHA256(key, canonicalized_packet_bytes_without_SIG_slot), hex-encoded.

Canonicalization (deterministic):
1. Strip leading/trailing whitespace.
2. Remove any existing `SIG:` slot.
3. Collapse internal whitespace to single spaces.
4. Collapse repeated `;` separators to single `;`.
5. Ensure exactly one trailing `;`.

Receivers MUST reject packets with `SIG:` present but invalid using
`ERR_AUTH_FAIL`. Receivers MAY treat absent `SIG:` as out-of-policy when running
in a signed-only mode; otherwise absence is acceptable (backward compat with v0.1).

Key distribution is out of scope; v0.2 reference implementation reads
`MLLANG_SIG_KEY` from environment.

---

## 2. Expanded `T:` slot

v0.1 used `T:` exclusively for test verification (`T:test=pass`, `T:test=fail`).
v0.2 expands `T:` to also carry a **packet-type discriminator** for routing
helpers. Values are disjoint strings, so the two usages coexist.

| `T:` value | Meaning | Companion slot |
|---|---|---|
| `test=pass` / `test=fail` (v0.1) | verification result | none |
| `cap` (v0.2) | capability discovery payload follows | `CAP:` required |
| `err` (v0.2, reserved) | error response packet | `O:{err:ERR_*}` |
| `route` (v0.2, reserved) | routing decision packet | `ROUTE:` |

A packet MUST NOT carry conflicting `T:` values (a `T:cap` packet is not also a
`T:test=pass` packet).

---

## 3. Map-form `N:` slot (vendor-safe encoding)

v0.1 form is preserved:

```
N:@AGENT -> verb
```

v0.2 adds an equivalent map-form:

```
N:{agent:"@AGENT", verb:"verb_name"}
```

Both forms parse to the same `(agent, verb)` tuple. The map form is RECOMMENDED
for cross-vendor composition because some LLM tokenizers (notably Gemini 2.5
Pro) rewrite unquoted `@<token>` patterns into local-file paths in the bare-N:
form. With map form the `@` lives inside a quoted dict value and is preserved.

Receivers MUST accept both forms. Composers MAY use either.

---

## 4. Canonical family enum (for `CAP.family`)

```
supervised_classifier         regression
gradient_boosting             random_forest
logistic_regression           support_vector_machine
k_nearest_neighbors           clustering
anomaly_detection             time_series_forecasting
recommendation                computer_vision
ocr_document_understanding    speech_to_text
text_to_speech                graph_ml
bayesian_probabilistic        causal_inference
reinforcement_learning        optimization_constraint_solver
embedding                     reranker
retrieval_augmented_generation llm_foundation_model
os_software_gateway           hardware_gateway
```

Adding a new family requires an RFC. Harnesses that do not match a canonical
family SHOULD use the closest match plus a free-form `cap.subfamily:` field.

---

## 5. Canonical error code registry (for `O.err`)

Every error packet MUST surface a code from this list as the prefix of `O.err`:

```
ERR_NOT_CAPABLE         ERR_NOT_FOUND
ERR_NEEDS_CREDENTIALS   ERR_NEEDS_PAIRING
ERR_DOMAIN_MISMATCH     ERR_BAD_URL
ERR_BAD_FORMAT          ERR_BAD_IMAGE
ERR_OOB                 ERR_SHAPE_MISMATCH
ERR_TOO_SHORT           ERR_TOO_LONG
ERR_TOO_SMALL           ERR_HA_HTTP
ERR_HA_UNREACHABLE      ERR_HA_UNEXPECTED
ERR_BACKEND_UNAVAILABLE
ERR_KASA_DISCOVER_FAILED ERR_KASA_CALL_FAILED
ERR_TTS_BACKEND_UNAVAILABLE ERR_TTS_TIMEOUT ERR_TTS_FAILED
ERR_OCR_BACKEND_UNAVAILABLE ERR_STT_BACKEND_UNAVAILABLE
ERR_NOT_DIR             ERR_NOT_READY
ERR_MISSING_SLOT        ERR_TYPE_MISMATCH
ERR_INSUFFICIENT_DATA   ERR_LIB
ERR_TARGET_MISMATCH     ERR_BAD_PACKET
ERR_AUTH_FAIL
```

Format: `ERR_<UPPERCASE_SNAKE>`. Optional `: <human-readable detail>` suffix.
Adding a new code requires an RFC.

---

## 6. Canonical example (v0.2 with all new slots)

```
V:0.2.r1; I:demo; G:{}; T:cap;
N:{agent:"@ML_CLF", verb:"ml.capabilities"};
H:done; P:0.95;
CAP:{agent_id:@ML_CLF, family:supervised_classifier,
     algorithm:tfidf+logistic_regression,
     verbs:[{name:clf.predict, required:[text], side_effects:false},
            {name:clf.train,   optional:[texts,labels], side_effects:true}],
     runtime:{sklearn:1.6.1}, state:{trained:true, n_train:16}};
TR:{root:demo, depth:0};
SIG:<hmac_sha256_hex>;
EN:@ML_CLF announces capability.
```

---

## 7. Compatibility matrix (verified 2026-05-24)

| Family | Vendor | Result |
|---|---|---|
| Anthropic | Claude Sonnet 4.6 / Opus 4.7 | ✓ compose + parse |
| OpenAI | Codex (gpt-5.5) | ✓ compose + parse |
| Google | Gemini 2.5 Pro | ✓ compose + parse (map-form N: required) |
| Open-weight | Gemma-4-e4b (local 127.0.0.1) | ✓ compose + parse |
| Open-weight | Gemma-4-26b-a4b-it (AIR 192.168.4.24) | ✓ compose + parse |

Round-trip artifacts archived under [`rfc/voting_packets/0001/`](../rfc/voting_packets/0001/).

---

## 8. Deferred to v0.3

- `P:` banding (`low|med|high`) inline with float
- Compression-tier slot (`std|mini|ultra`)
- Macro references beyond `^rN`
- `T:route` + `ROUTE:` slot pair (sketched in RFC 0001, implementation deferred)
- Chinese-vendor + non-Gemma open-weight inter-op tests

---

## 9. Spec lock

This document is **immutable** as of 2026-05-24. Subsequent changes require
v0.3 RFC. Editorial typos may be fixed without RFC; semantic changes may not.

Reference implementations:
- Parser: [`parser/mllang/`](../parser/mllang/) (pure stdlib, ~200 LOC); accepts v0.2 packets via unknown-slot passthrough.
- Single-file reference runner: [`examples/weather_runner.py`](../examples/weather_runner.py) — demonstrates the parse / compose / dispatch path including the new `cap_packet_with_output`, `inject_trace`, and map-form `N:` handling.

T:cap, TR:, SIG: composition follow the templates in §1-§3 above. A receiving
implementation only needs:
1. Slot-passthrough parser (already in v0.1 reference).
2. HMAC-SHA256 if signing is needed (Python stdlib `hmac`).
3. Acceptance of map-form `N:` (8 lines of code, see §3).

Conformance: `conformance/tests/cap_20.jsonl` (14 v0.2-specific cases) plus the
v0.1 suite (166 cases) — all 180 green at lock time.

End of spec.
