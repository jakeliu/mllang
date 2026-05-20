---
layout: default
title: Bootstrap — 3-layer setup
---

# Bootstrap — 3-layer setup

Getting an LLM (Claude / GPT / Gemini / Gemma / DeepSeek / Kimi / Qwen / etc.) to actually emit MLLANG v0.1 packets is a three-layer problem.

Each layer is a different way the spec text reaches the model. You stack as many layers as your client supports; whichever fires first wins.

---

## Layer 1 — Per-task injection (always works)

The spec is pasted at the **start of the task message** by the orchestrator or queue worker before the model reads anything else.

- Paste-ready bootstrap: [`bootstrap/full_session_init.md`](https://github.com/jakeliu/mllang/blob/main/bootstrap/full_session_init.md)
- Short variant: [`bootstrap/session_init.md`](https://github.com/jakeliu/mllang/blob/main/bootstrap/session_init.md)
- Role-specific: [`orchestrator.md`](https://github.com/jakeliu/mllang/blob/main/bootstrap/orchestrator.md) / [`critic.md`](https://github.com/jakeliu/mllang/blob/main/bootstrap/critic.md) / [`implementer.md`](https://github.com/jakeliu/mllang/blob/main/bootstrap/implementer.md) / [`synthesizer.md`](https://github.com/jakeliu/mllang/blob/main/bootstrap/synthesizer.md)

Programmatic injection (Python):

```python
BOOTSTRAP = open("bootstrap/full_session_init.md").read()
TASK = "Classify these 3 lines: ..."
message = BOOTSTRAP + "\n---\n\n" + TASK
```

Pros: works with **any** model — closed APIs, local weights, web tabs, anything.
Cons: pays the bootstrap-token cost on every task.

---

## Layer 2 — One-click / hotkey injection (saves keystrokes)

A button or hotkey injects the bootstrap into the current chat session. Useful when you talk to web UIs (chat.openai.com, claude.ai, gemini.google.com, krater.ai, chat.deepseek.com, kimi.moonshot.cn, qwen.ai).

This repo does **not** ship a browser extension. The Chrome companion that the author uses is internal-tooling, not open-source. Public alternatives:

### macOS — clipboard helper

Add a function to your shell profile (`~/.zshrc` / `~/.bashrc`):

```bash
mllang-bootstrap() {
  python3 -c "from importlib.resources import files; import mllang; print(open(__import__('pathlib').Path(mllang.__file__).parent.parent.parent / 'bootstrap' / 'full_session_init.md').read())" 2>/dev/null \
    || curl -s https://raw.githubusercontent.com/jakeliu/mllang/main/bootstrap/full_session_init.md
}
```

Then:

```bash
mllang-bootstrap | pbcopy   # macOS — bootstrap in clipboard
```

Paste with `Cmd+V` in the chat tab. ~3 seconds total.

### Linux

```bash
mllang-bootstrap | xclip -selection clipboard
```

### Cross-platform alternative — keyboard expander

Tools like Espanso / TextExpander can map a trigger (e.g. `:mllang`) to expand the full bootstrap text inline. Drop the contents of `bootstrap/full_session_init.md` into a snippet.

### Browser extension — write your own (optional)

If you want a one-click button in your browser, write a 50-line Manifest V3 extension that fetches `https://raw.githubusercontent.com/jakeliu/mllang/main/bootstrap/full_session_init.md` and inserts it into the active text area. The project does not ship one because the upstream chat UIs change often and a maintained extension has ongoing surface area cost.

---

## Layer 3 — Anchor files (always-on, no paste needed)

Some AI clients auto-load a known file from the project root. If you put a bootstrap pointer in those files, the model arrives pre-aware of MLLANG.

This repo ships these anchors:

| Client | File | Behavior |
|--------|------|----------|
| Codex / OpenAI agents / Cursor / Cline | [`AGENTS.md`](https://github.com/jakeliu/mllang/blob/main/AGENTS.md) | Joint Google/OpenAI/Cursor standard. Auto-loaded by Codex CLI, Cursor, Cline. |
| Claude Code | [`CLAUDE.md`](https://github.com/jakeliu/mllang/blob/main/CLAUDE.md) | Auto-loaded by Claude Code at session start. |
| Gemini CLI | [`GEMINI.md`](https://github.com/jakeliu/mllang/blob/main/GEMINI.md) | Auto-loaded by `gemini-cli` when present in the repo. |
| Cursor | [`.cursorrules`](https://github.com/jakeliu/mllang/blob/main/.cursorrules) | Auto-loaded by Cursor. |

Each anchor file points at `bootstrap/full_session_init.md` as the single source of truth. The anchor file is short; the bootstrap is canonical.

### Chinese models — anchor convention status

As of 2026-05-20, the Chinese model ecosystem does not yet have a widely-adopted anchor-file convention equivalent to AGENTS.md / CLAUDE.md:

| Model | Anchor file? | Recommended approach |
|-------|--------------|----------------------|
| DeepSeek V3 (chat.deepseek.com / API) | None standard | Set system prompt = `bootstrap/full_session_init.md` contents, OR paste at task start (Layer 1) |
| Kimi K2.6 (kimi.moonshot.cn / API) | None standard | Same — system prompt or Layer 1 paste |
| Qwen 3+ (qwen.ai / DashScope API) | None standard. Their `qwen-code` IDE plugin reads project-level config but the convention is unstable. | System prompt or Layer 1 paste |
| GLM-5 (Zhipu / chatglm.cn) | None standard | System prompt or Layer 1 paste |
| Minimax 2.7 | None standard | System prompt or Layer 1 paste |

**Workaround:** for any Chinese model, copy the contents of `bootstrap/full_session_init.md` into the model's **system prompt** field. That's the closest equivalent to Layer 3 — the bootstrap is always present, on every message, with no paste cost per turn.

If a Chinese model ecosystem adopts an anchor-file convention (e.g. `QWEN.md`, `DEEPSEEK.md`), open a PR to add it to this list and ship a parallel anchor file in the repo.

---

## Layer priority

If all three layers are present, the model sees:

```
[Layer 3 anchor]  ← always-loaded by client (AGENTS.md / CLAUDE.md / GEMINI.md)
[Layer 2 paste]   ← clipboard / extension button at session start
[Layer 1 inject]  ← per-task prefix from your orchestrator
[task body]       ← the actual user request
```

Stacking is safe (the spec content is the same in all three) but redundant. Pick the lowest-effort layer that works for your client and skip the rest.

---

## Confirmation packet

Whichever layer delivers the bootstrap, the model should respond with one MLLANG packet acknowledging the spec is understood (template at the bottom of `bootstrap/full_session_init.md`):

```
V:0.1.r1; I:bootstrap-ack; G:{task=acknowledge_spec};
S:{spec_version=0.1, slots_understood=16, ops_understood=19, halt_enum=9-way};
D:[ready_to_route]; N:@H -> proceed; H:<=>; P:<honest float>;
EN: MLLANG v0.1 spec acknowledged, ready to route packets.
```

If the packet parses with `python3 -c "from mllang import parse, validate; print(validate(parse(open('ack.txt').read())))"` and returns `[]` errors, the model is ratified for this session.

---

## Quick reference

| Need | Use |
|------|-----|
| One-off chat in a web UI | Layer 2 clipboard helper |
| Repeated tasks via queue worker | Layer 1 programmatic injection |
| Long-lived coding agent session | Layer 3 anchor file in repo root |
| Chinese model, web UI or API | System prompt = bootstrap contents (closest to Layer 3) |
| Claude Desktop / MCP-aware client | MCP server exposes `mllang_spec` tool; model can call it on demand instead of pre-loading |
