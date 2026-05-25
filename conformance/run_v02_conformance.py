#!/usr/bin/env python3
"""
run_v02_conformance.py — light v0.2 conformance check.

Loads conformance/tests/cap_20.jsonl. For each record, parses the input with the
examples/weather_runner.parse_packet (which already supports T:, CAP:, TR:, SIG:
slots transparently as unknown-passthrough) and asserts the expected slot
shapes.

This is a *minimal* gate so we can keep the v0.1 runner pristine while still
testing v0.2 packet shapes from RFC 0001.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "examples"))

from weather_runner import parse_packet, MLLangError  # noqa: E402

TEST_FILE = ROOT / "conformance" / "tests" / "cap_20.jsonl"


def _norm_n(value: str) -> str:
    m = re.match(r"\s*(@\w+)\s*->", str(value))
    return m.group(1) if m else str(value).strip()


def check(rec: dict) -> str:
    inp = rec["input"]
    exp = rec["expected"]
    try:
        p = parse_packet(inp)
    except MLLangError as exc:
        return f"PARSE_FAIL: {exc}"
    slots = p.slots
    if "version" in exp and slots.get("V") != exp["version"]:
        return f"version mismatch: {slots.get('V')} != {exp['version']}"
    if "thread_id" in exp and slots.get("I") != exp["thread_id"]:
        return f"thread_id mismatch: {slots.get('I')} != {exp['thread_id']}"
    if "next_agent_code" in exp:
        actual = _norm_n(slots.get("N", ""))
        if actual != exp["next_agent_code"]:
            return f"agent mismatch: {actual} != {exp['next_agent_code']}"
    if "halt" in exp and slots.get("H") != exp["halt"]:
        return f"halt mismatch: {slots.get('H')} != {exp['halt']}"
    if "confidence" in exp and float(slots.get("P", 0)) != exp["confidence"]:
        return f"confidence mismatch: {slots.get('P')} != {exp['confidence']}"
    if exp.get("has_t_slot") and slots.get("T") != exp.get("t_value", slots.get("T")):
        return f"t_slot mismatch: {slots.get('T')} != {exp.get('t_value')}"
    if exp.get("has_cap_slot") and not isinstance(slots.get("CAP"), dict):
        return "CAP missing or not a dict"
    if exp.get("has_err_code"):
        o = slots.get("O", {})
        err_text = ""
        if isinstance(o, dict):
            err_text = str(o.get("err", ""))
        if exp["err_code"] not in err_text:
            return f"err code missing: looking for {exp['err_code']} in {err_text[:80]!r}"
    if exp.get("has_tr_slot"):
        tr = slots.get("TR")
        if not isinstance(tr, dict):
            return "TR missing or not a dict"
        if "tr_root" in exp and tr.get("root") != exp["tr_root"]:
            return f"TR.root mismatch: {tr.get('root')} != {exp['tr_root']}"
        if "tr_parent" in exp and tr.get("parent") != exp["tr_parent"]:
            return f"TR.parent mismatch: {tr.get('parent')} != {exp['tr_parent']}"
        if "tr_depth" in exp and tr.get("depth") != exp["tr_depth"]:
            return f"TR.depth mismatch: {tr.get('depth')} != {exp['tr_depth']}"
    if exp.get("has_sig_slot"):
        sig = slots.get("SIG")
        if not isinstance(sig, str) or not re.fullmatch(r"[0-9a-fA-F]+", sig):
            return f"SIG missing or not hex: {sig!r}"
    return ""


def main() -> int:
    passed = 0
    failed = 0
    for idx, line in enumerate(TEST_FILE.read_text().splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        rec = json.loads(line)
        err = check(rec)
        if err:
            print(f"  FAIL #{idx}: {err}")
            failed += 1
        else:
            passed += 1
    print(f"\nv0.2 conformance: {passed} passed, {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
