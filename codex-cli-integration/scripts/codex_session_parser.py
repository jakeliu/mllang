#!/usr/bin/env python3
"""Parse Codex rollout JSONL and write shim-engine records.

Conservative Path 1 for Codex CLI:
- no hooks,
- no sub-agent cost slicing,
- one shim-engine row per completed Codex turn.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable, Iterator, Optional

from extract_budget import Budget, extract_budget

DEFAULT_LOG_PATH = os.path.expanduser(
    os.environ.get("MLLANG_CODEX_LOG", "~/.codex/mllang-shim/session.jsonl")
)
DEFAULT_SESSIONS_DIR = os.path.expanduser("~/.codex/sessions")


def _now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_jsonl_lines(lines: Iterable[str]) -> Iterator[dict[str, Any]]:
    for line in lines:
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            yield row


def _load_path(path: Path) -> list[dict[str, Any]]:
    try:
        with path.open(encoding="utf-8") as fh:
            return list(_read_jsonl_lines(fh))
    except FileNotFoundError:
        return []


def find_latest_rollout(sessions_dir: str = DEFAULT_SESSIONS_DIR) -> Optional[Path]:
    root = Path(os.path.expanduser(sessions_dir))
    if not root.exists():
        return None
    newest: Optional[Path] = None
    newest_mtime = -1.0
    for path in root.rglob("rollout-*.jsonl"):
        try:
            mtime = path.stat().st_mtime
        except OSError:
            continue
        if mtime > newest_mtime:
            newest = path
            newest_mtime = mtime
    return newest


def _usage_from_token_count(payload: dict[str, Any]) -> Optional[dict[str, Any]]:
    info = payload.get("info")
    if not isinstance(info, dict):
        return None
    usage = info.get("last_token_usage") or info.get("total_token_usage")
    return usage if isinstance(usage, dict) else None


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _coerce_latency_ms(value: Any) -> float:
    try:
        return round(float(value) / 1000.0, 4)
    except (TypeError, ValueError):
        return 0.0


def _import_recorder():
    try:
        from shim_engine import Recorder
    except ImportError:
        return None
    return Recorder


def _choose_budget(
    budget: Budget,
    usage: Optional[dict[str, Any]],
    task_complete: dict[str, Any],
) -> tuple[int, int, float, str]:
    session_latency = _coerce_latency_ms(task_complete.get("duration_ms"))
    if budget.present and (budget.tokens_in or budget.tokens_out):
        return (
            budget.tokens_in,
            budget.tokens_out,
            budget.latency_s or session_latency,
            "B-slot",
        )
    if usage:
        return (
            _coerce_int(usage.get("input_tokens")),
            _coerce_int(usage.get("output_tokens")),
            session_latency,
            "session-token_count",
        )
    return 0, 0, session_latency, "none"


def parse_rows(
    rows: Iterable[dict[str, Any]],
    *,
    log_path: str = DEFAULT_LOG_PATH,
    seen_turn_ids: Optional[set[str]] = None,
    require_shim: bool = True,
) -> list[dict[str, Any]]:
    """Parse rows and write shim records.

    Returns the records written. Malformed or incomplete rows are skipped.
    """
    Recorder = _import_recorder()
    if Recorder is None:
        if require_shim:
            raise RuntimeError(
                "shim-engine is not installed. Install: pip install 'shim-engine[mllang]'"
            )
        return []

    session_meta: dict[str, Any] = {}
    last_usage: Optional[dict[str, Any]] = None
    last_agent_message = ""
    written: list[dict[str, Any]] = []
    seen_turn_ids = seen_turn_ids if seen_turn_ids is not None else set()

    recorder = Recorder(path=log_path, parser="mllang")

    for row in rows:
        row_type = row.get("type")
        payload = row.get("payload")
        if not isinstance(payload, dict):
            continue

        if row_type == "session_meta":
            session_meta = payload
            continue

        if row_type != "event_msg":
            continue

        event_type = payload.get("type")
        if event_type == "token_count":
            usage = _usage_from_token_count(payload)
            if usage:
                last_usage = usage
            continue

        if event_type == "agent_message":
            message = payload.get("message")
            if isinstance(message, str):
                last_agent_message = message
            continue

        if event_type != "task_complete":
            continue

        turn_id = str(payload.get("turn_id", ""))
        if turn_id and turn_id in seen_turn_ids:
            continue
        if turn_id:
            seen_turn_ids.add(turn_id)

        agent_text = last_agent_message or payload.get("last_agent_message") or ""
        if not isinstance(agent_text, str):
            agent_text = str(agent_text)

        budget = extract_budget(agent_text)
        tokens_in, tokens_out, latency_s, budget_source = _choose_budget(
            budget, last_usage, payload
        )

        tags = {
            "source": "codex-cli",
            "codex_cli_version": str(session_meta.get("cli_version", "unknown")),
            "codex_session_id": str(session_meta.get("id", "")),
            "turn_id": turn_id,
            "originator": str(session_meta.get("originator", "")),
            "cwd": str(session_meta.get("cwd", "")),
            "capture_boundary": "turn",
            "budget_source": budget_source,
            "ts": _now_iso(),
        }
        model = f"codex-cli:{session_meta.get('model_provider', 'unknown') or 'unknown'}"

        record = recorder.observe(
            response=agent_text,
            model=model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_s=latency_s,
            tags=tags,
        )
        written.append(record)

    return written


def parse_file(path: Path, *, log_path: str, seen_turn_ids: Optional[set[str]] = None) -> int:
    records = parse_rows(_load_path(path), log_path=log_path, seen_turn_ids=seen_turn_ids)
    return len(records)


def _watch_latest(log_path: str, interval_s: float, sessions_dir: str) -> int:
    seen_turn_ids: set[str] = set()
    current: Optional[Path] = None
    print("Watching Codex sessions for completed turns...", file=sys.stderr)
    while True:
        latest = find_latest_rollout(sessions_dir)
        if latest is None:
            time.sleep(interval_s)
            continue
        if latest != current:
            current = latest
            print(f"Watching {current}", file=sys.stderr)
        try:
            count = parse_file(latest, log_path=log_path, seen_turn_ids=seen_turn_ids)
            if count:
                print(f"Recorded {count} completed Codex turn(s).", file=sys.stderr)
        except RuntimeError as exc:
            print(str(exc), file=sys.stderr)
            return 2
        time.sleep(interval_s)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codex_session_parser.py",
        description="Parse Codex rollout JSONL and write shim-engine records.",
    )
    parser.add_argument("path", nargs="?", help="path to a Codex rollout JSONL file")
    parser.add_argument("--latest", action="store_true", help="parse newest ~/.codex/sessions rollout")
    parser.add_argument("--watch", action="store_true", help="poll newest rollout and record new task_complete events")
    parser.add_argument("--stdin-events", action="store_true", help="read Codex --json events from stdin")
    parser.add_argument("--sessions-dir", default=DEFAULT_SESSIONS_DIR, help="Codex sessions root")
    parser.add_argument("--log-path", default=DEFAULT_LOG_PATH, help="shim-engine output JSONL")
    parser.add_argument("--poll-interval", type=float, default=2.0, help="watch polling interval seconds")
    return parser


def main(argv: Optional[Iterable[str]] = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)

    try:
        if args.watch:
            return _watch_latest(args.log_path, args.poll_interval, args.sessions_dir)

        if args.stdin_events:
            count = len(parse_rows(_read_jsonl_lines(sys.stdin), log_path=args.log_path))
            print(f"Recorded {count} completed Codex turn(s).")
            return 0

        path: Optional[Path]
        if args.latest:
            path = find_latest_rollout(args.sessions_dir)
            if path is None:
                print("No Codex rollout JSONL files found.", file=sys.stderr)
                return 1
        elif args.path:
            path = Path(os.path.expanduser(args.path))
        else:
            build_parser().print_usage(sys.stderr)
            return 2

        count = parse_file(path, log_path=args.log_path)
        print(f"Recorded {count} completed Codex turn(s) from {path}.")
        return 0
    except RuntimeError as exc:
        print(str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
