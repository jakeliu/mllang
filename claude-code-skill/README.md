# MLLANG Claude Code skill

A Claude Code skill that loads MLLANG v0.1 into the current session and (when `shim-engine` is installed) auto-logs sub-agent calls so you can run `/mllang report` to see live token-savings.

## Install

```bash
curl -sL https://raw.githubusercontent.com/jakeliu/mllang/main/claude-code-skill/install.sh | bash
```

Or, from a local clone:

```bash
git clone https://github.com/jakeliu/mllang.git
cd mllang
bash claude-code-skill/install.sh
```

The installer copies into `~/.claude/skills/mllang/`. If you have an existing install at that path, it's backed up with a timestamp.

**Optional but recommended — install shim-engine** for the live savings report:

```bash
pip install 'shim-engine[mllang]'
```

Without `shim-engine`, the skill still loads the bootstrap. The `/mllang report` and `/mllang status` commands print an install hint instead.

## Use

In Claude Code, type:

| Command | What it does |
|---------|--------------|
| `/mllang` | Load bootstrap, emit acknowledgment packet, start emitting MLLANG for the session |
| `/mllang load <role>` | Adopt orchestrator / critic / implementer / synthesizer role conventions |
| `/mllang report` | Run `shim-engine-report` on the session's MLLANG sub-agent log |
| `/mllang status` | One-liner: how many sub-agent calls logged, tokens saved, $$ saved |
| `/mllang spec` | 5-line summary of MLLANG v0.1 (slots / operators / halt enum) |
| `/mllang ratify` | Emit a packet + verify it parses + validates clean |
| `/mllang install-mcp` | Print Claude Desktop config snippet for the MLLANG MCP server |

## How the sub-agent logging works

The skill ships a `PostToolUse` hook (configured in `SKILL.md` frontmatter) that fires after every Claude Code `Agent` (sub-agent) call. The hook:

1. Reads the JSON payload Claude Code passes on stdin.
2. Pulls the sub-agent's prompt + final response text.
3. Pipes the response through `shim_engine.observe(..., parser="mllang")`.
4. Writes a privacy-redacted record to `~/.claude/mllang-shim/session.jsonl`.

What gets recorded (slot SHAPES only — no slot values):

| Field | Source |
|-------|--------|
| `halt` | `H:` slot of any MLLANG packet in the sub-agent's response |
| `confidence` | `P:` slot |
| `agent_code` | `@<X>` part of `N:` slot |
| `slots_present` | Uppercase slot keys actually populated |
| `tokens_saved_est` | Computed: JSON-RPC envelope size minus MLLANG packet size |
| `tags.subagent_type` | Which Claude Code subagent type was spawned |

Goal text, state values, evidence, file paths, and tool-call args are **never** recorded. Same posture as `mllang.sanitize()`.

## Disabling the hook

If you want the skill to load the bootstrap but NOT log sub-agent calls, edit `~/.claude/skills/mllang/SKILL.md` and comment out the `hooks:` block in the frontmatter, then restart Claude Code.

## Uninstall

```bash
rm -rf ~/.claude/skills/mllang
rm -rf ~/.claude/mllang-shim        # optional — removes the session log
```

## Limitations

- The hook captures the sub-agent's **final response text**, not internal sub-agent tool calls or token-usage breakdown. Claude Code does not expose those to PostToolUse hooks today.
- `tokens_in` / `tokens_out` / `latency_s` in the recorded payload are `0` because Claude Code's PostToolUse JSON doesn't include the sub-agent's usage stats. The `tokens_saved_est` field (vs JSON-RPC envelope) is still meaningful — it measures the MLLANG packet's compactness directly, not the wall-clock cost.
- The skill assumes you want MLLANG packets in your sub-agent loops. If you don't ratify the sub-agents to speak MLLANG, the hook will log empty records (`has_mllang_packet: false`) and the report will mostly show `(no MLLANG packets detected)`.

## License

Apache 2.0. Source: github.com/jakeliu/mllang/tree/main/claude-code-skill.
