"""Markdown-embed helpers for MLLANG packets.

Default pattern (summary mode):
    short workflow summary + fenced ```mllang block.

Rationale: when the consumer is an AI, the packet already carries the
state, and the `EN:` shadow line is the human-skim summary. Long prose
duplicates the packet content for a human reader who is rarely going to
read it. Keep the surrounding text tight; let `EN:` do the dual-channel.

Opt-in `mode="verbose"` keeps a long-prose channel above the packet for
human-authored docs (PRs, issues, design notes) where readers do want
the narrative.
"""

from __future__ import annotations

from typing import Optional, Union

from .packet import Packet, compose, parse

VALID_MODES = {"summary", "verbose", "packet_only"}
DEFAULT_FENCE = "mllang"


def embed_in_markdown(
    packet: Union[Packet, str],
    summary: str = "",
    prose: Optional[str] = None,
    mode: str = "summary",
    title: Optional[str] = None,
    fence: str = DEFAULT_FENCE,
) -> str:
    """Return markdown string containing the packet in a fenced block.

    Args:
        packet: Packet object or MLLANG text.
        summary: 1-3 line workflow summary used in `mode="summary"`.
        prose: long-form human-readable text used in `mode="verbose"`.
        mode: "summary" (default), "verbose", or "packet_only".
        title: optional `# Heading` line.
        fence: code-fence language tag (default "mllang").

    Returns:
        Markdown text with the packet embedded.
    """
    if mode not in VALID_MODES:
        raise ValueError(f"mode must be one of {sorted(VALID_MODES)}; got {mode!r}")

    if isinstance(packet, Packet):
        packet_text = compose(packet)
    else:
        packet_text = packet.strip()

    parts: list[str] = []
    if title:
        parts.append(f"# {title}")
    if mode == "summary" and summary:
        parts.append(summary.strip())
    elif mode == "verbose" and prose:
        parts.append(prose.strip())
    parts.append(f"```{fence}\n{packet_text}\n```")
    return "\n\n".join(parts) + "\n"


def extract_summary_and_packet(md_text: str, fence: str = DEFAULT_FENCE) -> tuple[str, Optional[Packet]]:
    """Return (text_before_first_block, parsed_packet | None).

    Useful when a downstream agent wants both the human summary line(s)
    and the structured packet from a summary-mode markdown file.
    """
    import re

    block_re = re.compile(rf"```{re.escape(fence)}\s*\n(.*?)\n```", re.DOTALL)
    m = block_re.search(md_text)
    if not m:
        return md_text.strip(), None
    before = md_text[: m.start()].strip()
    # Strip leading "# title" line if present, keep the rest as summary
    if before.startswith("#"):
        lines = before.splitlines()
        # Drop heading lines from the top until first non-heading
        i = 0
        while i < len(lines) and (lines[i].startswith("#") or not lines[i].strip()):
            i += 1
        before = "\n".join(lines[i:]).strip()
    try:
        p = parse(m.group(1))
    except ValueError:
        p = None
    return before, p
