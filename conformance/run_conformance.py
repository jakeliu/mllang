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

from mllang import (
    Packet,
    parse,
    compose,
    extract_from_markdown,
    sanitize,
    embed_in_markdown,
    extract_summary_and_packet,
)
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


def run_sanitize_tests():
    """Test sanitize() telemetry redaction behavior."""
    path = TESTS_DIR / "sanitize_30.jsonl"
    if not path.exists():
        return 0, 0
    passed = failed = 0
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        case = json.loads(line)
        name = case.get("name", f"line {line_no}")
        level = case.get("level", "shape")

        try:
            # Special multi-input case
            if case.get("check") == "thread_hashes_differ":
                o1 = sanitize(case["input1"], level=level)
                o2 = sanitize(case["input2"], level=level)
                if o1 is None or o2 is None:
                    print(f"  FAIL sanitize {name}: one payload null")
                    failed += 1
                    continue
                if o1["thread_hash"] == o2["thread_hash"]:
                    print(f"  FAIL sanitize {name}: thread_hash collision {o1['thread_hash']}")
                    failed += 1
                    continue
                passed += 1
                continue

            # Optionally accept Packet object
            payload_input = case["input"]
            if case.get("input_as_packet_object"):
                payload_input = parse(payload_input)

            reject_leaks = case.get("reject_leaks", True)
            out = sanitize(payload_input, level=level, reject_leaks=reject_leaks)

            expect = case.get("expect", "__SKIP__")
            if expect is None:
                if out is None:
                    passed += 1
                else:
                    print(f"  FAIL sanitize {name}: expected None, got payload")
                    failed += 1
                continue

            if expect == "__SKIP__":
                pass  # Use other assertion fields
            else:
                bad = False
                for k, v in expect.items():
                    if out is None:
                        print(f"  FAIL sanitize {name}: expected {k}={v!r}, got None payload")
                        bad = True
                        break
                    if out.get(k) != v:
                        print(f"  FAIL sanitize {name}: {k} got={out.get(k)!r} expected={v!r}")
                        bad = True
                        break
                if bad:
                    failed += 1
                    continue

            if "must_not_contain_substring" in case:
                needle = case["must_not_contain_substring"]
                blob = json.dumps(out) if out is not None else ""
                if needle in blob:
                    print(f"  FAIL sanitize {name}: payload contains forbidden substring {needle!r}")
                    failed += 1
                    continue

            if "expect_contains_slots" in case:
                if out is None or not set(case["expect_contains_slots"]).issubset(set(out.get("slots_present", []))):
                    print(f"  FAIL sanitize {name}: slots_present missing required entries")
                    failed += 1
                    continue

            if "expect_thread_hash_prefix" in case:
                if out is None or not out.get("thread_hash", "").startswith(case["expect_thread_hash_prefix"]):
                    print(f"  FAIL sanitize {name}: thread_hash prefix mismatch ({out.get('thread_hash') if out else 'None'})")
                    failed += 1
                    continue

            if "expect_thread_hash_equals" in case:
                if out is None or out.get("thread_hash") != case["expect_thread_hash_equals"]:
                    print(f"  FAIL sanitize {name}: thread_hash mismatch: {out.get('thread_hash') if out else 'None'}")
                    failed += 1
                    continue

            if "expect_goal_keys" in case:
                if out is None or sorted(out.get("goal_keys", [])) != sorted(case["expect_goal_keys"]):
                    print(f"  FAIL sanitize {name}: goal_keys mismatch: {out.get('goal_keys') if out else 'None'}")
                    failed += 1
                    continue

            if "expect_state_keys" in case:
                if out is None or sorted(out.get("state_keys", [])) != sorted(case["expect_state_keys"]):
                    print(f"  FAIL sanitize {name}: state_keys mismatch")
                    failed += 1
                    continue

            if "expect_test_results" in case:
                if out is None or out.get("test_results") != case["expect_test_results"]:
                    print(f"  FAIL sanitize {name}: test_results mismatch")
                    failed += 1
                    continue

            if "expect_tool_verbs" in case:
                if out is None or sorted(out.get("tool_verbs", [])) != sorted(case["expect_tool_verbs"]):
                    print(f"  FAIL sanitize {name}: tool_verbs mismatch")
                    failed += 1
                    continue

            if "expect_counts" in case:
                if out is None:
                    print(f"  FAIL sanitize {name}: payload null for counts check")
                    failed += 1
                    continue
                bad = False
                for k, v in case["expect_counts"].items():
                    if out.get(k) != v:
                        print(f"  FAIL sanitize {name}: count {k} got={out.get(k)} expected={v}")
                        bad = True
                        break
                if bad:
                    failed += 1
                    continue

            if "expect_goal_values_redacted" in case:
                if out is None or out.get("goal_values_redacted") != case["expect_goal_values_redacted"]:
                    print(f"  FAIL sanitize {name}: goal_values_redacted mismatch: {out.get('goal_values_redacted') if out else 'None'}")
                    failed += 1
                    continue

            if "expect_state_values_redacted" in case:
                if out is None or out.get("state_values_redacted") != case["expect_state_values_redacted"]:
                    print(f"  FAIL sanitize {name}: state_values_redacted mismatch: {out.get('state_values_redacted') if out else 'None'}")
                    failed += 1
                    continue

            if "expect_assumptions_prefix_length_each_le" in case:
                cap = case["expect_assumptions_prefix_length_each_le"]
                if out is None or any(len(a) > cap for a in out.get("assumptions_prefix", [])):
                    print(f"  FAIL sanitize {name}: assumption prefix exceeds {cap} chars")
                    failed += 1
                    continue

            if "expect_operators_contains" in case:
                if out is None or not set(case["expect_operators_contains"]).issubset(set(out.get("operators_used", []))):
                    print(f"  FAIL sanitize {name}: operators_used missing required entries: have {out.get('operators_used') if out else 'None'}")
                    failed += 1
                    continue

            if "expect_halt_categories" in case:
                if out is None or out.get("halt_categories") != case["expect_halt_categories"]:
                    print(f"  FAIL sanitize {name}: halt_categories mismatch")
                    failed += 1
                    continue

            passed += 1
        except Exception as e:
            print(f"  FAIL sanitize {name}: exception {e}")
            failed += 1
    return passed, failed


def run_embed_tests():
    """Test embed_in_markdown / extract_summary_and_packet behavior."""
    path = TESTS_DIR / "embed_10.jsonl"
    if not path.exists():
        return 0, 0
    passed = failed = 0
    for line_no, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        case = json.loads(line)
        name = case.get("name", f"line {line_no}")

        try:
            if case.get("extract_only"):
                summary, parsed_pkt = extract_summary_and_packet(case["raw_markdown"])
                if case.get("extract_expect_packet_none"):
                    if parsed_pkt is None:
                        passed += 1
                    else:
                        print(f"  FAIL embed {name}: expected no packet, got one")
                        failed += 1
                continue

            if case.get("expect_raises_value_error"):
                try:
                    embed_in_markdown(case["packet"], mode=case.get("mode", "summary"))
                    print(f"  FAIL embed {name}: expected ValueError, none raised")
                    failed += 1
                except ValueError:
                    passed += 1
                continue

            md = embed_in_markdown(
                case["packet"],
                summary=case.get("summary", ""),
                prose=case.get("prose"),
                mode=case.get("mode", "summary"),
                title=case.get("title"),
            )

            bad = False
            for needle in case.get("must_contain", []):
                if needle not in md:
                    print(f"  FAIL embed {name}: missing required substring {needle!r}")
                    bad = True
                    break
            if bad:
                failed += 1
                continue

            for needle in case.get("must_not_contain", []):
                if needle in md:
                    print(f"  FAIL embed {name}: contains forbidden substring {needle!r}")
                    bad = True
                    break
            if bad:
                failed += 1
                continue

            if "roundtrip_check" in case:
                summary, parsed_pkt = extract_summary_and_packet(md)
                check = case["roundtrip_check"]
                if "summary_equals" in check and summary != check["summary_equals"]:
                    print(f"  FAIL embed {name}: roundtrip summary got={summary!r} expected={check['summary_equals']!r}")
                    failed += 1
                    continue
                if "thread_id" in check and (parsed_pkt is None or parsed_pkt.thread_id != check["thread_id"]):
                    print(f"  FAIL embed {name}: roundtrip thread_id mismatch")
                    failed += 1
                    continue

            passed += 1
        except Exception as e:
            print(f"  FAIL embed {name}: exception {e}")
            failed += 1
    return passed, failed


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

    s_pass, s_fail = run_sanitize_tests()
    print(f"SANITIZE tests:   {s_pass} passed, {s_fail} failed")

    e_pass, e_fail = run_embed_tests()
    print(f"EMBED tests:      {e_pass} passed, {e_fail} failed")

    total_pass = p_pass + h_pass + r_pass + m_pass + s_pass + e_pass
    total_fail = p_fail + h_fail + r_fail + m_fail + s_fail + e_fail

    print(f"\n--- TOTAL: {total_pass} passed, {total_fail} failed ---")
    sys.exit(0 if total_fail == 0 else 1)


if __name__ == "__main__":
    main()
