#!/usr/bin/env python3
"""Extract the cooperative MLLANG B: budget slot from model output.

This mirrors the Claude Code skill's `_extract_budget()` helper, with a
small regex fallback so the Codex integration can still detect B: when the
optional `mllang` package is not importable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class Budget:
    tokens_in: int = 0
    tokens_out: int = 0
    latency_s: float = 0.0
    present: bool = False


def _intish(value: Any) -> int:
    text = str(value).strip().rstrip("s").rstrip()
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return 0


def _floatish(value: Any) -> float:
    text = str(value).strip().rstrip("s").rstrip()
    try:
        return float(text)
    except (TypeError, ValueError):
        return 0.0


def _budget_from_mapping(mapping: Mapping[str, Any]) -> Budget:
    if not mapping:
        return Budget()
    return Budget(
        tokens_in=_intish(mapping.get("tokens_in", 0)),
        tokens_out=_intish(mapping.get("tokens_out", 0)),
        latency_s=_floatish(mapping.get("time", mapping.get("latency_s", 0))),
        present=True,
    )


def _extract_via_mllang(response_text: str) -> Budget:
    try:
        from mllang import extract_from_markdown, parse
    except ImportError:
        return Budget()

    packet = None
    if "```mllang" in response_text:
        try:
            packets = extract_from_markdown(response_text)
            if packets:
                packet = packets[0]
        except Exception:
            packet = None

    if packet is None:
        match = re.search(r"V:\s*\d+\.\d+\.r\d+\s*;", response_text)
        if match:
            try:
                packet = parse(response_text[match.start():])
            except Exception:
                packet = None

    budget = getattr(packet, "budget", None) if packet is not None else None
    if not budget:
        return Budget()
    return _budget_from_mapping(budget)


def _packet_slice(response_text: str) -> str:
    fenced = re.search(r"```mllang\s*(.*?)```", response_text, flags=re.DOTALL)
    if fenced:
        return fenced.group(1)
    match = re.search(r"V:\s*\d+\.\d+\.r\d+\s*;", response_text)
    return response_text[match.start():] if match else response_text


def _extract_via_regex(response_text: str) -> Budget:
    packet_text = _packet_slice(response_text)
    match = re.search(r"\bB\s*:\s*\{([^}]*)\}", packet_text, flags=re.DOTALL)
    if not match:
        return Budget()

    values: dict[str, str] = {}
    for part in match.group(1).split(","):
        if "=" not in part:
            continue
        key, value = part.split("=", 1)
        values[key.strip()] = value.strip().strip('"')

    if not values:
        return Budget(present=True)
    return _budget_from_mapping(values)


def extract_budget(response_text: str) -> Budget:
    """Return tokens/latency from B:{...}, or an empty Budget when absent."""
    if not response_text:
        return Budget()

    budget = _extract_via_mllang(response_text)
    if budget.present:
        return budget
    return _extract_via_regex(response_text)
