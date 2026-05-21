MLLANG mailbox + protocol command. Parse `$ARGUMENTS` and execute one of:

## `/mllang send <box> <message...>`

```bash
mllang-mailbox send <box> "<message>"
```

Reply ONE LINE: `Sent to <box>. msg_id=<first 8 chars>`. Skip the JSON dump.

## `/mllang receive [<box>]` (aliases: `check`, `read`, `inbox`)

```bash
mllang-mailbox check [<box>]
```

Reply ONE LINE: `<N> mail from <senders>` if N>0; `Empty mailbox` if N==0. Skip JSON dump unless user asks for specific msg_id.

## `/mllang status`

```bash
mllang-mailbox status
```

Show only box names with unread > 0.

## `/mllang load` (no args)

Read `~/.claude/skills/mllang/bootstrap.md` and emit acknowledgment packet.

## `/mllang load <role>`

`<role>` is one of: `orchestrator`, `critic`, `implementer`, `synthesizer`. Read `~/.claude/skills/mllang/roles/<role>.md` and adopt the role.

## `/mllang spec`

Read `~/.claude/skills/mllang/spec-summary.md` — 5-line spec summary.

## `/mllang report`

```bash
bash ~/.claude/skills/mllang/scripts/report.sh
```

Shows token-savings report from the shim-engine session log.

## Notes

- `mllang-mailbox` resolves to `/Users/jake/.local/bin/mllang-mailbox`.
- DO NOT pass `--from` (auto-fills from `MLLANG_MY_BOX` env).
- DO NOT pass `--subject` unless user supplied one explicitly.
- If `MLLANG_MY_BOX` is empty, sends go as `from=me`. Suggest user set it in shell rc once.

Parse `$ARGUMENTS` for subcommand. Default to `/mllang load` when no args.
