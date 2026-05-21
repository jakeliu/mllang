---
name: mllang
description: Load MLLANG v0.1 protocol so this Claude Code session emits compact agent-state packets, and check live how many tokens / dollars MLLANG saved this session via shim-engine. Invoke when the user types /mllang or asks about MLLANG packets, agent-state protocol, or token-savings reports.
trigger: /mllang
allowed-tools: Bash, Read
hooks:
  PostToolUse:
    - matcher: "Agent"
      hooks:
        - type: command
          command: "python3 ${CLAUDE_SKILL_DIR}/scripts/hook_postagent.py"
  UserPromptSubmit:
    - hooks:
        - type: command
          command: "python3 ${CLAUDE_SKILL_DIR}/scripts/hook_preprompt.py"
  PreToolUse:
    - hooks:
        - type: command
          command: "python3 ${CLAUDE_SKILL_DIR}/scripts/hook_preprompt.py"
---

# MLLANG skill

This skill loads MLLANG v0.1 into the current Claude Code session and instruments sub-agent calls (`Agent` tool) so every sub-agent response that contains an MLLANG packet is logged for after-the-fact savings reports.

## Sub-commands

Parse the user's invocation. Supported args:

### `/mllang` (no args) or `/mllang load`

1. Read `${CLAUDE_SKILL_DIR}/bootstrap.md`.
2. State concisely that the MLLANG v0.1 spec is now loaded for this session, and any agent-state handoffs in your responses will follow the canonical slot order (V I G S D E U R T F Y B N H P A; required V G S N H).
3. Emit ONE acknowledgment packet, substituting your honest confidence float (use 0.85-0.92 range; never 1.00):

```
V:0.1.r1; I:cc-session-ack; G:{task=acknowledge_spec};
S:{spec_version=0.1, slots_understood=16, ops_understood=19, halt_enum=9-way};
D:[ready_to_route]; N:@H -> proceed; H:<=>; P:<honest float>;
EN: MLLANG v0.1 spec acknowledged for this Claude Code session.
```

### `/mllang send <box> <message>` — also fires for natural language

Trigger this when the user types `/mllang send codex-two hi` OR uses natural language like "send X to <box>", "tell <box> Y", "message <box> Z", "mailbox send X to Y", etc.

Run via Bash (`mllang-mailbox` resolves to `/Users/jake/.local/bin/mllang-mailbox`):

```bash
mllang-mailbox send <box> "<message>"
```

Do NOT pass `--from` — it auto-fills from the user's `MLLANG_MY_BOX` env. Do NOT pass `--subject` unless the user supplied one explicitly.

After the command runs, show the user only the `msg_id` and the destination box. Skip the full JSON. One-liner like: `Sent to codex-two. msg_id=abc12345`.

### `/mllang receive [<box>]` or `/mllang check [<box>]` — read inbox

Trigger on `/mllang receive`, `/mllang check`, `/mllang read`, "check my mailbox", "any new messages", "what's in inbox", etc.

Run via Bash:

```bash
mllang-mailbox check <box>     # if user specified a box
mllang-mailbox check           # if not — defaults to MLLANG_MY_BOX
```

Summarize the returned JSON: `N messages. From <senders>. Subjects: <list>.` Show body text only if the user asked to read a specific message.

### `/mllang load <role>`

`<role>` is one of: `orchestrator`, `critic`, `implementer`, `synthesizer`. Read `${CLAUDE_SKILL_DIR}/roles/<role>.md` and adopt that role's output conventions for subsequent messages. If the role file is missing, tell the user to re-run the install script: `bash ${CLAUDE_SKILL_DIR}/install.sh`.

### `/mllang report`

Run the report. Use Bash:

```bash
${CLAUDE_SKILL_DIR}/scripts/report.sh
```

This wraps `shim-engine-report` on the session log at `~/.claude/mllang-shim/session.jsonl`. If `shim-engine` is not on PATH, the script prints the install command (`pip install 'shim-engine[mllang]'`) and exits cleanly.

If the log file does not exist, tell the user: "No MLLANG calls recorded yet this session. The PostToolUse hook starts logging from the first `Agent` sub-agent call that returns an MLLANG packet in its response."

### `/mllang status`

Quick one-liner. Run:

```bash
${CLAUDE_SKILL_DIR}/scripts/report.sh --json 2>/dev/null
```

Parse the JSON output (fields: `records`, `with_mllang_packet`, `mean_reduction_pct`, `tokens_saved_total`, `estimated_dollars_saved`) and emit one sentence:

> Logged N calls (M with MLLANG packets), mean reduction X%, ~Y tokens saved (~$Z at $5/M).

If `records == 0`: "No MLLANG-tagged calls recorded yet this session."

### `/mllang spec`

Read `${CLAUDE_SKILL_DIR}/spec-summary.md` and summarize in 5 lines max: 16 slots, 19 operators, 9-way halt enum, required slots, the EN: dual-channel rule.

### `/mllang ratify`

Emit one valid MLLANG packet acknowledging the spec. Then run:

```bash
echo "<the packet you just emitted>" | python3 -c "from mllang import parse, validate; import sys; print(validate(parse(sys.stdin.read())))"
```

Empty list output = ratified. Non-empty list = packet has errors; re-emit with the errors corrected.

### `/mllang install-mcp`

Print the Claude Desktop config snippet for the MLLANG MCP server (so the user can wire `mllang-mcp-server` into Claude Desktop alongside this Claude Code skill):

```json
{
  "mcpServers": {
    "mllang": { "command": "mllang-mcp-server" }
  }
}
```

Tell the user this is for Claude Desktop, not Claude Code, and that they need `pip install 'mllang-protocol[mcp]'` first.

## Honest-confidence rule

Never emit `P:1.00` on any packet. Real confidence lives in `0.70-0.95`. Use the lower end when uncertain; the upper end only when the packet exactly mirrors a canonical example.

## Markdown-embed pattern

When writing markdown for downstream agents (AGENTS.md, llms.txt, runtime-state docs), use the **summary+packet** pattern:

````markdown
# Optional title

Workflow: <one line: what, gate, next step>.

```mllang
V:0.1.r1; I:<thread>; G:{...}; S:{...}; N:@<agent> -> <verb>;
H:<halt>; P:<float>;
EN: <one-sentence English shadow>.
```
````

Do NOT duplicate the packet content in long prose above the block. The `EN:` line inside the packet is the human-skim channel. Long prose only for human-authored docs (PR descriptions, design notes).

## Privacy

The PostToolUse hook records sub-agent calls to `~/.claude/mllang-shim/session.jsonl`. Logging uses `shim_engine.observe(..., parser="mllang")`, which extracts slot SHAPES (halt, confidence, agent code, slots present) — NOT slot values. Goal text, state values, evidence, file paths, and tool args are never logged. The same posture as `mllang.sanitize()`.

If the user wants to disable hook logging: comment out the `hooks:` block in `~/.claude/skills/mllang/SKILL.md`.
