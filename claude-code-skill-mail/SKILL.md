---
name: mail
description: Check inbox or send mail via mllang-mailbox. Trigger on /mail, /mail send <box> <text>, "check mail", "send mail to <box>", "mail <box> <text>".
allowed-tools: Bash
---

# Mail — one-stop mailbox skill

User-facing slash commands:

## `/mail` — check this session's inbox

When invoked with NO args, run:

```bash
mllang-mailbox check
```

Reply ONE LINE only:
- `N mail from <senders>` if N > 0
- `Empty mailbox` if N == 0

DO NOT dump JSON. DO NOT list bodies unless the user explicitly asks for a specific msg_id.

## `/mail send <box> <message>`

Or natural language: "mail <box> <msg>", "send mail to <box> <msg>".

Run:

```bash
mllang-mailbox send <box> "<message>"
```

Reply ONE LINE: `Sent to <box>. msg_id=<first 8 chars>`.

Do NOT pass `--from` (auto-fills from `MLLANG_MY_BOX`). Do NOT pass `--subject` unless user supplied one.

## `/mail check <box>`

Read a different box than the session default.

```bash
mllang-mailbox check <box>
```

Same one-line reply as `/mail`.

## Notes for the assistant

- `mllang-mailbox` resolves to `/Users/jake/.local/bin/mllang-mailbox`.
- If env `MLLANG_MY_BOX` is not set, sends will go out with `from_=me` and checks will read box `me`. That's usually wrong — tell the user to set `MLLANG_MY_BOX=<their-name>` in their shell rc once.
- Never show the full message JSON unless explicitly asked. The point of this skill is one-keystroke triage.
