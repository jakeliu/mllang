"""MLLANG telemetry sanitization.

Strips IP from packets BEFORE telemetry leaves user's machine. Slot
SHAPES are public; slot VALUES stay private.

Public API:
    sanitize(packet, level=None, reject_leaks=True) -> dict | None

Levels:
    off        — return None (nothing sent). Default.
    shape      — slot presence, halt, confidence, next-agent code, operators.
    structured — shape + map keys (no values) + verb names + counts.
    full       — structured + redacted map values + assumption prefixes.

Set via MLLANG_TELEMETRY env var or explicit level=... kwarg.
Per-packet override always wins over env var.

Defense in depth: by default, sanitize() refuses to ship a payload that
still matches any leak detector (email/path/api-key/long-quote) and
returns None instead.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from typing import Any, Dict, List, Optional, Union

from .halt import halt_categories
from .operators import OPERATORS
from .packet import Packet, compose, parse

VALID_LEVELS = {"off", "shape", "structured", "full"}
DEFAULT_LEVEL = "off"

# Operators excluded from telemetry: structural / too common to be a signal.
_TRIVIAL_OPS = {";", ",", "=", "[]", "{}", "()"}

# Leak detectors — last-line defense before payload ships.
_EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
_PATH_RE = re.compile(r"(?:/[A-Za-z0-9._-]+){2,}")
_API_KEY_RE = re.compile(
    r"\b(?:sk|pk|api|key|token|secret|bearer)[-_=][A-Za-z0-9_-]{16,}",
    re.IGNORECASE,
)
_LONG_QUOTE_RE = re.compile(r'"[^"]{60,}"')

_LEAK_DETECTORS = [
    ("email", _EMAIL_RE),
    ("path", _PATH_RE),
    ("api_key", _API_KEY_RE),
    ("long_quote", _LONG_QUOTE_RE),
]

_TOOL_VERB_RE = re.compile(r"\$?([A-Za-z_][A-Za-z0-9_]*)")
_AGENT_CODE_RE = re.compile(r"@[CXKGMH?]")


def _level_from_env(explicit: Optional[str]) -> str:
    if explicit is not None:
        level = explicit
    else:
        level = os.environ.get("MLLANG_TELEMETRY", DEFAULT_LEVEL).lower()
    if level not in VALID_LEVELS:
        level = DEFAULT_LEVEL
    return level


def _hash_thread_id(thread_id: str) -> str:
    if not thread_id:
        return ""
    digest = hashlib.sha256(thread_id.encode("utf-8")).hexdigest()[:12]
    return f"<I:hash:{digest}>"


def _detect_operators(packet_text: str) -> List[str]:
    """Return operators present in raw text. Multi-char first to avoid shadow."""
    found: List[str] = []
    seen: set = set()
    ops_sorted = sorted(OPERATORS.keys(), key=lambda o: -len(o))
    for op in ops_sorted:
        if op in _TRIVIAL_OPS or op in seen:
            continue
        if op in packet_text:
            found.append(op)
            seen.add(op)
    return found


def _redact_map(m: Dict[str, str]) -> Dict[str, str]:
    return {k: f"<REDACTED:{len(v)}-chars>" for k, v in m.items()}


def _verb_names(tool_calls: List[str]) -> List[str]:
    """Verb name from $verb(args). Args NEVER returned."""
    out: List[str] = []
    for call in tool_calls:
        m = _TOOL_VERB_RE.search(call)
        if m:
            out.append(m.group(1))
    return out


def _agent_code(next_agent: str) -> str:
    m = _AGENT_CODE_RE.search(next_agent or "")
    return m.group(0) if m else ""


def _slots_present(p: Packet) -> List[str]:
    present: List[str] = []
    if p.version:
        present.append("V")
    if p.thread_id:
        present.append("I")
    if p.goal:
        present.append("G")
    if p.state:
        present.append("S")
    if p.decisions:
        present.append("D")
    if p.evidence:
        present.append("E")
    if p.unknowns:
        present.append("U")
    if p.risks:
        present.append("R")
    if p.test:
        present.append("T")
    if p.files:
        present.append("F")
    if p.tool_calls:
        present.append("Y")
    if p.budget:
        present.append("B")
    if p.next_agent:
        present.append("N")
    if p.halt:
        present.append("H")
    if p.confidence:
        present.append("P")
    if p.assumptions:
        present.append("A")
    return present


def _walk_strings(value: Any):
    if isinstance(value, str):
        yield value
    elif isinstance(value, dict):
        for k, v in value.items():
            yield k
            yield from _walk_strings(v)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_strings(item)


def _detect_leaks(payload: Dict[str, Any]) -> List[str]:
    """Scan payload for residual IP markers. Returns hit list."""
    leaks: List[str] = []
    for key, value in payload.items():
        if key in ("thread_hash",):
            continue  # hash output deliberately matches no detector
        for text in _walk_strings(value):
            for name, rx in _LEAK_DETECTORS:
                if rx.search(text):
                    leaks.append(f"{key}:{name}")
                    break
    return leaks


def sanitize(
    packet: Union[Packet, str],
    level: Optional[str] = None,
    reject_leaks: bool = True,
) -> Optional[Dict[str, Any]]:
    """Sanitize an MLLANG packet for telemetry.

    Args:
        packet: a Packet object or raw MLLANG text.
        level: "off" | "shape" | "structured" | "full".
            None = read MLLANG_TELEMETRY env var (default "off").
        reject_leaks: when True (default), return None instead of a payload
            whose values still match a leak detector.

    Returns:
        dict telemetry payload, or None if level=="off" / leak detected /
        packet unparseable.
    """
    resolved = _level_from_env(level)
    if resolved == "off":
        return None

    if isinstance(packet, Packet):
        p = packet
        raw_text = compose(p)
    else:
        try:
            p = parse(packet)
        except ValueError:
            return None
        raw_text = packet

    if not p.version:
        return None

    if reject_leaks:
        for _name, rx in _LEAK_DETECTORS:
            if rx.search(raw_text):
                return None

    payload: Dict[str, Any] = {
        "v": p.version,
        "slots_present": _slots_present(p),
        "operators_used": _detect_operators(raw_text),
        "halt": p.halt,
        "halt_categories": halt_categories(p.halt),
        "confidence": p.confidence,
        "next_agent": _agent_code(p.next_agent),
        "thread_hash": _hash_thread_id(p.thread_id),
        "level": resolved,
    }

    if resolved in ("structured", "full"):
        payload.update(
            {
                "goal_keys": list(p.goal.keys()),
                "state_keys": list(p.state.keys()),
                "test_results": {
                    k: v for k, v in p.test.items() if v in ("pass", "fail")
                },
                "tool_verbs": _verb_names(p.tool_calls),
                "decisions_count": len(p.decisions),
                "evidence_count": len(p.evidence),
                "unknowns_count": len(p.unknowns),
                "risks_count": len(p.risks),
                "files_count": len(p.files),
                "tool_calls_count": len(p.tool_calls),
                "assumptions_count": len(p.assumptions),
                "en_shadow_length": len(p.en_shadow),
            }
        )

    if resolved == "full":
        payload.update(
            {
                "goal_values_redacted": _redact_map(p.goal),
                "state_values_redacted": _redact_map(p.state),
                "assumptions_prefix": [a[:20] for a in p.assumptions],
            }
        )

    if reject_leaks:
        leaks = _detect_leaks(payload)
        if leaks:
            return None

    return payload


def sanitize_to_json(
    packet: Union[Packet, str],
    level: Optional[str] = None,
    reject_leaks: bool = True,
) -> Optional[str]:
    """sanitize() + JSON encode. None when payload would be empty / rejected."""
    out = sanitize(packet, level=level, reject_leaks=reject_leaks)
    return json.dumps(out, separators=(",", ":")) if out is not None else None
