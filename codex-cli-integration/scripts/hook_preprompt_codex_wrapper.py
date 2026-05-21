#!/usr/bin/env python3
"""Codex adapter for the shared mailbox preprompt hook.

The shared `hook_preprompt.py` is kept verbatim for Claude Code parity.
Codex uses a different model-visible hook output shape: Claude's
`systemMessage` is recorded only as a warning, while Codex injects
`hookSpecificOutput.additionalContext` into the next model turn.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def _passthrough() -> None:
    sys.stdout.write(json.dumps({"continue": True, "suppressOutput": True}) + "\n")


def main() -> None:
    payload = sys.stdin.read()
    hook = Path(__file__).with_name("hook_preprompt.py")
    if not hook.exists():
        _passthrough()
        return

    try:
        proc = subprocess.run(
            [sys.executable, str(hook)],
            input=payload,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=5,
            check=False,
        )
        data = json.loads(proc.stdout or "{}")
    except Exception:
        _passthrough()
        return

    reminder = data.get("systemMessage")
    if not reminder:
        _passthrough()
        return

    sys.stdout.write(
        json.dumps(
            {
                "continue": True,
                "suppressOutput": True,
                "hookSpecificOutput": {
                    "hookEventName": "UserPromptSubmit",
                    "additionalContext": reminder,
                },
            }
        )
        + "\n"
    )


if __name__ == "__main__":
    main()
