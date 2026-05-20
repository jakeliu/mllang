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


def _extract_budget(response_text: str) -> tuple:
    """Pull (tokens_in, tokens_out, latency_s) from the B: slot of an
    MLLANG packet in the sub-agent's response, if present.

    Path 1 of the sub-agent usage capture. Sub-agents are instructed by
    the MLLANG bootstrap to include a B: slot in their final packet:

        B:{tokens_in=N, tokens_out=N, time=Ns, money=N}

    Falls back to (0, 0, 0.0) when the packet is absent, lacks B:,
    or the values are unparseable. Path 2 (transcript parsing) is
    briefed in ai_language/mllang_launch/PATH2_TRANSCRIPT_PARSING.md.
    """
    if not response_text:
        return 0, 0, 0.0
    try:
        from mllang import parse, extract_from_markdown
    except ImportError:
        return 0, 0, 0.0

    p = None
    if "```mllang" in response_text:
        try:
            packets = extract_from_markdown(response_text)
            if packets:
                p = packets[0]
        except Exception:
            p = None
    if p is None:
        import re

        m = re.search(r"V:\s*\d+\.\d+\.r\d+\s*;", response_text)
        if m:
            try:
                p = parse(response_text[m.start():])
            except Exception:
                p = None

    if p is None or not p.budget:
        return 0, 0, 0.0

    def _intish(v: str) -> int:
        s = str(v).strip().rstrip("s").rstrip()
        try:
            return int(float(s))
        except (TypeError, ValueError):
            return 0

    def _floatish(v: str) -> float:
        s = str(v).strip().rstrip("s").rstrip()
        try:
            return float(s)
        except (TypeError, ValueError):
            return 0.0

    return (
        _intish(p.budget.get("tokens_in", 0)),
        _intish(p.budget.get("tokens_out", 0)),
        _floatish(p.budget.get("time", 0)),
    )


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

    # Path 1 — sub-agent self-reports its usage via the B: slot of its
    # final MLLANG packet. If present, use those values. Path 2 (parsing
    # the transcript JSONL for ground-truth usage) is briefed for later.
    tokens_in, tokens_out, latency_s = _extract_budget(response_text)

    os.makedirs(LOG_DIR, exist_ok=True)
    r = Recorder(path=LOG_PATH, parser="mllang")

    try:
        r.observe(
            response=response_text,
            model=f"claude-code-subagent:{subagent_type}",
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_s=latency_s,
            tags={
                "source": "claude-code",
                "tool": "Agent",
                "subagent_type": subagent_type,
                "session_id": payload.get("session_id", ""),
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "budget_source": "B-slot" if tokens_in or tokens_out else "none",
            },
        )
    except Exception:
        # Never block the user's session on a logging failure.
        pass

    _emit_passthrough()


if __name__ == "__main__":
    main()
