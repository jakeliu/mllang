#!/usr/bin/env python3
"""End-to-end MCP server test.

Spawns `mllang-mcp-server` as a stdio subprocess and drives it via the
official MCP client. Verifies every tool round-trips through the wire
protocol with a real packet.

Skipped (exit 0 with a message) when the `mcp` package is not installed.
Run conformance/run_conformance.py covers the library directly; this
test covers the integration surface.

Usage:
    pip install 'mllang-protocol[mcp]'
    python conformance/test_mcp_server.py
"""

import asyncio
import json
import sys


def _have_mcp() -> bool:
    try:
        import mcp  # noqa: F401
        from mcp import ClientSession  # noqa: F401
        from mcp.client.stdio import stdio_client, StdioServerParameters  # noqa: F401
    except ImportError:
        return False
    return True


SAMPLE_PACKET = (
    "V:0.1.r1; I:mcp-roundtrip-001; "
    "G:{task=mcp_e2e_test, scope=all_tools}; "
    "S:{server=mllang-mcp-server, transport=stdio}; "
    "D:[spawn_subprocess, drive_each_tool, assert_responses]; "
    "N:@K -> verify; H:test=pass; P:0.90; "
    "A:[mcp_sdk_available];"
)


async def _run() -> int:
    import os as _os
    import tempfile as _tempfile

    from mcp import ClientSession
    from mcp.client.stdio import StdioServerParameters, stdio_client

    # Route mailbox writes to a throwaway dir so the test never touches
    # the user's real ~/.mllang-mailbox/.
    mailbox_tmp = _tempfile.mkdtemp(prefix="mllang_mailbox_test_")
    server_env = _os.environ.copy()
    server_env["MLLANG_MAILBOX_ROOT"] = mailbox_tmp

    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mllang.mcp_server"],
        env=server_env,
    )

    failed = 0
    passed = 0

    def _check(name: str, condition: bool, detail: str = "") -> None:
        nonlocal failed, passed
        if condition:
            print(f"  PASS  {name}")
            passed += 1
        else:
            print(f"  FAIL  {name} {detail}")
            failed += 1

    def _unwrap(r):
        """Pull structured result out of a CallToolResult.

        FastMCP returns scalar results in `content[0].text`, and complex
        results (lists / dicts) in `structuredContent['result']`. Prefer
        the structured form when present, fall back to the text content.
        """
        structured = getattr(r, "structuredContent", None)
        if isinstance(structured, dict) and "result" in structured:
            return structured["result"]
        if r.content:
            try:
                return json.loads(r.content[0].text)
            except (json.JSONDecodeError, AttributeError):
                return r.content[0].text
        return None

    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            # Route mailbox writes to a temp dir so the test never touches ~/.mllang-mailbox
            # (we already initialized the server before this point, so the env var must
            # be set BEFORE stdio_client; do it via params.env if needed in future)

            tools_resp = await session.list_tools()
            tool_names = {t.name for t in tools_resp.tools}
            expected = {
                "mllang_parse",
                "mllang_compose",
                "mllang_validate",
                "mllang_embed_in_markdown",
                "mllang_extract_summary",
                "mllang_sanitize",
                "mllang_spec",
                "mailbox_send",
                "mailbox_check",
                "mailbox_status",
            }
            _check(
                "all 10 tools advertised (7 mllang + 3 mailbox)",
                expected.issubset(tool_names),
                f"missing={expected - tool_names}",
            )

            # mllang_parse
            r = await session.call_tool("mllang_parse", {"text": SAMPLE_PACKET})
            payload = _unwrap(r)
            _check("parse returns thread_id", payload.get("thread_id") == "mcp-roundtrip-001")
            _check("parse returns next_agent", payload.get("next_agent") == "@K -> verify")
            _check("parse returns confidence", abs(payload.get("confidence", 0) - 0.90) < 0.001)
            _check("parse returns halt", payload.get("halt") == "test=pass")

            # mllang_compose roundtrip
            r = await session.call_tool("mllang_compose", {"packet": payload})
            composed = _unwrap(r)
            _check("compose includes thread id", "I:mcp-roundtrip-001" in composed)
            _check("compose includes next agent", "N:@K -> verify" in composed)
            _check("compose includes halt", "H:test=pass" in composed)

            # mllang_validate (clean packet -> empty errors)
            r = await session.call_tool("mllang_validate", {"text": SAMPLE_PACKET})
            errs = _unwrap(r)
            _check("validate empty for clean packet", errs == [])

            # mllang_validate (missing required slot -> errors)
            r = await session.call_tool(
                "mllang_validate",
                {"text": "V:0.1.r1; G:{x=1}; H:<=>;"},
            )
            errs = _unwrap(r)
            _check("validate reports missing slots", isinstance(errs, list) and len(errs) >= 1)

            # mllang_embed_in_markdown summary mode
            r = await session.call_tool(
                "mllang_embed_in_markdown",
                {
                    "packet_text": SAMPLE_PACKET,
                    "summary": "Workflow: drive MCP server end-to-end.",
                    "mode": "summary",
                    "title": "MCP roundtrip",
                },
            )
            md = _unwrap(r)
            _check("embed has title", "# MCP roundtrip" in md)
            _check("embed has summary line", "drive MCP server end-to-end" in md)
            _check("embed has fenced mllang block", "```mllang" in md)

            # mllang_extract_summary roundtrip
            r = await session.call_tool("mllang_extract_summary", {"markdown_text": md})
            extracted = _unwrap(r)
            _check(
                "extract returns summary",
                "drive MCP server end-to-end" in (extracted.get("summary") or ""),
            )
            _check(
                "extract returns packet",
                (extracted.get("packet") or {}).get("thread_id") == "mcp-roundtrip-001",
            )

            # mllang_sanitize at each level
            for level, expect_dict in [
                ("off", False),
                ("shape", True),
                ("structured", True),
                ("full", True),
            ]:
                r = await session.call_tool(
                    "mllang_sanitize",
                    {"text": SAMPLE_PACKET, "level": level},
                )
                resp = _unwrap(r)
                if expect_dict:
                    _check(
                        f"sanitize level={level} returns payload",
                        isinstance(resp, dict) and resp.get("v") == "0.1.r1",
                    )
                else:
                    _check(f"sanitize level={level} returns null", resp is None)

            # sanitize must NEVER leak the goal-value string at shape level
            r = await session.call_tool(
                "mllang_sanitize",
                {"text": SAMPLE_PACKET, "level": "shape"},
            )
            shape_payload = _unwrap(r)
            blob = json.dumps(shape_payload)
            _check(
                "shape payload does not leak goal value",
                "mcp_e2e_test" not in blob,
            )
            _check(
                "shape payload hashes thread id",
                shape_payload.get("thread_hash", "").startswith("<I:hash:"),
            )

            # mllang_spec returns something
            r = await session.call_tool("mllang_spec", {})
            spec_text = _unwrap(r)
            _check(
                "spec returns text containing MLLANG",
                isinstance(spec_text, str) and "MLLANG" in spec_text,
            )

            # ── Mailbox round-trip ────────────────────────────────────
            # 1. Claude side sends to codex's inbox
            r = await session.call_tool(
                "mailbox_send",
                {
                    "to": "codex",
                    "body": SAMPLE_PACKET,
                    "from_": "claude",
                    "subject": "diff review request",
                },
            )
            send_result = _unwrap(r)
            _check(
                "mailbox_send returns msg_id + path",
                isinstance(send_result, dict)
                and "msg_id" in send_result
                and "path" in send_result,
            )

            # 2. Status shows codex has 1 unread
            r = await session.call_tool("mailbox_status", {})
            status = _unwrap(r)
            _check(
                "mailbox_status shows codex has 1 unread",
                status.get("boxes", {}).get("codex", {}).get("unread") == 1,
            )

            # 3. Codex side reads its inbox
            r = await session.call_tool("mailbox_check", {"box": "codex"})
            msgs = _unwrap(r)
            _check(
                "mailbox_check returns 1 message",
                isinstance(msgs, list) and len(msgs) == 1,
            )
            _check(
                "mailbox_check message has correct from / subject / body",
                msgs[0].get("from") == "claude"
                and msgs[0].get("subject") == "diff review request"
                and "V:0.1.r1" in msgs[0].get("body", ""),
            )

            # 4. Codex re-checks → empty (mark_read=True consumed it)
            r = await session.call_tool("mailbox_check", {"box": "codex"})
            msgs2 = _unwrap(r)
            _check(
                "mailbox_check after read returns empty (default mark_read)",
                isinstance(msgs2, list) and len(msgs2) == 0,
            )

            # 5. Codex replies to claude
            r = await session.call_tool(
                "mailbox_send",
                {
                    "to": "claude",
                    "body": "Reviewed. Looks good.",
                    "from_": "codex",
                    "subject": "re: diff review request",
                },
            )
            _check("mailbox reply lands in claude's inbox", _unwrap(r).get("msg_id"))

            # 6. Claude reads codex's reply
            r = await session.call_tool("mailbox_check", {"box": "claude"})
            reply_msgs = _unwrap(r)
            _check(
                "claude reads codex's reply",
                len(reply_msgs) == 1 and reply_msgs[0].get("from") == "codex",
            )

            # 7. unread_only=False also returns read messages
            r = await session.call_tool(
                "mailbox_check",
                {"box": "codex", "unread_only": False, "mark_read": False},
            )
            all_msgs = _unwrap(r)
            _check(
                "mailbox_check unread_only=False returns history",
                len(all_msgs) >= 1,
            )

    print()
    print(f"--- MCP E2E: {passed} passed, {failed} failed ---")
    return 0 if failed == 0 else 1


def main() -> int:
    if not _have_mcp():
        print("MCP SDK not installed — skipping end-to-end test.")
        print("To run: pip install 'mllang-protocol[mcp]'")
        return 0
    return asyncio.run(_run())


if __name__ == "__main__":
    sys.exit(main())
