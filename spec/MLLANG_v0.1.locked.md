# MLLANG v0.1 — LOCKED

Status: **LOCKED** 2026-05-19. Ratified across 8 deployments / 5 vendor families.

Mean ratification confidence: 0.95. Total rounds: 10.

ASCII-only. Tokenizer-stable across Claude / GPT / Gemini / Codex / Gemma.

---

## 1. Agent codes

| Code | Model family |
|------|--------------|
| `@C` | Claude (Opus/Sonnet/Haiku) |
| `@X` | ChatGPT (GPT-5.x / GPT-4.x) |
| `@K` | Codex (codex CLI, gpt-5.5) |
| `@G` | Gemini (Pro / Flash) |
| `@M` | Gemma (local LM Studio) |
| `@H` | Human |
| `@?` | Unknown / any |

Domain-specific deployments may add their own codes via `lib_<domain>.mllang` extension packs.

---

## 2. Slots — 16 total, canonical order

Order is fixed. Drop unused. Required marked *.

| Pos | Key | Meaning | Required |
|-----|-----|---------|----------|
| 1 | `V:` * | version + round (e.g. `V:0.1.r3`) | yes |
| 2 | `I:` | thread id | optional |
| 3 | `G:` * | goal | yes |
| 4 | `S:` * | state (known / done) | yes |
| 5 | `D:` | decisions | optional |
| 6 | `E:` | evidence (files, runs, citations) | optional |
| 7 | `U:` | unknowns / open questions | optional |
| 8 | `R:` | risks / failure modes | optional |
| 9 | `T:` | test / verification result | optional |
| 10 | `F:` | files touched | optional |
| 11 | `Y:` | tool-call / external-action marker | optional |
| 12 | `B:` | budget cap (tokens \| time \| money) | optional |
| 13 | `N:` * | next: `@agent -> action` | yes |
| 14 | `H:` * | halt condition | yes |
| 15 | `P:` | confidence (float 0.00–1.00) | optional |
| 16 | `A:` | assumptions | optional |

Canonical order: `V I G S D E U R T F Y B N H P A`

---

## 3. Operators — 19 total

| Symbol | Meaning |
|--------|---------|
| `=` | is / equals |
| `:=` | assign |
| `==` | confirmed equal (verified) |
| `?` | unknown / open |
| `!` | assertion / must |
| `*` | important / pinned |
| `~` | approximate / loose |
| `^` | parent / prior round (e.g. `^r1`) |
| `->` | leads to / next step |
| `=>` | implies / therefore |
| `<=>` | agreed by all parties (halt value) |
| `&` | and |
| `\|` | or |
| `^!` | **reserved compound** — never appears bare |
| `#` | tag / topic |
| `$` | tool-invocation shorthand (inside `Y:` slot only) |
| `[ ]` | list / set |
| `{ }` | map / struct |
| `( )` | group |
| `;` | slot separator |
| `,` | item separator |

---

## 4. Verbs (for `N:` slot)

`review` `propose` `agree` `reject` `revise` `merge` `test` `fix` `report` `halt` `escalate@H` `lock`

---

## 5. Halt values (`H:` slot)

```
accept | repair | regen | escalate@H | after-N-rounds | test=pass | test=fail | risk!high | <=>
```

Semantics:
- `accept` — packet output good, move on
- `repair` — local window repair only
- `regen` — full regeneration of round
- `escalate@H` — hand to human
- `after-N-rounds` — round cap reached
- `test=pass` — deterministic check green
- `test=fail` — deterministic check red, block
- `risk!high` — abort, escalate
- `<=>` — all agents in agreement, terminal lock

Multiple values allowed (e.g. `H:after-5-rounds | <=>`). First match wins.

---

## 6. Confidence (`P:` slot)

Float `0.00`–`1.00`. Two decimal places.

- `P:0.00–0.40` = low (may auto-route to `escalate@H`)
- `P:0.40–0.75` = medium
- `P:0.75–1.00` = high

Banded values deferred to v0.2.

---

## 7. Budget (`B:` slot)

```
B:{tokens=<int>, time=<seconds>, money=<usd>}
```

Examples:
```
B:{tokens=5000}
B:{time=300, money=0.50}
```

Exceeding cap forces `H:risk!high`.

---

## 8. Tool calls (`Y:` slot)

```
Y:[$<verb>(<args>), ...]
```

`$` valid **only inside `Y:`**.

Examples:
```
Y:[$bash("ls /tmp")]
Y:[$codex_exec(model=gpt-5.5, effort=high, prompt="diagnose login failure")]
Y:[$curl("https://api.example.com/v1/status"), $sqlite("app.db", "SELECT * FROM jobs")]
```

Tool results return in receiving agent's next `E:` slot.

---

## 9. Packet grammar

```
packet  := slot (';' slot)* ';'?
slot    := KEY ':' value
value   := atom | list | map | expr
list    := '[' value (',' value)* ']'
map     := '{' kv (',' kv)* '}'
kv      := key '=' value
expr    := atom op atom
atom    := word | '@'agent | '#'tag | number | path | quoted
quoted  := '"' ... '"'
```

---

## 10. Output format (dual-channel)

Every message = ONE MLLANG packet + ONE English-shadow line.

```
V:0.1.rN; <slots...>; H:<...>;
EN: One-sentence summary of packet intent.
```

- `EN:` prefix required.
- `EN:` ≤ 1 sentence in steady-state. Allowed 2–3 sentences during refinement phase.
- No prose preamble, no markdown outside the packet.
- Code, file paths, error strings: keep verbatim, do not encode.

---

## 11. Canonical example

```
V:0.1.r4; I:demo; G:^r3; S:{reviewed=@G}; D:[accept-all]; U:[]; R:[]; N:@C -> lock; H:<=>; P:0.95;
EN: Reviewer agrees, ready to lock.
```

---

## 12. Markdown-embedded usage (the killer pattern)

MLLANG lives inside fenced code blocks in any markdown file. Humans read the prose; agents parse the fenced block.

```markdown
# Refactor authentication module to JWT

Switch from sessions to JWT. Preserve user DB. No breaking API.

​```mllang
V:0.1.r1; I:auth-001; G:{task=refactor_auth, from=sessions, to=jwt};
S:{users_db=preserve, api_compat=hard}; D:[migration_plan, rollback_path];
R:[downtime, token_leak]; N:@K -> implement; H:test=pass; P:0.85;
EN: Refactor auth sessions→JWT, preserve DB + API compat.
​```
```

Library helper: `extract_from_markdown(text)` returns all packets parsed from `mllang` fences.

---

## 13. Non-goals (v0.1)

- Not a programming language. No control flow beyond `->`.
- Not Turing-complete. Pure state-carrier.
- Not human-readable by default — `EN:` line is the human fallback.
- Not a replacement for code — code stays in code blocks.
- Not real RecursiveMAS latent transfer — closed APIs expose no hidden states. MLLANG is a text-surface approximation.

---

## 14. Collaboration patterns (declare in `G:`)

| Pattern | Roles | Use for |
|---------|-------|---------|
| Sequential | Planner → Critic → Solver | reasoning, single answer |
| Mixture | [Domain experts] → Summarizer | multi-domain queries |
| Distillation | Expert → Learner | speed/cost tradeoff |
| Deliberation | Reflector ↔ ToolCaller | tool-use loops |

Declare: `G:{pattern=sequential, task=...}`.

---

## 15. Recursion default

`H: after-3-rounds | <=>` default.

- Rounds 1–2: MLLANG packets only, no `EN:` required (latent rounds).
- Final round: packet + ONE `EN:` line summarizing whole trace.

---

## 16. Versioning

`V:MAJOR.MINOR.rROUND`
- MINOR bump on slot/operator change.
- ROUND increments every packet within a thread.
- Lock to v0.1 → 4 weeks real use → propose v0.2 from telemetry.

---

## 17. Deferred to v0.2

- `P:` banding `low|med|high` alongside float
- Compression-tier slot (`std|mini|ultra`)
- Macro references beyond `^rN` (e.g. `^@C` last-from-Claude)
- Optional 4-way `H:` simplification

Domain-specific extensions (`T_PROFILE:`, beat-level routing) live in extension packs, not core spec.

---

## 18. Compatibility with other standards

MLLANG composes with existing standards rather than replacing them:

| Layer | Standard | Role |
|-------|----------|------|
| Doc/agent rules | AGENTS.md / llms.txt | host markdown containing MLLANG blocks |
| Tool calls | MCP (Model Context Protocol) | carry MLLANG packets as tool payload |
| Agent transport | A2A / ACP | carry MLLANG packets as message body |
| Runtime state | MLLANG | THIS LAYER — slot grammar, halt enum, confidence |

---

## 19. Reference parser

Python 3 parser available in [`parser/`](../parser/). Pure stdlib, ~200 LOC.

Conformance test suite at [`conformance/`](../conformance/) — 115-packet test set, any implementation can run + score.

---

End of spec. Lock immutable. Next change = v0.2 RFC.
