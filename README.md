# MLLANG — Markdown Language for AI Agents

[![PyPI](https://img.shields.io/pypi/v/mllang-protocol.svg)](https://pypi.org/project/mllang-protocol/)
[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Spec: v0.1 locked](https://img.shields.io/badge/spec-v0.1_locked-green.svg)](spec/MLLANG_v0.1.locked.md)
[![Vendors: 6+](https://img.shields.io/badge/vendors-6%2B_ratified-orange.svg)](spec/MLLANG_v0.1.locked.md)
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

Mean ratification confidence: **0.95**. Spec locked 2026-05-19.

Audit trail: [`examples/05_negotiation_trace.jsonl`](examples/05_negotiation_trace.jsonl) (sanitized).

---

## Repo structure

```
mllang/
├── spec/                  Spec (v0.1 locked + v0.2 draft)
├── parser/                Python reference parser (pure stdlib)
├── examples/              5 generic packet examples + markdown-embedded demo
├── bootstrap/             Role prompts (orchestrator, critic, implementer, synthesizer)
├── conformance/           Test suite — any parser implementation can score against it
├── docs/                  GitHub Pages site
├── rfc/                   Quarterly RFC proposals
└── .github/workflows/     CI: conformance test on PR
```

---

## Install

```bash
pip install mllang-protocol
```

PyPI distribution name is `mllang-protocol` (the bare `mllang` name was already held by an unrelated 2021 ML library on PyPI). The Python import path is still `mllang`:

```python
from mllang import Packet, parse, embed_in_markdown, sanitize
```

Editable install from the repo also works:

```bash
git clone https://github.com/jakeliu/mllang.git
cd mllang
pip install -e parser/
```

---

## Documentation

- [Specification (v0.1 locked)](spec/MLLANG_v0.1.locked.md)
- [Quickstart](docs/quickstart.md)
- [Markdown-embedded usage](docs/markdown-embedded.md)
- [MCP server](docs/mcp.md)
- [Telemetry & privacy](docs/telemetry.md)
- [FAQ](docs/faq.md)
- [Conformance tests](conformance/)
- [RFC process](rfc/README.md)
- [Security policy](.github/SECURITY.md)

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Quarterly RFC review windows. Multi-vendor test required for any spec change.

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
- v0.2 spec: draft, RFC window open
- Parser: pure Python 3, no external deps
- Conformance: 160-packet test suite (parse / halt / roundtrip / markdown extract / sanitize / embed)
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
