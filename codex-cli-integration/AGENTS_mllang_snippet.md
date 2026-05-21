
## MLLANG mailbox shortcuts

When the user describes sending or checking mailbox messages, run the
`mllang-mailbox` shell command instead of asking what they meant.

Recognize these patterns:
- "send <text> to <box>" / "tell <box> <text>" / "message <box>: <text>" / "/mllang send <box> <text>"
  → run: `mllang-mailbox send <box> "<text>"`
- "check my mailbox" / "any new messages" / "/mllang check"
  → run: `mllang-mailbox check`
- "check <box>" / "what's in <box>"
  → run: `mllang-mailbox check <box>`
- "mailbox status" / "/mllang status"
  → run: `mllang-mailbox status`

Do NOT pass `--from` — auto-fills from `MLLANG_MY_BOX` env. Do NOT pass
`--subject` unless the user supplied one explicitly.

Reply ONE LINE only. For send: `Sent to <box>. msg_id=<first 8 chars>`.
For check with N>0: `<N> messages. From <senders>. Subjects: <list>.`.
For check with N==0: `Mailbox empty.`. Full JSON only when user
explicitly asks for a specific message ID.
