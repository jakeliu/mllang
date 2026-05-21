"""MLLANG MCP server.

Exposes the parser library as a set of Model Context Protocol tools.
Compatible with Claude Desktop, Cline, and any MCP-aware client.

Install:
    pip install 'mllang-protocol[mcp]'

Run (stdio transport, the default Claude-Desktop expects):
    mllang-mcp-server

Tools exposed:
    mllang_parse              text → packet dict
    mllang_compose            packet dict → MLLANG text
    mllang_validate           text → list[str] of validation errors
    mllang_embed_in_markdown  build markdown with embedded packet
    mllang_extract_summary    pull (summary, packet) from markdown
    mllang_sanitize           run telemetry redaction
    mllang_spec               return the locked v0.1 spec text
"""

from __future__ import annotations

import dataclasses
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    from mcp.server.fastmcp import FastMCP
except ImportError as e:  # pragma: no cover
    raise ImportError(
        "MLLANG MCP server requires the optional 'mcp' dependency. "
        "Install with: pip install 'mllang-protocol[mcp]'"
    ) from e

from .embed import embed_in_markdown, extract_summary_and_packet
from .packet import Packet, compose, extract_from_markdown, parse, validate
from .sanitize import sanitize

mcp = FastMCP("mllang")


def _packet_to_dict(p: Packet) -> Dict[str, Any]:
    """Convert a Packet dataclass into a JSON-safe dict."""
    return dataclasses.asdict(p)


def _dict_to_packet(d: Dict[str, Any]) -> Packet:
    """Construct a Packet from a dict (accepts the same keys _packet_to_dict emits)."""
    field_names = {f.name for f in dataclasses.fields(Packet)}
    cleaned = {k: v for k, v in d.items() if k in field_names}
    return Packet(**cleaned)


@mcp.tool()
def mllang_parse(text: str) -> Dict[str, Any]:
    """Parse MLLANG packet text into structured fields.

    Accepts either a bare MLLANG line (with optional EN: shadow line)
    or a packet wrapped in a ```mllang fenced block.
    """
    stripped = text.strip()
    if stripped.startswith("```"):
        packets = extract_from_markdown(stripped)
        if not packets:
            raise ValueError("No mllang fenced block found in input")
        p = packets[0]
    else:
        p = parse(stripped)
    return _packet_to_dict(p)


@mcp.tool()
def mllang_compose(packet: Dict[str, Any]) -> str:
    """Compose MLLANG text from a packet dict.

    The packet dict shape matches what mllang_parse returns.
    """
    return compose(_dict_to_packet(packet))


@mcp.tool()
def mllang_validate(text: str) -> List[str]:
    """Validate an MLLANG packet. Returns a list of error strings; empty list = valid."""
    return validate(parse(text))


@mcp.tool()
def mllang_embed_in_markdown(
    packet_text: str,
    summary: str = "",
    prose: str = "",
    mode: str = "summary",
    title: str = "",
) -> str:
    """Embed an MLLANG packet inside a markdown document.

    Modes:
        summary     (default) title + one-line workflow summary + fenced block
        verbose     title + long prose + fenced block
        packet_only fenced block alone
    """
    return embed_in_markdown(
        packet_text,
        summary=summary,
        prose=prose or None,
        mode=mode,
        title=title or None,
    )


@mcp.tool()
def mllang_extract_summary(markdown_text: str) -> Dict[str, Any]:
    """Pull the (summary, packet) pair out of a summary-mode markdown file."""
    summary, p = extract_summary_and_packet(markdown_text)
    return {
        "summary": summary,
        "packet": _packet_to_dict(p) if p is not None else None,
    }


@mcp.tool()
def mllang_sanitize(text: str, level: str = "shape") -> Optional[Dict[str, Any]]:
    """Run telemetry-safe sanitization on an MLLANG packet.

    Levels:
        off         returns null (nothing sent)
        shape       slot presence + halt + confidence + agent code (default)
        structured  + map keys + verb names + counts
        full        + redacted values + assumption prefixes

    Returns null when the level is off OR a leak detector refuses the payload.
    """
    return sanitize(text, level=level)


@mcp.tool()
def mllang_spec() -> str:
    """Return the locked v0.1 spec text for downstream LLMs that need it as context."""
    spec_path = Path(__file__).resolve().parents[2] / "spec" / "MLLANG_v0.1.locked.md"
    if spec_path.exists():
        return spec_path.read_text(encoding="utf-8")
    return (
        "MLLANG v0.1 spec not bundled with this install. "
        "See https://github.com/jakeliu/mllang/blob/main/spec/MLLANG_v0.1.locked.md"
    )


# ── Mailbox: cross-CLI message channel ──────────────────────────────────
#
# Two agents (e.g. Claude Code and Codex CLI) both configure this MCP
# server and share ~/.mllang-mailbox/ on disk. `mailbox_send` writes to
# the recipient's inbox; `mailbox_check` reads + acks. Filesystem is the
# transport; MCP is the operation API. No long-running daemon.
#
# Layout:
#   ~/.mllang-mailbox/<box>/inbox/<ts>-<msg_id>.json     unread
#   ~/.mllang-mailbox/<box>/read/<ts>-<msg_id>.json      read (ack'd)

import time as _time
import uuid as _uuid
import json as _json
import os as _os

_MAILBOX_ROOT = Path(_os.environ.get("MLLANG_MAILBOX_ROOT", str(Path.home() / ".mllang-mailbox")))
_MY_BOX = _os.environ.get("MLLANG_MY_BOX", "me")
_NOTIFY_MODE = _os.environ.get("MLLANG_NOTIFY", "desktop").lower()  # desktop | off


def _notify_desktop(to: str, from_: str, subject: str) -> None:
    """Best-effort desktop notification on the local machine. Silent fallthrough on any error
    (notifications are a UX bonus; never block mail delivery on a missing command).
    """
    if _NOTIFY_MODE == "off":
        return
    import platform
    import shlex
    import subprocess as _sp

    title = f"mllang: new mail for {to}"
    body = f"from {from_}" + (f": {subject}" if subject else "")

    system = platform.system()
    try:
        if system == "Darwin":
            # macOS: osascript banner. Escape double quotes in user fields.
            safe_body = body.replace('"', '\\"')
            safe_title = title.replace('"', '\\"')
            _sp.run(
                [
                    "osascript",
                    "-e",
                    f'display notification "{safe_body}" with title "{safe_title}" sound name "Glass"',
                ],
                check=False,
                timeout=2,
                capture_output=True,
            )
        elif system == "Linux":
            # Linux: notify-send if installed
            _sp.run(
                ["notify-send", "--app-name=mllang", title, body],
                check=False,
                timeout=2,
                capture_output=True,
            )
        elif system == "Windows":
            # Windows 10+: native UWP toast via PowerShell. Falls back silent if
            # PowerShell isn't on PATH (rare) or the WinRT class lookup fails.
            safe_title = title.replace('"', "'").replace("`", "'")
            safe_body = body.replace('"', "'").replace("`", "'")
            ps_cmd = (
                "[Windows.UI.Notifications.ToastNotificationManager, "
                "Windows.UI.Notifications, ContentType=WindowsRuntime] | Out-Null;"
                "$t = [Windows.UI.Notifications.ToastNotificationManager]"
                "::GetTemplateContent([Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
                "$n = $t.GetElementsByTagName('text');"
                f'$n[0].AppendChild($t.CreateTextNode("{safe_title}")) | Out-Null;'
                f'$n[1].AppendChild($t.CreateTextNode("{safe_body}")) | Out-Null;'
                "$toast = [Windows.UI.Notifications.ToastNotification]::new($t);"
                "[Windows.UI.Notifications.ToastNotificationManager]"
                "::CreateToastNotifier('mllang').Show($toast)"
            )
            _sp.run(
                ["powershell", "-NoProfile", "-Command", ps_cmd],
                check=False,
                timeout=3,
                capture_output=True,
            )
    except (FileNotFoundError, _sp.SubprocessError, OSError):
        pass


def _box_dir(box: str, sub: str) -> Path:
    safe = "".join(c for c in box if c.isalnum() or c in ("-", "_")) or "default"
    d = _MAILBOX_ROOT / safe / sub
    d.mkdir(parents=True, exist_ok=True)
    return d


@mcp.tool()
def mailbox_send(
    to: str,
    body: str,
    from_: str = "",
    subject: str = "",
    tags: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Drop a message into another agent's inbox at ~/.mllang-mailbox/<to>/inbox/.

    Body can be any text — including an MLLANG packet. The recipient
    calls mailbox_check(box="<to>") to read.

    `from_` defaults to the session's own box name (env var MLLANG_MY_BOX),
    so the recipient can reply by addressing the from_ value as `to`. If
    MLLANG_MY_BOX is not set, falls back to "me".

    Returns: {msg_id, path, ts, to, from_}.
    """
    if not from_:
        from_ = _os.environ.get("MLLANG_MY_BOX") or "me"
    ts = _time.strftime("%Y-%m-%dT%H:%M:%SZ", _time.gmtime())
    msg_id = _uuid.uuid4().hex[:12]
    payload = {
        "msg_id": msg_id,
        "ts": ts,
        "from": from_,
        "to": to,
        "subject": subject,
        "body": body,
        "tags": tags or {},
    }
    fname = f"{ts.replace(':', '-')}-{msg_id}.json"
    path = _box_dir(to, "inbox") / fname
    path.write_text(_json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    _notify_desktop(to, from_, subject)
    return {"msg_id": msg_id, "path": str(path), "ts": ts, "to": to, "from_": from_}


@mcp.tool()
def mailbox_check(
    box: str = "",
    unread_only: bool = True,
    since: str = "",
    mark_read: bool = True,
) -> List[Dict[str, Any]]:
    """Read messages from `box`'s inbox.

    Args:
        box: which inbox to read (the agent's own name). When empty,
            falls back to the session's MLLANG_MY_BOX env var, then to "me".
        unread_only: when True (default), only return messages in /inbox/;
            when False, also include /read/.
        since: ISO timestamp filter — only messages with ts > since.
        mark_read: when True (default), move returned messages from
            /inbox/ to /read/ so they aren't returned again.

    Returns: list of message dicts (msg_id, ts, from, to, subject, body, tags).
    """
    if not box:
        box = _os.environ.get("MLLANG_MY_BOX") or "me"
    inbox = _box_dir(box, "inbox")
    read_dir = _box_dir(box, "read")
    sources = [inbox] + ([read_dir] if not unread_only else [])

    messages: List[Dict[str, Any]] = []
    for src in sources:
        for fpath in sorted(src.glob("*.json")):
            try:
                msg = _json.loads(fpath.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if since and msg.get("ts", "") <= since:
                continue
            messages.append(msg)
            if mark_read and src == inbox:
                try:
                    fpath.rename(read_dir / fpath.name)
                except OSError:
                    pass
    return messages


@mcp.tool()
def mailbox_status() -> Dict[str, Any]:
    """Quick stats on the local mailbox root. Useful to see which boxes have unread messages."""
    if not _MAILBOX_ROOT.exists():
        return {"root": str(_MAILBOX_ROOT), "boxes": {}}
    out: Dict[str, Any] = {"root": str(_MAILBOX_ROOT), "boxes": {}}
    for box_dir in sorted(_MAILBOX_ROOT.iterdir()):
        if not box_dir.is_dir():
            continue
        inbox = box_dir / "inbox"
        read = box_dir / "read"
        out["boxes"][box_dir.name] = {
            "unread": len(list(inbox.glob("*.json"))) if inbox.exists() else 0,
            "read": len(list(read.glob("*.json"))) if read.exists() else 0,
        }
    return out


def main() -> None:
    """Console-script entry point. Runs the stdio MCP server."""
    mcp.run()


def mailbox_cli() -> None:
    """Shell-friendly mailbox CLI — direct use without MCP.

    Usage:
        mllang-mailbox send <to> <body> [--from NAME] [--subject TEXT]
        mllang-mailbox check <box> [--all] [--keep-unread]
        mllang-mailbox status
    """
    import argparse
    import sys as _sys

    p = argparse.ArgumentParser(prog="mllang-mailbox")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp_send = sub.add_parser("send", help="Send a message to <to>'s inbox")
    sp_send.add_argument("to")
    sp_send.add_argument("body")
    sp_send.add_argument(
        "--from",
        dest="from_",
        default="",
        help="Sender box name. Defaults to MLLANG_MY_BOX env, then 'me'.",
    )
    sp_send.add_argument("--subject", default="")

    sp_check = sub.add_parser("check", help="Read messages from <box>'s inbox")
    sp_check.add_argument(
        "box",
        nargs="?",
        default="",
        help="Box to read. Defaults to MLLANG_MY_BOX env, then 'me'.",
    )
    sp_check.add_argument("--all", action="store_true", help="Include already-read")
    sp_check.add_argument("--keep-unread", action="store_true", help="Don't mark as read")

    sub.add_parser("status", help="Show mailbox stats")

    args = p.parse_args()

    if args.cmd == "send":
        out = mailbox_send(to=args.to, body=args.body, from_=args.from_, subject=args.subject)
        _sys.stdout.write(_json.dumps(out, indent=2) + "\n")
    elif args.cmd == "check":
        out = mailbox_check(
            box=args.box,
            unread_only=not args.all,
            mark_read=not args.keep_unread,
        )
        _sys.stdout.write(_json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    elif args.cmd == "status":
        out = mailbox_status()
        _sys.stdout.write(_json.dumps(out, indent=2) + "\n")


if __name__ == "__main__":
    main()
