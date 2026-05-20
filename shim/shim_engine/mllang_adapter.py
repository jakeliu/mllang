"""Optional MLLANG awareness for shim-engine.

When `mllang-protocol` is installed (via `pip install 'shim-engine[mllang]'`),
shim-engine extracts structured signals from MLLANG packets present in LLM
responses. When MLLANG is not installed, this module degrades to no-op —
shim-engine still works fine as a generic LLM observability layer.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

try:
    from mllang import Packet, parse, compose, extract_from_markdown  # type: ignore

    _HAVE_MLLANG = True
except ImportError:  # pragma: no cover
    _HAVE_MLLANG = False
    Packet = None  # type: ignore[assignment]


_BARE_PACKET_RE = re.compile(r"V:\s*\d+\.\d+\.r\d+\s*;", re.MULTILINE)


def mllang_available() -> bool:
    """True when mllang-protocol is installed in the current environment."""
    return _HAVE_MLLANG


def _build_json_rpc_envelope(p: Any) -> str:
    """Build a JSON-RPC envelope with the same content. Baseline for reduction comparison."""
    body: Dict[str, Any] = {
        "jsonrpc": "2.0",
        "method": "agent_state",
        "params": {
            "version": p.version,
            "thread_id": p.thread_id,
            "goal": p.goal,
            "state": p.state,
            "decisions": p.decisions,
            "evidence": p.evidence,
            "unknowns": p.unknowns,
            "risks": p.risks,
            "test": p.test,
            "files": p.files,
            "tool_calls": p.tool_calls,
            "next_agent": p.next_agent,
            "halt": p.halt,
            "confidence": p.confidence,
            "assumptions": p.assumptions,
            "en_shadow": p.en_shadow,
        },
    }
    body["params"] = {
        k: v for k, v in body["params"].items() if v not in (None, "", [], {}, 0, 0.0)
    }
    return json.dumps(body, ensure_ascii=False)


def _agent_code(next_agent: str) -> str:
    if not next_agent:
        return ""
    m = re.search(r"@[CXKGMH?]", next_agent)
    return m.group(0) if m else ""


def _slots_present(p: Any) -> list:
    """Return uppercase slot keys actually populated on the packet."""
    out = []
    if p.version:
        out.append("V")
    if p.thread_id:
        out.append("I")
    if p.goal:
        out.append("G")
    if p.state:
        out.append("S")
    if p.decisions:
        out.append("D")
    if p.evidence:
        out.append("E")
    if p.unknowns:
        out.append("U")
    if p.risks:
        out.append("R")
    if p.test:
        out.append("T")
    if p.files:
        out.append("F")
    if p.tool_calls:
        out.append("Y")
    if p.next_agent:
        out.append("N")
    if p.halt:
        out.append("H")
    if p.confidence:
        out.append("P")
    if p.assumptions:
        out.append("A")
    return out


def extract_mllang_signals(response_text: str) -> Optional[Dict[str, Any]]:
    """Pull MLLANG structured signals from a model response.

    Tries (in order):
        1. Fenced ```mllang block extraction.
        2. Bare packet starting with `V:0.1.r...` somewhere in the text.

    Returns:
        Dict of signals (halt, confidence, agent_code, slots_present,
        json_rpc_chars), or None when no packet found / parser absent.
    """
    if not _HAVE_MLLANG or not response_text:
        return None

    p: Optional[Any] = None

    # Try fenced markdown block first
    if "```mllang" in response_text:
        try:
            packets = extract_from_markdown(response_text)
            if packets:
                p = packets[0]
        except Exception:
            p = None

    # Fall back to bare packet: locate first "V:0.1.rN;" and parse from there
    if p is None:
        m = _BARE_PACKET_RE.search(response_text)
        if m:
            try:
                p = parse(response_text[m.start():])
            except Exception:
                p = None

    if p is None or not p.version:
        return None

    json_rpc = _build_json_rpc_envelope(p)

    return {
        "halt": p.halt or "",
        "confidence": float(p.confidence) if p.confidence else 0.0,
        "agent_code": _agent_code(p.next_agent),
        "slots_present": _slots_present(p),
        "json_rpc_chars": len(json_rpc),
    }
