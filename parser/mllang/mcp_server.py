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


def main() -> None:
    """Console-script entry point. Runs the stdio MCP server."""
    mcp.run()


if __name__ == "__main__":
    main()
