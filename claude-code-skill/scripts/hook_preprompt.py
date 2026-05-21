#!/usr/bin/env python3
"""UserPromptSubmit + PreToolUse hook — auto-surface unread mailbox messages.

Fires on every user prompt AND before every tool call in Claude Code (or
Codex via the wrapper). Polls the active session's mailbox (default box
=`claude`, override via $MLLANG_MY_BOX) and surfaces ONLY messages whose
msg_id has not been seen yet this session. Tracks seen IDs in
~/.mllang-mailbox/.seen/<box>-<pid-ancestor>.json so PreToolUse firing 10x
per turn doesn't re-surface the same unread 10x.

Output contract:
- stdout: JSON {"continue": true, "suppressOutput": true [, "systemMessage": ...]}
- Pass-through on any error.

Fail-soft on every I/O step. Never blocks the user.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

DEFAULT_BOX = os.environ.get("MLLANG_MY_BOX", "claude")
MAILBOX_ROOT = Path(os.environ.get("MLLANG_MAILBOX_ROOT", str(Path.home() / ".mllang-mailbox")))
SEEN_DIR = MAILBOX_ROOT / ".seen"


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


def _seen_path(box: str, session_id: str = "") -> Path:
    """Per-session seen-ids file. session_id from hook payload preferred; PPID fallback."""
    key = session_id or str(os.getppid())
    return SEEN_DIR / f"{box}-{key}.json"


def _load_seen(box: str, session_id: str = "") -> set:
    try:
        return set(json.loads(_seen_path(box, session_id).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return set()


def _save_seen(box: str, seen: set, session_id: str = "") -> None:
    try:
        SEEN_DIR.mkdir(parents=True, exist_ok=True)
        _seen_path(box, session_id).write_text(json.dumps(sorted(seen)), encoding="utf-8")
    except OSError:
        pass


def main() -> None:
    try:
        # Read hook payload; extract session_id if Claude Code / Codex passed one.
        session_id = ""
        try:
            raw = sys.stdin.read()
            if raw.strip():
                payload = json.loads(raw)
                session_id = str(payload.get("session_id", "") or "")
        except Exception:
            pass

        box = DEFAULT_BOX
        unread = _read_unread(box)
        if not unread:
            _emit_passthrough()
            return

        seen = _load_seen(box, session_id)
        new = [m for m in unread if m.get("msg_id") not in seen]
        if not new:
            # Same unread still sitting there; already surfaced this session.
            _emit_passthrough()
            return

        n = len(new)
        froms = sorted({msg.get("from", "?") for msg in new})
        body = f"📬 {n} new from {', '.join(froms)}"

        # Record everything we just surfaced so we don't repeat.
        for m in new:
            mid = m.get("msg_id")
            if mid:
                seen.add(mid)
        _save_seen(box, seen, session_id)

        _emit_passthrough(body)
    except Exception:
        _emit_passthrough()


if __name__ == "__main__":
    main()
