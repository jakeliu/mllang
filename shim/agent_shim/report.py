"""agent-shim CLI report.

Usage:
    agent-shim-report <log.jsonl>
    agent-shim-report --json <log.jsonl>          # machine-readable summary
    agent-shim-report --cost-per-M 8 <log.jsonl>  # override cost assumption

Reads a JSONL file produced by agent_shim.Recorder.observe() and prints an
aggregated summary: counts, mean token reduction (when MLLANG packets are
present), latency percentiles, halt distribution, model distribution,
estimated cost saved.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter
from typing import Any, Dict, Iterable, List, Optional


def _read_jsonl(path: str) -> List[Dict[str, Any]]:
    rows: List[Dict[str, Any]] = []
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _percentile(values: List[float], pct: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = max(0, min(len(s) - 1, int(pct * (len(s) - 1))))
    return s[k]


def _format_distribution(counter: Counter, total: int, top: int = 5) -> str:
    parts = []
    for value, count in counter.most_common(top):
        pct = round(100 * count / total) if total else 0
        parts.append(f"{value or '(none)'} {pct}%")
    return " | ".join(parts) if parts else "(none)"


def summarize(rows: List[Dict[str, Any]], cost_per_M: Optional[float] = None) -> Dict[str, Any]:
    if not rows:
        return {"records": 0}

    n = len(rows)
    has_mllang = sum(1 for r in rows if r.get("has_mllang_packet"))
    reductions = [r["reduction_pct"] for r in rows if r.get("has_mllang_packet")]
    latencies = [r.get("latency_s", 0.0) for r in rows if r.get("latency_s")]
    tokens_in_total = sum(r.get("tokens_in", 0) for r in rows)
    tokens_out_total = sum(r.get("tokens_out", 0) for r in rows)
    tokens_saved_total = sum(r.get("tokens_saved_est", 0) for r in rows)
    cost_sum = sum(r.get("cost_estimate_usd", 0.0) for r in rows)
    confidences = [r["confidence"] for r in rows if r.get("confidence")]

    halts = Counter(r.get("halt", "") for r in rows if r.get("halt"))
    models = Counter(r.get("model", "") for r in rows if r.get("model"))
    agents = Counter(r.get("agent_code", "") for r in rows if r.get("agent_code"))

    cost_per_M_effective = cost_per_M if cost_per_M is not None else (
        rows[0].get("cost_per_M") if rows else 5.0
    )
    if cost_per_M_effective is None:
        cost_per_M_effective = 5.0
    dollars_saved = tokens_saved_total / 1_000_000 * cost_per_M_effective

    return {
        "records": n,
        "with_mllang_packet": has_mllang,
        "mean_reduction_pct": round(statistics.mean(reductions), 1) if reductions else 0.0,
        "tokens_in_total": tokens_in_total,
        "tokens_out_total": tokens_out_total,
        "tokens_saved_total": tokens_saved_total,
        "estimated_dollars_saved": round(dollars_saved, 2),
        "estimated_dollars_spent": round(cost_sum, 4),
        "latency_p50_s": round(_percentile(latencies, 0.50), 3) if latencies else 0.0,
        "latency_p99_s": round(_percentile(latencies, 0.99), 3) if latencies else 0.0,
        "mean_confidence": round(statistics.mean(confidences), 3) if confidences else 0.0,
        "halt_distribution": dict(halts.most_common(5)),
        "model_distribution": dict(models.most_common(5)),
        "agent_distribution": dict(agents.most_common(5)),
    }


def _format_text(summary: Dict[str, Any], path: str, cost_per_M: float) -> str:
    n = summary["records"]
    if n == 0:
        return f"{path}: no records"

    lines = []
    lines.append(f"{n} packets logged ({path})")
    if summary["with_mllang_packet"]:
        lines.append(
            f"mean token reduction:  {summary['mean_reduction_pct']:.1f}% "
            f"vs JSON-RPC equivalent  ({summary['with_mllang_packet']}/{n} packets MLLANG-tagged)"
        )
        lines.append(f"estimated tokens saved: {summary['tokens_saved_total']:,}")
        lines.append(
            f"estimated $$ saved:    ${summary['estimated_dollars_saved']:.2f} "
            f"@ ${cost_per_M:.2f}/M tokens"
        )
    else:
        lines.append("(no MLLANG packets detected — install agent-shim[mllang] for richer signal)")
    lines.append(
        f"tokens in/out:         {summary['tokens_in_total']:,} / {summary['tokens_out_total']:,}"
    )
    lines.append(f"estimated $$ spent:    ${summary['estimated_dollars_spent']:.4f}")
    lines.append(
        f"p50 latency:           {summary['latency_p50_s']:.2f}s    "
        f"p99: {summary['latency_p99_s']:.2f}s"
    )
    if summary["mean_confidence"]:
        lines.append(f"mean P:                {summary['mean_confidence']:.2f}")

    def fmt(d):
        total = sum(d.values()) or 1
        parts = [f"{k or '(none)'} {round(100*v/total)}%" for k, v in d.items()]
        return " | ".join(parts) if parts else "(none)"

    if summary["halt_distribution"]:
        lines.append(f"halt distribution:     {fmt(summary['halt_distribution'])}")
    if summary["model_distribution"]:
        lines.append(f"model distribution:    {fmt(summary['model_distribution'])}")
    if summary["agent_distribution"]:
        lines.append(f"agent distribution:    {fmt(summary['agent_distribution'])}")

    return "\n".join(lines)


def main(argv: Optional[Iterable[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="agent-shim-report",
        description="Aggregate metrics from an agent-shim JSONL log.",
    )
    parser.add_argument("path", help="path to agent_shim JSONL log")
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable JSON summary instead of text",
    )
    parser.add_argument(
        "--cost-per-M",
        type=float,
        default=5.0,
        help="cost in USD per 1M tokens (default 5.0)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    rows = _read_jsonl(args.path)
    summary = summarize(rows, cost_per_M=args.cost_per_M)

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(_format_text(summary, args.path, args.cost_per_M))

    return 0


if __name__ == "__main__":
    sys.exit(main())
