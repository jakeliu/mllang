---
layout: default
title: MCP server
---

# MLLANG MCP server

The library ships an optional Model Context Protocol server so any MCP-aware client (Claude Desktop, Cline, Zed, custom hosts) can use MLLANG as a tool.

---

## Install

```bash
pip install 'mllang-protocol[mcp]'
```

The `[mcp]` extra pulls in the `mcp` SDK. Core install (`pip install mllang-protocol`) stays pure stdlib.

---

## Run

Stdio transport (what Claude Desktop / most clients expect):

```bash
mllang-mcp-server
```

That's it. The console script is registered by the package, so it's on PATH after install.

To run from source without installing:

```bash
python -m mllang.mcp_server
```

---

## Claude Desktop config

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) / `%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "mllang": {
      "command": "mllang-mcp-server"
    }
  }
}
```

Restart Claude Desktop. The `mllang` tools appear in the tool list. Ask Claude to "parse this MLLANG packet" or "embed it in a markdown file" — it'll route through the server.

If `mllang-mcp-server` isn't on the PATH that Claude Desktop sees (common on macOS with pyenv / Homebrew Python), use the absolute path:

```bash
which mllang-mcp-server
```

…then paste that path in place of `"mllang-mcp-server"` in the config.

---

## Tools exposed

| Tool | Description |
|------|-------------|
| `mllang_parse` | Parse MLLANG packet text into a structured dict |
| `mllang_compose` | Build MLLANG text from a packet dict |
| `mllang_validate` | Return list of validation errors (empty = valid) |
| `mllang_embed_in_markdown` | Wrap packet in markdown — `summary` / `verbose` / `packet_only` modes |
| `mllang_extract_summary` | Pull `(summary, packet)` out of a summary-mode markdown file |
| `mllang_sanitize` | Telemetry redaction — `off` / `shape` / `structured` / `full` |
| `mllang_spec` | Return the locked v0.1 spec as text (for LLMs that need spec context) |

---

## End-to-end test

```bash
pip install 'mllang-protocol[mcp]'
python conformance/test_mcp_server.py
```

Spawns the server as a subprocess, drives every tool over real MCP stdio, asserts responses round-trip cleanly. 22 assertions. CI runs this on every PR.

---

## Use from another Python program

You can also call the server tools directly via the MCP client SDK (no Claude Desktop needed):

```python
import asyncio
import sys
from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

async def main():
    params = StdioServerParameters(command="mllang-mcp-server")
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            r = await session.call_tool(
                "mllang_parse",
                {"text": "V:0.1.r1; I:demo; G:{a=1}; S:{b=2}; N:@K -> verify; H:accept; P:0.85;"},
            )
            print(r.structuredContent["result"])

asyncio.run(main())
```

---

## Why an MCP server

MLLANG is a text-surface convention; it doesn't *need* a server to be useful. But putting the parser behind an MCP server gets you:

- **Drop-in for Claude Desktop / Cline / Zed users** — no Python required on the user's side, just a config line.
- **Cross-language access** — any MCP client (TypeScript, Go, Rust, etc.) can drive the tools without a language binding.
- **End-to-end sanity check** — the conformance test exercises the same path real LLMs use, so a regression in transport handling is caught.

---

## Roadmap

- Streaming responses for very large packet lists.
- HTTP transport mode (currently stdio only).
- Optional dependency `[mcp-streaming]` once the SDK's streaming API stabilizes.
