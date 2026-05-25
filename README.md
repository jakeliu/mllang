# MLLANG — Markdown Language for AI Agents

[![PyPI](https://img.shields.io/pypi/v/mllang-protocol.svg)](https://pypi.org/project/mllang-protocol/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Spec: v0.2 locked](https://img.shields.io/badge/spec-v0.2_locked-green.svg)](spec/MLLANG_v0.2.locked.md)
[![Vendors: 9+](https://img.shields.io/badge/vendors-9%2B_ratified-orange.svg)](spec/MLLANG_v0.2.locked.md)
[![CI](https://github.com/jakeliu/mllang/actions/workflows/ci.yml/badge.svg)](https://github.com/jakeliu/mllang/actions/workflows/ci.yml)

> Compact text-surface protocol for AI-agent state. Lives inside markdown fenced blocks. Cross-vendor ratified across 6+ LLM families.

---

## What it solves

Multi-agent workflows need to pass state between LLM turns. JSON-RPC is verbose. Plain prose drifts. Every team invents their own slot syntax. MLLANG = a small shared convention that fits inside markdown fenced blocks, 50–70% less tokens than JSON-RPC for the same state.

---

## 30-second example

````markdown
# Refactor auth module

Workflow: switch sessions → JWT, gate on test=pass, rollback ready.

```mllang
V:0.1.r1; I:auth-001; G:{task=refactor_auth, from=sessions, to=jwt};
S:{users_db=preserve, api_compat=hard}; D:[migration_plan, rollback_path];
R:[downtime, token_leak]; N:@K -> implement; H:test=pass; P:0.85;
EN: Refactor auth sessions → JWT, preserve DB + API compat.
```
````

One-line workflow summary above the fenced block, full state inside the packet, `EN:` line for human skim. No content duplication. Agents parse the block; humans glance at the summary. Long prose is opt-in (`mode="verbose"`) for human-authored docs.

See [`docs/markdown-embedded.md`](docs/markdown-embedded.md) for the full pattern.

---

## Quick start

```python
from mllang import Packet, embed_in_markdown, extract_summary_and_packet

# Build a packet
p = Packet(
    version="0.1.r1",
    thread_id="auth-001",
    goal={"task": "refactor_auth", "to": "jwt"},
    state={"users_db": "preserve"},
    next_agent="@K -> implement",
    halt="test=pass",
    confidence=0.85,
    en_shadow="Refactor auth sessions → JWT, preserve DB.",
)

# Embed in markdown (summary mode = default, tight)
md = embed_in_markdown(
    p,
    title="Refactor auth module",
    summary="Workflow: switch sessions → JWT, gate on test=pass.",
)

# Pull both channels back out
summary, packet = extract_summary_and_packet(md)
print(summary)              # the workflow summary
print(packet.next_agent)    # @K -> implement
print(packet.halt)          # test=pass
```

Three modes: `summary` (default, agent-loaded files), `verbose` (long prose for human-authored docs), `packet_only` (pure agent pipelines).

---

## Where it fits

MLLANG composes with existing standards rather than replacing them:

| Layer | Standard | Role |
|-------|----------|------|
| Doc / agent rules | AGENTS.md, llms.txt, Cursor rules | host markdown containing MLLANG blocks |
| Tool calls | MCP (Model Context Protocol) | carry MLLANG packets as tool payload |
| Agent transport | A2A, ACP | carry MLLANG packets as message body |
| **Runtime state** | **MLLANG** | **THIS LAYER — slot grammar, halt enum, confidence** |

MLLANG sits inside MCP/A2A as payload, inside markdown files as runtime state. Doesn't compete with them.

### Credit / inspiration — RecursiveMAS

**The core idea of MLLANG is inspired by [RecursiveMAS / RecursiveLink](https://github.com/RecursiveMAS/RecursiveMAS) (arXiv 2604.25917).** Full credit to that team — they solved multi-agent collaboration by exchanging **latent vectors** between recursive agent rounds, which is the elegant solution when you control the model weights.

Their constraint: it requires direct activation access (Qwen / Llama / Gemma / DeepSeek self-hosted). Closed APIs like Claude / GPT / Gemini don't expose hidden states, so latent exchange can't reach them.

MLLANG is the **text-surface approximation** of the same goal. Loses the latent-recursion benefit. Gains universal compatibility — runs everywhere RecursiveMAS can't (closed APIs, mixed-vendor loops, paste-based workflows). A team running RecursiveMAS internally can still emit MLLANG packets as the text log of their latent rounds. Orthogonal layers; not competing.

If you can run RecursiveMAS, prefer it. MLLANG exists for the rooms where you can't.

---

## Why MLLANG vs alternatives

| | JSON-RPC | YAML frontmatter | LangGraph state | MLLANG |
|---|----------|------------------|-----------------|--------|
| Format | JSON-RPC envelope | YAML | Python dict | Compact ASCII |
| Single-line | No | No | No | **Yes** |
| Token cost | High | High | High | **50–70% lower** |
| Embed in markdown | No | header only | No | **YES (fenced block)** |
| Human readable | Verbose | Yes | No | **5-min learn** |
| Confidence built-in | No | No | No | **`P:` slot** |
| Halt enum | No | No | No | **9-way native** |
| Multi-agent handoff | Manual | Manual | Framework-locked | **`N:` slot** |

---

## Cross-vendor ratification

MLLANG v0.1 was tested across these LLM families before locking:

| Family | Model | Status |
|--------|-------|--------|
| Anthropic | Claude Sonnet 4.6 / Opus 4.7 | ✅ ratified |
| OpenAI | GPT-5.5 Thinking, Codex (gpt-5.5) | ✅ ratified |
| Google | Gemini Pro web, Gemini Flash CLI | ✅ ratified |
| Google (local) | Gemma-4 26B (AIR backend) | ✅ ratified |
| Google (local) | Gemma-4 4B (local, ~4B params) | ✅ ratified — small-model compactness test PASS |
| DeepSeek | DeepSeek V3 | ✅ ratified (P:0.92, 1 round) |
| Moonshot | Kimi K2.6 | ✅ ratified (P:0.88, 1 round) |
| Alibaba | Qwen 3.6 | ✅ ratified (P:0.85, 1 round) |

Mean ratification confidence: **0.93** (0.95 original 6 vendors + 0.883 Chinese 3-vendor pass). Spec locked 2026-05-19.

Audit trail: [`examples/05_negotiation_trace.jsonl`](examples/05_negotiation_trace.jsonl) (original 6), [`examples/ratification_chinese_2026-05-20.jsonl`](examples/ratification_chinese_2026-05-20.jsonl) (Chinese pass).

The Chinese-family pass converged in **1 round per model** (vs 3 rounds for the original spec-locking pass) because the spec was already locked — each backend only needed to acknowledge and emit a valid packet, not negotiate the grammar.

---

## Repo structure

```
mllang/
├── spec/                  Spec (v0.1 locked + v0.2 draft)
├── parser/                Python reference parser (pure stdlib)
├── examples/              5 generic packet examples + markdown-embedded demo
├── bootstrap/             Role prompts (orchestrator, critic, implementer, synthesizer)
├── conformance/           Test suite — any parser implementation can score against it
├── codex-cli-integration/ Conservative Codex CLI session parser + report wrapper
├── docs/                  GitHub Pages site
├── rfc/                   Quarterly RFC proposals
└── .github/workflows/     CI: conformance test on PR
```

---

## Install

**macOS / Linux** — one command, sets up Claude Code + Codex + mailbox + hooks:

```bash
curl -sL https://raw.githubusercontent.com/jakeliu/mllang/main/install.sh | bash -s -- --my-box=<your-name>
```

**Windows** — PowerShell:

```powershell
$env:MLLANG_MY_BOX="<your-name>"; iwr -useb https://raw.githubusercontent.com/jakeliu/mllang/main/install.ps1 | iex
```

Substitute `<your-name>` with your agent identity (e.g. `alice`, `claude-jake`, `codex-main`). The installer:
- `pipx install mllang-protocol[mcp]` (installs pipx if missing)
- Detects Claude Code (`~/.claude*/`) and/or Codex CLI (`~/.codex/`)
- Drops `/mllang` slash command, hook scripts, bootstrap
- Adds `[mcp_servers.mllang]` + `[[hooks.UserPromptSubmit]]` to Codex `config.toml`
- Appends MLLANG natural-language snippet to Codex `AGENTS.md`
- Sets `MLLANG_MY_BOX` in your shell rc
- Backs up any file it modifies as `.bak-<ts>`

After install, restart both CLIs.

**Use it:**

```bash
mllang-mailbox send <box> "hi"        # any shell
/mllang send <box> hi                 # in Claude Code
send hi to <box>                      # in Codex (natural language)
```

### Just the parser (no client wiring)

```bash
pipx install mllang-protocol           # CLI + library
pipx install 'mllang-protocol[mcp]'    # + MCP server
```

PyPI distribution is `mllang-protocol`; Python import path is `mllang`:

```python
from mllang import Packet, parse, embed_in_markdown, sanitize
```

### Editable / dev install

```bash
git clone https://github.com/jakeliu/mllang.git
cd mllang
pip install -e parser/
```

---

## Documentation

- [Specification (v0.2 locked)](spec/MLLANG_v0.2.locked.md) — adds T:cap, TR:, SIG:, map-form N:
- [Specification (v0.1 locked)](spec/MLLANG_v0.1.locked.md) — base, still valid
- [Quickstart](docs/quickstart.md)
- [Markdown-embedded usage](docs/markdown-embedded.md)
- [Bootstrap — 3-layer setup](docs/bootstrap.md)
- [MCP server](docs/mcp.md)
- [shim-engine — observability](docs/shim.md)
- [Telemetry & privacy](docs/telemetry.md)
- [FAQ](docs/faq.md)
- [Conformance tests](conformance/)
- [RFC process](rfc/README.md)
- [Security policy](.github/SECURITY.md)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Quarterly RFC review windows. Multi-vendor test required for any spec change.

---

## Sister package — `shim-engine`

Same repo, separate PyPI listing. Local-first observability for LLM-agent loops — token / latency / cost / outcome distribution in a JSONL log, aggregated by a small CLI. Works with **any** model. Optional MLLANG awareness for 5x more signal.

```bash
pip install shim-engine               # standalone (any LLM)
pip install 'shim-engine[mllang]'     # auto-extract halt / confidence / agent code from MLLANG responses
pip install 'mllang-protocol[shim]'  # same as above, reverse install order
```

Killer demo:

```text
$ shim-engine-report calls.jsonl
200 packets logged
mean token reduction:  56.8% vs JSON-RPC equivalent  (200/200 packets MLLANG-tagged)
estimated tokens saved: 9,536
p50 latency: 4.32s    p99: 7.92s
mean P: 0.81
halt distribution:     test=pass 62% | <=> 18% | accept 9% | escalate@H 7% | risk!high 4%
model distribution:    gpt-5.5-thinking 42% | claude-opus 32% | gemini-pro 13% | gemma-26b 10% | deepseek-v3 4%
agent distribution:    @G 23% | @X 21% | @K 20% | @M 19% | @C 17%
```

Full guide: [`docs/shim.md`](docs/shim.md) and [`shim/README.md`](shim/README.md).

---

## Claude Code skill — `/mllang`

One-keystroke MLLANG inside Claude Code (Anthropic's official CLI). The skill loads the bootstrap, instruments sub-agent (`Agent` tool) calls via a `PostToolUse` hook, and lets you check live token-savings at any time.

Install:

```bash
curl -sL https://raw.githubusercontent.com/jakeliu/mllang/main/claude-code-skill/install.sh | bash
pip install 'shim-engine[mllang]'    # optional, enables /mllang report
```

Then in Claude Code:

```
/mllang             # load bootstrap, ratify session
/mllang load critic # adopt the critic role's conventions
/mllang report      # token-savings report from sub-agent calls this session
/mllang status      # one-liner summary
/mllang spec        # 5-line MLLANG v0.1 summary
```

The sub-agent log is privacy-redacted (slot SHAPES only, no slot values) and lives at `~/.claude/mllang-shim/session.jsonl`. Full guide: [`claude-code-skill/README.md`](claude-code-skill/README.md).

---

## Codex CLI integration

Conservative Path 1 for Codex CLI. No hooks are installed. The integration parses Codex's persisted session JSONL under `~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl`, records one `shim-engine` row per completed turn, and reports real tokens in/out from Codex `token_count` events.

Install:

```bash
bash codex-cli-integration/install.sh
pip install 'shim-engine[mllang]'    # optional, enables reports
```

Use:

```bash
python3 ~/.codex/mllang-integration/scripts/codex_session_parser.py --latest
bash ~/.codex/mllang-integration/scripts/codex-mllang-report.sh
```

Budget source is tagged honestly: `B-slot` when the final MLLANG packet self-reports `B:{tokens_in=..., tokens_out=..., time=...}`, otherwise `session-token_count`, otherwise `none`. Capture boundary is top-level Codex turn, not sub-agent. Full guide: [`codex-cli-integration/README.md`](codex-cli-integration/README.md).

---

## MCP server (Claude Desktop / Cline / Zed)

```bash
pip install 'mllang-protocol[mcp]'
mllang-mcp-server
```

Or drop into `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "mllang": { "command": "mllang-mcp-server" }
  }
}
```

Exposes 7 tools (`mllang_parse` / `mllang_compose` / `mllang_validate` / `mllang_embed_in_markdown` / `mllang_extract_summary` / `mllang_sanitize` / `mllang_spec`). End-to-end test in `conformance/test_mcp_server.py` drives every tool over real MCP stdio. Full guide: [`docs/mcp.md`](docs/mcp.md).

---

## Telemetry & privacy

MLLANG ships with a built-in `sanitize()` function. Telemetry is **opt-in only**, **off by default**, and the library never auto-enables it.

```bash
# default — nothing sent
export MLLANG_TELEMETRY=off

# opt-in levels:
export MLLANG_TELEMETRY=shape        # slot presence + halt + confidence (recommended)
export MLLANG_TELEMETRY=structured   # add map keys + verb names + counts
export MLLANG_TELEMETRY=full         # add redacted values (research consent only)
```

```python
from mllang import sanitize, sanitize_to_json

payload = sanitize(packet)         # None unless env var set
line = sanitize_to_json(packet)    # None or one-line JSON
```

Slot **shapes** are public; slot **values** stay private. Thread ids are hashed (`<I:hash:<sha256_12>>`), file paths and tool args are never logged, and a leak-detector refuses payloads that still contain emails / paths / API-key patterns / long quoted strings.

Full slot-by-slot rules and before/after examples: [`docs/telemetry.md`](docs/telemetry.md). Disclosure policy and IP-leak bug bounty: [`.github/SECURITY.md`](.github/SECURITY.md).

---

## Status

- v0.1 spec: **LOCKED** 2026-05-19
- v0.2 spec: **LOCKED** 2026-05-24 (4 of 5 jury approve; RFC 0001 ratified)
- Parser: pure Python 3, no external deps
- Conformance: 166 v0.1 packets + 14 v0.2 packets (T:cap, TR:, SIG:, map-N:) — all green at lock
- Telemetry: opt-in `sanitize()` with 4 levels + leak-detector defense

---

## License

Apache 2.0. See [LICENSE](LICENSE).

---

## Citation

If you use MLLANG in research or production, please cite:

```
MLLANG: Markdown Language for AI Agents (2026)
github.com/jakeliu/mllang
```
