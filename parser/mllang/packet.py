"""MLLANG Packet parser/composer/validator.

Reference implementation, pure stdlib, ~200 LOC core.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional, Union, List, Dict

from .slots import SLOT_ORDER, REQUIRED_SLOTS, MAP_SLOTS, LIST_SLOTS
from .halt import is_valid_halt
from .operators import AGENT_CODES


# ── Regex helpers ───────────────────────────────────────────────────────


# Match a fenced ```mllang block in markdown
_MARKDOWN_FENCE_RE = re.compile(r"```mllang\s*\n(.*?)\n```", re.DOTALL)

# Match a slot: KEY:value;
# Slot value continues until next ; that's not inside brackets/braces/quotes
_SLOT_KEY_RE = re.compile(r"(?:^|;)\s*([A-Z]):\s*", re.MULTILINE)

# Match version: V:MAJOR.MINOR.rROUND
_VERSION_RE = re.compile(r"^\s*(\d+)\.(\d+)\.r(\d+)\s*$")

# Match next agent: @C -> verb
_NEXT_AGENT_RE = re.compile(r"@([CXKGMH?])\s*->\s*(\S+)")


# ── Packet dataclass ────────────────────────────────────────────────────


@dataclass
class Packet:
    """An MLLANG v0.1 packet."""

    # Required slots
    version: str = ""            # V: "0.1.r1"
    goal: Dict[str, str] = field(default_factory=dict)  # G:
    state: Dict[str, str] = field(default_factory=dict)  # S:
    next_agent: str = ""         # N: "@K -> verb" (full string)
    halt: str = ""               # H: "<=>" or "test=pass | after-3-rounds"

    # Optional slots
    thread_id: str = ""          # I:
    decisions: List[str] = field(default_factory=list)  # D:
    evidence: List[str] = field(default_factory=list)   # E:
    unknowns: List[str] = field(default_factory=list)   # U:
    risks: List[str] = field(default_factory=list)      # R:
    test: Dict[str, str] = field(default_factory=dict)  # T:
    files: List[str] = field(default_factory=list)      # F:
    tool_calls: List[str] = field(default_factory=list) # Y:
    budget: Dict[str, str] = field(default_factory=dict)  # B:
    confidence: float = 0.0      # P:
    assumptions: List[str] = field(default_factory=list)  # A:

    # Dual-channel EN: shadow line (not a slot, but tracked)
    en_shadow: str = ""

    @classmethod
    def parse(cls, text: str) -> "Packet":
        """Parse MLLANG packet text into Packet object."""
        return parse(text)

    def compose(self) -> str:
        """Serialize Packet to MLLANG text."""
        return compose(self)

    def validate(self) -> List[str]:
        """Return list of validation errors. Empty = valid."""
        return validate(self)

    @property
    def next_agent_code(self) -> str:
        """Return just the @X part of N: slot."""
        m = _NEXT_AGENT_RE.search(self.next_agent)
        return f"@{m.group(1)}" if m else ""

    @property
    def next_agent_verb(self) -> str:
        """Return just the verb part of N: slot."""
        m = _NEXT_AGENT_RE.search(self.next_agent)
        return m.group(2) if m else ""

    def __str__(self) -> str:
        return self.compose()


# ── Parser ──────────────────────────────────────────────────────────────


_INLINE_EN_RE = re.compile(r"(?:^|[;\s])EN:\s*", re.MULTILINE)


def _strip_en_shadow(text: str) -> tuple[str, str]:
    """Strip EN: shadow line, return (packet_text, en_text).

    Accepts both forms:
        - EN: on its own line (canonical)
        - EN: inline after the last slot on the same line (common
          output from models that emit one-line packets)
    """
    # Multi-line case — strip lines starting with EN:.
    lines = text.strip().splitlines()
    en = ""
    packet_lines: List[str] = []
    for line in lines:
        if line.startswith("EN:"):
            en = line[len("EN:"):].strip()
        else:
            packet_lines.append(line)
    joined = " ".join(packet_lines).strip()

    # Inline case — find the first EN: that follows a slot terminator
    # or whitespace boundary and split there.
    m = _INLINE_EN_RE.search(joined)
    if m:
        en_inline = joined[m.end():].strip()
        joined = joined[: m.start()].strip()
        # Prefer the inline shadow if no multiline shadow was captured;
        # otherwise concatenate so neither channel is lost.
        if not en:
            en = en_inline
        elif en_inline and en_inline != en:
            en = f"{en} {en_inline}".strip()

    return joined, en


def _split_slots(packet_text: str) -> List[tuple[str, str]]:
    """Split packet into [(slot_key, value), ...]. Respects nested brackets/braces/quotes."""
    slots = []
    i = 0
    text = packet_text.strip()
    while i < len(text):
        # Skip leading whitespace + semicolons
        while i < len(text) and text[i] in " \t;\n":
            i += 1
        if i >= len(text):
            break

        # Expect a slot key (single uppercase letter followed by :)
        if i + 1 < len(text) and text[i].isupper() and text[i + 1] == ":":
            key = text[i]
            i += 2  # skip "K:"

            # Read value until top-level ;
            depth = 0
            in_quote = False
            start = i
            while i < len(text):
                c = text[i]
                if c == '"' and (i == 0 or text[i - 1] != "\\"):
                    in_quote = not in_quote
                elif not in_quote:
                    if c in "[{(":
                        depth += 1
                    elif c in "]})":
                        depth -= 1
                    elif c == ";" and depth == 0:
                        break
                i += 1

            value = text[start:i].strip()
            slots.append((key, value))
        else:
            # Unknown character — skip and continue
            i += 1
    return slots


def _parse_map(value: str) -> Dict[str, str]:
    """Parse {k=v, k=v} into dict."""
    value = value.strip()
    if value.startswith("{") and value.endswith("}"):
        value = value[1:-1].strip()
    if not value:
        return {}
    out = {}
    parts = _split_top_level(value, ",")
    for part in parts:
        part = part.strip()
        if "=" in part:
            k, v = part.split("=", 1)
            out[k.strip()] = v.strip()
        elif part:
            out[part] = ""
    return out


def _parse_list(value: str) -> List[str]:
    """Parse [a, b, c] into list."""
    value = value.strip()
    if value.startswith("[") and value.endswith("]"):
        value = value[1:-1].strip()
    if not value:
        return []
    return [p.strip() for p in _split_top_level(value, ",")]


def _split_top_level(text: str, sep: str) -> List[str]:
    """Split by `sep` at top level (respects nested brackets/braces/quotes)."""
    out = []
    depth = 0
    in_quote = False
    cur = []
    for i, c in enumerate(text):
        if c == '"' and (i == 0 or text[i - 1] != "\\"):
            in_quote = not in_quote
            cur.append(c)
        elif in_quote:
            cur.append(c)
        elif c in "[{(":
            depth += 1
            cur.append(c)
        elif c in "]})":
            depth -= 1
            cur.append(c)
        elif c == sep and depth == 0:
            out.append("".join(cur))
            cur = []
        else:
            cur.append(c)
    if cur:
        out.append("".join(cur))
    return out


def parse(text: str) -> Packet:
    """Parse MLLANG packet text into Packet object.

    Tolerates optional EN: shadow line.
    """
    if not text or not text.strip():
        raise ValueError("Empty packet")

    packet_text, en = _strip_en_shadow(text)
    slots = _split_slots(packet_text)

    p = Packet()
    p.en_shadow = en

    for key, value in slots:
        if key == "V":
            p.version = value.strip()
        elif key == "I":
            p.thread_id = value.strip()
        elif key == "G":
            p.goal = _parse_map(value)
        elif key == "S":
            p.state = _parse_map(value)
        elif key == "D":
            p.decisions = _parse_list(value)
        elif key == "E":
            p.evidence = _parse_list(value)
        elif key == "U":
            p.unknowns = _parse_list(value)
        elif key == "R":
            p.risks = _parse_list(value)
        elif key == "T":
            p.test = _parse_map(value)
        elif key == "F":
            p.files = _parse_list(value)
        elif key == "Y":
            p.tool_calls = _parse_list(value)
        elif key == "B":
            p.budget = _parse_map(value)
        elif key == "N":
            p.next_agent = value.strip()
        elif key == "H":
            p.halt = value.strip()
        elif key == "P":
            try:
                p.confidence = float(value.strip())
            except ValueError:
                pass
        elif key == "A":
            p.assumptions = _parse_list(value)

    return p


def compose(p: Packet) -> str:
    """Serialize Packet to MLLANG text (single line + EN: line if present)."""
    parts = []

    def fmt_map(m: Dict[str, str]) -> str:
        return "{" + ", ".join(f"{k}={v}" for k, v in m.items()) + "}"

    def fmt_list(l: List[str]) -> str:
        return "[" + ", ".join(l) + "]"

    if p.version:
        parts.append(f"V:{p.version}")
    if p.thread_id:
        parts.append(f"I:{p.thread_id}")
    if p.goal:
        parts.append(f"G:{fmt_map(p.goal)}")
    if p.state:
        parts.append(f"S:{fmt_map(p.state)}")
    if p.decisions:
        parts.append(f"D:{fmt_list(p.decisions)}")
    if p.evidence:
        parts.append(f"E:{fmt_list(p.evidence)}")
    if p.unknowns:
        parts.append(f"U:{fmt_list(p.unknowns)}")
    if p.risks:
        parts.append(f"R:{fmt_list(p.risks)}")
    if p.test:
        parts.append(f"T:{fmt_map(p.test)}")
    if p.files:
        parts.append(f"F:{fmt_list(p.files)}")
    if p.tool_calls:
        parts.append(f"Y:{fmt_list(p.tool_calls)}")
    if p.budget:
        parts.append(f"B:{fmt_map(p.budget)}")
    if p.next_agent:
        parts.append(f"N:{p.next_agent}")
    if p.halt:
        parts.append(f"H:{p.halt}")
    if p.confidence > 0:
        parts.append(f"P:{p.confidence:.2f}")
    if p.assumptions:
        parts.append(f"A:{fmt_list(p.assumptions)}")

    body = "; ".join(parts) + ";"
    if p.en_shadow:
        body += f"\nEN: {p.en_shadow}"
    return body


def validate(p: Packet) -> List[str]:
    """Return list of validation errors. Empty = valid."""
    errors = []

    # Required slots
    if not p.version:
        errors.append("missing required slot V (version)")
    elif not _VERSION_RE.match(p.version):
        errors.append(f"V slot must be MAJOR.MINOR.rROUND format, got: {p.version!r}")

    if not p.goal:
        errors.append("missing required slot G (goal)")

    if not p.state:
        errors.append("missing required slot S (state)")

    if not p.next_agent:
        errors.append("missing required slot N (next agent)")
    elif not _NEXT_AGENT_RE.search(p.next_agent):
        errors.append(f"N slot must be '@<agent> -> <verb>' format, got: {p.next_agent!r}")

    if not p.halt:
        errors.append("missing required slot H (halt)")
    elif not is_valid_halt(p.halt):
        errors.append(f"H slot has invalid value(s): {p.halt!r}")

    # Confidence range
    if p.confidence and not (0.0 <= p.confidence <= 1.0):
        errors.append(f"P slot must be 0.00-1.00, got: {p.confidence}")

    # Agent code validation
    if p.next_agent:
        m = _NEXT_AGENT_RE.search(p.next_agent)
        if m:
            agent = f"@{m.group(1)}"
            if agent not in AGENT_CODES:
                errors.append(f"unknown agent code in N: {agent}")

    return errors


def extract_from_markdown(md_text: str) -> List[Packet]:
    """Find all fenced ```mllang blocks in markdown, parse each into Packet."""
    matches = _MARKDOWN_FENCE_RE.findall(md_text)
    out = []
    for m in matches:
        try:
            out.append(parse(m))
        except ValueError:
            continue
    return out
