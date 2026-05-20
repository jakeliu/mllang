#!/usr/bin/env python3
"""End-to-end tests for the Codex session JSONL parser."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
INTEGRATION = ROOT / "codex-cli-integration"
SCRIPTS = INTEGRATION / "scripts"
FIXTURE = INTEGRATION / "fixtures" / "sample_rollout.jsonl"

sys.path.insert(0, str(SCRIPTS))
sys.path.insert(0, str(ROOT / "shim"))
sys.path.insert(0, str(ROOT / "parser"))

import codex_session_parser as parser  # noqa: E402
from extract_budget import extract_budget  # noqa: E402


def _read_rows(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _check(name: str, condition: bool, detail: str = "") -> tuple[int, int]:
    if condition:
        print(f"  PASS  {name}")
        return 1, 0
    print(f"  FAIL  {name} {detail}")
    return 0, 1


def _mutate_final_message(rows: list[dict], text: str) -> list[dict]:
    out = json.loads(json.dumps(rows))
    for row in out:
        payload = row.get("payload", {})
        if row.get("type") == "event_msg" and payload.get("type") == "agent_message":
            payload["message"] = text
        if row.get("type") == "event_msg" and payload.get("type") == "task_complete":
            payload["last_agent_message"] = text
    return out


def main() -> int:
    passed = failed = 0

    def check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        p, f = _check(name, condition, detail)
        passed += p
        failed += f

    rows = _read_rows(FIXTURE)
    check("fixture exists and has rows", len(rows) >= 6)
    check("fixture user text redacted", all("<REDACTED" in r.get("payload", {}).get("message", "") for r in rows if r.get("payload", {}).get("type") == "user_message"))
    check("fixture paths anonymized", "/Users/" not in FIXTURE.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "codex-mllang.jsonl"
        records = parser.parse_rows(rows, log_path=str(log_path))
        written = _read_rows(log_path)

        check("parser produces one record for one task_complete", len(records) == 1 and len(written) == 1)
        check("session-token_count fallback tokens_in", written[0]["tokens_in"] == 18040)
        check("session-token_count fallback tokens_out", written[0]["tokens_out"] == 773)
        check("budget_source tag is session-token_count", written[0]["tags"]["budget_source"] == "session-token_count")
        check("has_mllang_packet true for fixture packet", written[0]["has_mllang_packet"] is True)
        check("tags include codex_cli_version", written[0]["tags"]["codex_cli_version"] == "0.130.0")
        check("tags include codex_session_id", written[0]["tags"]["codex_session_id"] == "019e427b-9169-7c11-b1a5-3e631c43e693")
        check("tags include turn capture boundary", written[0]["tags"]["capture_boundary"] == "turn")

    b_packet = (
        "V:0.1.r1; I:b-slot-fixture; G:{task=test}; S:{ok=1}; "
        "B:{tokens_in=850, tokens_out=240, time=3.4s}; "
        "N:@K -> report; H:test=pass; P:0.88; EN: Budget fixture."
    )
    budget = extract_budget(b_packet)
    check("extract_budget reads B slot", budget.present and budget.tokens_in == 850 and budget.tokens_out == 240 and budget.latency_s == 3.4)

    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "b-slot.jsonl"
        records = parser.parse_rows(_mutate_final_message(rows, b_packet), log_path=str(log_path))
        written = _read_rows(log_path)
        check("B-slot wins over session token_count", len(records) == 1 and written[0]["tokens_in"] == 850 and written[0]["tokens_out"] == 240)
        check("B-slot budget_source tag", written[0]["tags"]["budget_source"] == "B-slot")
        check("B-slot latency wins", written[0]["latency_s"] == 3.4)

    malformed_b_packet = (
        "V:0.1.r1; I:b-slot-malformed; G:{task=test}; S:{ok=1}; "
        "B:{tokens=4000}; N:@K -> report; H:test=pass; P:0.88; EN: Bad budget."
    )
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "malformed-b-slot.jsonl"
        parser.parse_rows(_mutate_final_message(rows, malformed_b_packet), log_path=str(log_path))
        written = _read_rows(log_path)
        check("malformed B-slot falls back to session token_count", written[0]["tokens_in"] == 18040 and written[0]["tags"]["budget_source"] == "session-token_count")

    prose_no_packet = "Plain final answer without an MLLANG packet."
    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "plain.jsonl"
        records = parser.parse_rows(_mutate_final_message(rows, prose_no_packet), log_path=str(log_path))
        written = _read_rows(log_path)
        check("plain response still records one turn", len(records) == 1)
        check("plain response has_mllang_packet false", written[0]["has_mllang_packet"] is False)
        check("plain response uses session-token_count", written[0]["tags"]["budget_source"] == "session-token_count")

    with tempfile.TemporaryDirectory() as tmp:
        bad_path = Path(tmp) / "bad.jsonl"
        bad_path.write_text('{"type":"event_msg","payload":{"type":"task_started"}}\nnot-json\n', encoding="utf-8")
        log_path = Path(tmp) / "bad-log.jsonl"
        records = parser.parse_rows(parser._read_jsonl_lines(bad_path.read_text(encoding="utf-8").splitlines()), log_path=str(log_path))
        check("malformed JSONL skipped without raising", len(records) == 0)

    with tempfile.TemporaryDirectory() as tmp:
        log_path = Path(tmp) / "empty-log.jsonl"
        records = parser.parse_rows([], log_path=str(log_path))
        check("empty rollout returns zero records", len(records) == 0)

    with tempfile.TemporaryDirectory() as tmp:
        fixture_copy = Path(tmp) / "sample.jsonl"
        fixture_copy.write_text(FIXTURE.read_text(encoding="utf-8"), encoding="utf-8")
        log_path = Path(tmp) / "cli-log.jsonl"
        count = parser.parse_file(fixture_copy, log_path=str(log_path))
        check("parse_file returns record count", count == 1)

    print()
    print(f"--- codex session parser: {passed} passed, {failed} failed ---")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
