#!/usr/bin/env python3
"""sanitize_log.py — strip user IP from MLLANG packet logs before public release.

Usage:
    python3 sanitize_log.py --in log.jsonl --out log_public.jsonl

Rules (per Phase F telemetry spec):

Keep verbatim:
  ts, round, from, to, backend, model, tokens_in, tokens_out, latency_s

Keep slot SHAPES (names only, not values):
  slots_present:[V, I, G, S, ...]
  operators_used:[^, $, ->, ...]
  halt: as-is (public enum)
  confidence: as-is (float)
  next_agent: as-is (@C, @X, etc.)

Redact slot VALUES (replace with <REDACTED:N-chars>):
  goal text, state text, decisions, evidence, unknowns, risks,
  files, tool_calls, assumptions, en_shadow,
  PRESERVE: items, K:[] beat content, any quoted string values

Strip entirely:
  Thread IDs (replace with hashed opaque id)
  Custom detector ids (could be proprietary)
  Project-specific keys

The output is safe to push to a public corpus dataset.
"""

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path


# Public detector ids (no ip leak) — extend per use case
PUBLIC_DETECTOR_IDS = set()  # default empty — strip all

# Public slot names (kept verbatim)
SLOT_NAMES = set("V I G S D E U R T F Y B N H P A".split())

# Public halt enum values (kept verbatim)
PUBLIC_HALT = {
    "accept", "repair", "regen", "escalate@H",
    "test=pass", "test=fail", "risk!high", "<=>",
}

# Regex to find quoted strings inside packets
QUOTED_STRING_RE = re.compile(r'"([^"]*)"')


def hash_thread_id(thread_id: str) -> str:
    """Replace thread_id with opaque hash for correlation without leaking name."""
    if not thread_id:
        return ""
    h = hashlib.sha256(thread_id.encode("utf-8")).hexdigest()[:12]
    return f"<I:hash:{h}>"


def redact_quoted(text: str) -> str:
    """Replace quoted string content with <REDACTED:N-chars> placeholder."""
    def replace(m):
        n = len(m.group(1))
        return f'"<REDACTED:{n}-chars>"'
    return QUOTED_STRING_RE.sub(replace, text)


def extract_slot_names(packet: str) -> list:
    """Return list of slot keys present in packet (V, G, S, etc.)."""
    slots = []
    for slot in SLOT_NAMES:
        if re.search(rf'(?:^|;)\s*{re.escape(slot)}\s*:', packet):
            slots.append(slot)
    return sorted(set(slots))


def extract_operators(packet: str) -> list:
    """Return list of operators used in packet."""
    ops = set()
    for op in ["^", "$", "->", "=>", "<=>", "&", "|", "^!", ":=", "=="]:
        if op in packet:
            ops.add(op)
    return sorted(ops)


def extract_halt(packet: str) -> str:
    m = re.search(r';\s*H:\s*([^;]+)', ";" + packet)
    if not m:
        return ""
    halt = m.group(1).strip()
    # Keep only public halt values
    parts = [p.strip() for p in halt.split("|")]
    safe = [p for p in parts if p in PUBLIC_HALT or p.startswith("after-")]
    return " | ".join(safe) if safe else "<redacted>"


def extract_confidence(packet: str) -> float:
    m = re.search(r';\s*P:\s*([0-9.]+)', ";" + packet)
    if not m:
        return 0.0
    try:
        return float(m.group(1))
    except ValueError:
        return 0.0


def extract_next_agent(packet: str) -> str:
    m = re.search(r';\s*N:\s*@([A-Z?])\s*->', ";" + packet)
    if not m:
        return ""
    return "@" + m.group(1)


def sanitize_entry(entry: dict) -> dict:
    """Sanitize one log entry. Keep only public fields."""
    packet = entry.get("packet") or entry.get("math") or ""

    return {
        "ts": entry.get("ts", ""),
        "round": entry.get("round", 0),
        "from": entry.get("from", ""),
        "to": entry.get("to", ""),
        "thread_id_hash": hash_thread_id(entry.get("thread", "") or entry.get("I", "")),
        "slots_present": extract_slot_names(packet),
        "operators_used": extract_operators(packet),
        "halt": extract_halt(packet),
        "confidence": extract_confidence(packet),
        "next_agent": extract_next_agent(packet),
        "backend": entry.get("backend", ""),
        "model": entry.get("model", ""),
        "tokens_in": entry.get("tokens_in", 0),
        "tokens_out": entry.get("tokens_out", 0),
        "latency_s": entry.get("latency_s", 0.0),
        # NOTE: packet content REMOVED. EN: shadow REMOVED. All quoted strings REDACTED.
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True, help="input log.jsonl path")
    ap.add_argument("--out", dest="out_path", required=True, help="output sanitized jsonl path")
    args = ap.parse_args()

    in_p = Path(args.in_path)
    out_p = Path(args.out_path)

    if not in_p.exists():
        print(f"ERROR: input not found: {in_p}", file=sys.stderr)
        sys.exit(1)

    count_in = count_out = 0
    with in_p.open() as fin, out_p.open("w") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            count_in += 1
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            safe = sanitize_entry(entry)
            fout.write(json.dumps(safe) + "\n")
            count_out += 1

    print(f"sanitized {count_out}/{count_in} entries → {out_p}", file=sys.stderr)


if __name__ == "__main__":
    main()
