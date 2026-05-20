#!/usr/bin/env python3
"""PostToolUse hook for Claude Code Agent (sub-agent) calls.

Reads the hook JSON from stdin, extracts the sub-agent's prompt and final
response, and feeds them through shim_engine.observe() so the user can
see live token-savings via `/mllang report`.

Wiring (via SKILL.md hooks frontmatter):
    PostToolUse:
      - matcher: "Agent"
        hooks:
          - type: command
            command: "python3 ${CLAUDE_SKILL_DIR}/scripts/hook_postagent.py"

Privacy posture:
- Records slot SHAPES via parser="mllang" (halt, confidence, agent_code,
  slots_present, tokens_saved_est). Slot VALUES (goal text, state values,
  evidence, file paths, tool args) are NEVER logged. Defense in depth
  via shim_engine's reject_leaks=True is left enabled.
- If shim_engine is not installed, this hook is a silent no-op. Failing
  silently is the right behavior — the user's primary Claude Code work
  must not be blocked by a missing optional observability dependency.
"""

from __future__ import annotations

import json
import os
import sys
import time

LOG_DIR = os.path.expanduser("~/.claude/mllang-shim")
LOG_PATH = os.path.join(LOG_DIR, "session.jsonl")


def _emit_passthrough() -> None:
    """Write the standard hook-success response and exit 0."""
    sys.stdout.write('{"continue": true, "suppressOutput": true}\n')
    sys.exit(0)


def main() -> None:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        _emit_passthrough()
        return

    if payload.get("tool_name") != "Agent":
        _emit_passthrough()
        return

    try:
        from shim_engine import Recorder
    except ImportError:
        _emit_passthrough()
        return

    tool_input = payload.get("tool_input") or {}
    tool_output = payload.get("tool_output") or {}

    response_text = ""
    if isinstance(tool_output, dict):
        response_text = (
            tool_output.get("content")
            or tool_output.get("text")
            or ""
        )
    if not isinstance(response_text, str):
        try:
            response_text = json.dumps(response_text)
        except Exception:
            response_text = str(response_text)

    subagent_type = tool_input.get("agent") or tool_input.get("subagent_type") or "unknown"

    os.makedirs(LOG_DIR, exist_ok=True)
    r = Recorder(path=LOG_PATH, parser="mllang")

    try:
        r.observe(
            response=response_text,
            model=f"claude-code-subagent:{subagent_type}",
            tokens_in=0,            # not exposed by hook payload
            tokens_out=0,            # not exposed by hook payload
            latency_s=0.0,           # not exposed by hook payload
            tags={
                "source": "claude-code",
                "tool": "Agent",
                "subagent_type": subagent_type,
                "session_id": payload.get("session_id", ""),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            },
        )
    except Exception:
        # Never block the user's session on a logging failure.
        pass

    _emit_passthrough()


if __name__ == "__main__":
    main()
