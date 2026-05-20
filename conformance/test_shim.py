#!/usr/bin/env python3
"""End-to-end agent-shim test.

Exercises the full Recorder → JSONL → report-CLI path with both
"standalone" (no MLLANG packets in the responses) and "with MLLANG"
modes. Verifies metrics arithmetic + signal extraction + report format.

Skipped (exit 0 with a message) when `agent-shim` is not installed.
"""

from __future__ import annotations

import json
import os
import sys
import tempfile


def _have_agent_shim() -> bool:
    try:
        import agent_shim  # noqa: F401
    except ImportError:
        return False
    return True


def main() -> int:
    if not _have_agent_shim():
        print("agent-shim not installed — skipping end-to-end test.")
        print("To run: pip install -e shim/")
        return 0

    from agent_shim import Recorder, record
    from agent_shim.report import summarize

    passed = failed = 0

    def _check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed
        if condition:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name} {detail}")
            failed += 1

    with tempfile.TemporaryDirectory() as tmp:
        # --- Standalone (no MLLANG) ---
        log_alone = os.path.join(tmp, "alone.jsonl")
        with record(log_alone) as r:
            r.observe(
                response="Plain prose response",
                model="gpt-4",
                tokens_in=100,
                tokens_out=50,
                latency_s=1.0,
                tags={"call_type": "test_alone"},
            )
            r.observe(
                response="Another plain response",
                model="gpt-4",
                tokens_in=150,
                tokens_out=75,
                latency_s=2.0,
                tags={"call_type": "test_alone"},
            )

        rows = [json.loads(l) for l in open(log_alone)]
        _check("standalone: 2 records written", len(rows) == 2)
        _check("standalone: tokens_in summed correctly",
               sum(r["tokens_in"] for r in rows) == 250)
        _check("standalone: no mllang flag", all(not r["has_mllang_packet"] for r in rows))
        _check("standalone: cost computed",
               all(r["cost_estimate_usd"] > 0 for r in rows))

        summary = summarize(rows, cost_per_M=5.0)
        _check("standalone summary: record count", summary["records"] == 2)
        _check("standalone summary: with_mllang_packet=0",
               summary["with_mllang_packet"] == 0)

        # --- With MLLANG awareness ---
        log_mllang = os.path.join(tmp, "mllang.jsonl")
        packets = [
            "V:0.1.r1; I:t1; G:{task=classify}; S:{x=1}; D:[plan, verify]; "
            "N:@K -> implement; H:test=pass; P:0.85; EN: Classify test.",
            "V:0.1.r1; I:t2; G:{task=refactor}; S:{deps=stable}; "
            "N:@C -> review; H:<=>; P:0.91; EN: Refactor done.",
            "V:0.1.r1; I:t3; G:{task=audit}; S:{rows=668}; "
            "N:@G -> validate; H:risk!high; P:0.62; EN: Audit risk-flagged.",
        ]
        with record(log_mllang, parser="mllang") as r:
            for i, pkt in enumerate(packets, 1):
                r.observe(
                    response=pkt,
                    model="claude-opus-4-7" if i <= 2 else "gemini-pro",
                    tokens_in=200 + 50 * i,
                    tokens_out=80 + 20 * i,
                    latency_s=1.0 + 0.5 * i,
                )

        rows = [json.loads(l) for l in open(log_mllang)]
        _check("mllang: 3 records written", len(rows) == 3)
        _check("mllang: all flagged has_mllang_packet",
               all(r["has_mllang_packet"] for r in rows))
        _check("mllang: confidence captured",
               rows[0]["confidence"] == 0.85 and rows[1]["confidence"] == 0.91)
        _check("mllang: agent codes captured",
               [r["agent_code"] for r in rows] == ["@K", "@C", "@G"])
        _check("mllang: halt values captured",
               [r["halt"] for r in rows] == ["test=pass", "<=>", "risk!high"])
        _check("mllang: token reduction is positive on all rows",
               all(r["reduction_pct"] > 0 for r in rows))
        _check("mllang: json_rpc_chars > response_chars",
               all(r["json_rpc_chars"] > r["response_chars"] for r in rows))

        summary = summarize(rows, cost_per_M=5.0)
        _check("mllang summary: records",
               summary["records"] == 3 and summary["with_mllang_packet"] == 3)
        _check("mllang summary: mean reduction positive",
               summary["mean_reduction_pct"] > 0)
        _check("mllang summary: halt distribution captured",
               len(summary["halt_distribution"]) == 3)
        _check("mllang summary: model distribution captured",
               len(summary["model_distribution"]) == 2)
        _check("mllang summary: agent distribution captured",
               len(summary["agent_distribution"]) == 3)

        # --- Mixed: prose response with packet embedded ---
        log_mixed = os.path.join(tmp, "mixed.jsonl")
        with record(log_mixed, parser="mllang") as r:
            r.observe(
                response=(
                    "Here is the analysis you requested: "
                    "V:0.1.r1; I:mixed; G:{task=classify}; S:{ok=1}; "
                    "N:@K -> finish; H:<=>; P:0.88; EN: Done."
                ),
                model="claude-opus-4-7",
                tokens_in=300,
                tokens_out=120,
                latency_s=3.4,
            )

        rows = [json.loads(l) for l in open(log_mixed)]
        _check("mixed: packet extracted from prose",
               rows[0]["has_mllang_packet"] and rows[0]["confidence"] == 0.88)

        # --- Markdown-fenced packet ---
        log_md = os.path.join(tmp, "md.jsonl")
        md_response = (
            "# Result\n\n"
            "Workflow: classify three lines.\n\n"
            "```mllang\n"
            "V:0.1.r1; I:md-test; G:{task=demo}; S:{ok=1}; "
            "N:@K -> done; H:accept; P:0.77;\n"
            "EN: Done.\n"
            "```\n"
        )
        with record(log_md, parser="mllang") as r:
            r.observe(
                response=md_response,
                model="claude-sonnet-4-6",
                tokens_in=120,
                tokens_out=60,
                latency_s=1.4,
            )
        rows = [json.loads(l) for l in open(log_md)]
        _check("markdown: fenced packet extracted",
               rows[0]["has_mllang_packet"]
               and rows[0]["halt"] == "accept"
               and rows[0]["agent_code"] == "@K")

        # --- Refuses garbage ---
        log_bad = os.path.join(tmp, "bad.jsonl")
        with record(log_bad, parser="mllang") as r:
            r.observe(response="totally unrelated text, no packet", model="x",
                      tokens_in=10, tokens_out=5, latency_s=0.1)
        rows = [json.loads(l) for l in open(log_bad)]
        _check("bad input: not flagged as mllang",
               not rows[0]["has_mllang_packet"])

    print()
    print(f"--- agent-shim E2E: {passed} passed, {failed} failed ---")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
