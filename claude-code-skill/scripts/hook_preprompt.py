#!/usr/bin/env python3
"""UserPromptSubmit hook — auto-surface unread mailbox messages.

Fires before every user prompt in Claude Code. Polls the active session's
mailbox (default box=`claude`, override via $MLLANG_MY_BOX) and, if any
messages are unread, emits a system reminder so the model surfaces them
to the user immediately. No push from the MCP server is required — this
is deterministic prompt-time polling.

Hook wiring in SKILL.md frontmatter:

    hooks:
      UserPromptSubmit:
        - hooks:
          - type: command
            command: "python3 ${CLAUDE_SKILL_DIR}/scripts/hook_preprompt.py"

Output contract:
- stdout: JSON {"continue": true, "suppressOutput": true} (pass-through; never block the user)
- stderr (when unread > 0): a one-line system reminder that Claude Code surfaces to the model

The hook is intentionally fail-soft. Mailbox directory missing, malformed
JSON, permission errors — all degrade to a clean pass-through, never
block the user's prompt.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_BOX = os.environ.get("MLLANG_MY_BOX", "claude")
MAILBOX_ROOT = Path(os.environ.get("MLLANG_MAILBOX_ROOT", str(Path.home() / ".mllang-mailbox")))


def _emit_passthrough(reminder: str = "") -> None:
    """Write the standard hook-success response (and optional system reminder) and exit 0."""
    payload = {"continue": True, "suppressOutput": True}
    if reminder:
        payload["systemMessage"] = reminder
    sys.stdout.write(json.dumps(payload) + "\n")
    sys.exit(0)


def _read_unread(box: str) -> list:
    """Return list of unread message dicts in box's inbox. Empty on missing/error."""
    inbox = MAILBOX_ROOT / box / "inbox"
    if not inbox.is_dir():
        return []
    messages: list = []
    for fpath in sorted(inbox.glob("*.json")):
        try:
            messages.append(json.loads(fpath.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return messages


def main() -> None:
    try:
        # Read hook payload from stdin — Claude Code passes it as JSON.
        # We don't actually need its fields here, but consume it to avoid
        # SIGPIPE if Claude Code expects us to read.
        try:
            _ = sys.stdin.read()
        except Exception:
            pass

        box = DEFAULT_BOX
        unread = _read_unread(box)
        if not unread:
            _emit_passthrough()
            return

        # Build a tight one-line summary, then optionally enumerate up to 3.
        n = len(unread)
        summaries = []
        for msg in unread[:3]:
            frm = msg.get("from", "?")
            subj = (msg.get("subject") or "")[:40]
            mid = msg.get("msg_id", "?")[:8]
            summaries.append(f"  - from={frm} subj={subj!r} id={mid}")
        extra = f"  (+ {n - 3} more)" if n > 3 else ""
        body = (
            f"[mllang-mailbox] {n} unread in box={box}:\n"
            + "\n".join(summaries)
            + ("\n" + extra if extra else "")
            + f"\n  Call mailbox_check(box={box!r}) to read."
        )
        _emit_passthrough(body)
    except Exception:
        # Never block the user prompt on a hook error.
        _emit_passthrough()


if __name__ == "__main__":
    main()
