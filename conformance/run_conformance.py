#!/usr/bin/env python3
"""Run MLLANG conformance test suite.

Exit 0 = all pass. Exit 1 = any fail.

Tests live in tests/<name>.jsonl. Each line = one test case.
"""

import json
import sys
from pathlib import Path

# Make parser importable
sys.path.insert(0, str(Path(__file__).parent.parent / "parser"))

from mllang import Packet, parse, compose, extract_from_markdown
from mllang.halt import is_valid_halt


TESTS_DIR = Path(__file__).parent / "tests"


def run_parse_tests():
    """Test that parser extracts expected slot values."""
    path = TESTS_DIR / "parse_50.jsonl"
    if not path.exists():
        return 0, 0
    passed = failed = 0
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        case = json.loads(line)
        try:
            p = parse(case["input"])
            for slot, expected in case["expected"].items():
                actual = getattr(p, slot)
                if actual != expected:
                    print(f"  FAIL parse line {line_no}: slot={slot} got={actual!r} expected={expected!r}")
                    failed += 1
                    break
            else:
                passed += 1
        except Exception as e:
            print(f"  FAIL parse line {line_no}: exception {e}")
            failed += 1
    return passed, failed


def run_halt_tests():
    """Test halt enum validation."""
    path = TESTS_DIR / "halt_15.jsonl"
    if not path.exists():
        return 0, 0
    passed = failed = 0
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        case = json.loads(line)
        actual = is_valid_halt(case["halt"])
        if actual == case["valid"]:
            passed += 1
        else:
            print(f"  FAIL halt line {line_no}: halt={case['halt']!r} expected={case['valid']} got={actual}")
            failed += 1
    return passed, failed


def run_roundtrip_tests():
    """Test that parse(compose(parse(p))) == parse(p)."""
    path = TESTS_DIR / "parse_50.jsonl"
    if not path.exists():
        return 0, 0
    passed = failed = 0
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        case = json.loads(line)
        try:
            p1 = parse(case["input"])
            text = compose(p1)
            p2 = parse(text)
            # Roundtrip check: key slot values should match
            if p1.version != p2.version:
                print(f"  FAIL roundtrip line {line_no}: version drift")
                failed += 1
                continue
            if p1.thread_id != p2.thread_id:
                print(f"  FAIL roundtrip line {line_no}: thread_id drift")
                failed += 1
                continue
            if p1.halt != p2.halt:
                print(f"  FAIL roundtrip line {line_no}: halt drift")
                failed += 1
                continue
            if abs(p1.confidence - p2.confidence) > 0.001:
                print(f"  FAIL roundtrip line {line_no}: confidence drift {p1.confidence} vs {p2.confidence}")
                failed += 1
                continue
            passed += 1
        except Exception as e:
            print(f"  FAIL roundtrip line {line_no}: exception {e}")
            failed += 1
    return passed, failed


def run_markdown_extract_test():
    """Test extract_from_markdown."""
    md = """# Header

Some prose.

```mllang
V:0.1.r1; I:t1; G:{task=test}; S:{x=1}; N:@K -> classify; H:<=>; P:0.85;
EN: First packet.
```

More prose.

```mllang
V:0.1.r2; I:t2; G:{task=verify}; S:{y=2}; N:@C -> verify; H:test=pass; P:0.91;
EN: Second packet.
```
"""
    packets = extract_from_markdown(md)
    if len(packets) != 2:
        print(f"  FAIL markdown: expected 2 packets, got {len(packets)}")
        return 0, 1
    if packets[0].thread_id != "t1" or packets[1].thread_id != "t2":
        print(f"  FAIL markdown: thread_ids wrong: {packets[0].thread_id} {packets[1].thread_id}")
        return 0, 1
    return 1, 0


def main():
    print("=== MLLANG Conformance Suite ===\n")

    p_pass, p_fail = run_parse_tests()
    print(f"PARSE tests:      {p_pass} passed, {p_fail} failed")

    h_pass, h_fail = run_halt_tests()
    print(f"HALT tests:       {h_pass} passed, {h_fail} failed")

    r_pass, r_fail = run_roundtrip_tests()
    print(f"ROUNDTRIP tests:  {r_pass} passed, {r_fail} failed")

    m_pass, m_fail = run_markdown_extract_test()
    print(f"MARKDOWN tests:   {m_pass} passed, {m_fail} failed")

    total_pass = p_pass + h_pass + r_pass + m_pass
    total_fail = p_fail + h_fail + r_fail + m_fail

    print(f"\n--- TOTAL: {total_pass} passed, {total_fail} failed ---")
    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
