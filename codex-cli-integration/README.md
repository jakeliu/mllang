# Codex CLI Integration

Conservative Path 1 for Codex CLI: parse Codex session JSONL, capture real per-turn token usage, and write local `shim-engine` records.

The base installer does **not** install hooks. Codex's stable telemetry surface is still:

```text
~/.codex/sessions/YYYY/MM/DD/rollout-*.jsonl
```

Records are written to:

```text
~/.codex/mllang-shim/session.jsonl
```

## Install

From a local clone:

```bash
bash codex-cli-integration/install.sh
pip install 'shim-engine[mllang]'
```

From GitHub:

```bash
curl -sL https://raw.githubusercontent.com/jakeliu/mllang/main/codex-cli-integration/install.sh | bash
pip install 'shim-engine[mllang]'
```

The installer copies files to:

```text
~/.codex/mllang-integration/
```

It also creates the log directory:

```text
~/.codex/mllang-shim/
```

It does not edit `~/.codex/config.toml` and does not install hooks. Optional mailbox auto-surface wiring is documented below.

## Example 1: Parse The Latest Codex Session

Run any Codex task, then parse the latest rollout:

```bash
python3 ~/.codex/mllang-integration/scripts/codex_session_parser.py --latest
bash ~/.codex/mllang-integration/scripts/codex-mllang-report.sh
```

Budget source priority:

```text
B-slot -> session-token_count -> none
```

If the final message contains:

```text
B:{tokens_in=850, tokens_out=240, time=3.4s}
```

the parser uses that cooperative budget and tags the row with:

```text
budget_source=B-slot
```

If no `B:` slot is present, it uses Codex's `token_count` event and tags:

```text
budget_source=session-token_count
```

## Example 2: Watch New Completed Turns

Leave this running in another terminal:

```bash
python3 ~/.codex/mllang-integration/scripts/codex_session_parser.py --watch
```

The watcher polls the newest rollout file under `~/.codex/sessions/` and records each new `task_complete` once. It uses only Python stdlib polling, no inotify dependency.

## Example 3: Wrap `codex exec --json`

Run a one-shot task and record the completed turn from streamed JSON events:

```bash
~/.codex/mllang-integration/scripts/codex_exec_wrapper.sh \
  'Emit one MLLANG packet with B:{tokens_in=850, tokens_out=240, time=3.4s}.'
```

The wrapper is optional. The `--latest` and `--watch` modes cover the same data after Codex writes its session file.

## Optional: Mailbox Auto-Surface Hook

Codex can run a `UserPromptSubmit` hook that polls `~/.mllang-mailbox/codex/inbox/` before each prompt and injects unread-message context into the next model turn.

This uses the same mailbox polling script as the Claude Code skill, kept verbatim as `hook_preprompt.py`. Codex needs a tiny adapter because Claude Code's `systemMessage` hook output is only a warning in Codex; Codex model-visible context uses `hookSpecificOutput.additionalContext`.

Copy scripts into the active Codex home:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/mllang-integration/scripts"
cp claude-code-skill/scripts/hook_preprompt.py \
  "${CODEX_HOME:-$HOME/.codex}/mllang-integration/scripts/hook_preprompt.py"
cp codex-cli-integration/scripts/hook_preprompt_codex_wrapper.py \
  "${CODEX_HOME:-$HOME/.codex}/mllang-integration/scripts/hook_preprompt_codex_wrapper.py"
chmod +x "${CODEX_HOME:-$HOME/.codex}/mllang-integration/scripts/"hook_preprompt*.py
```

Add this to the active Codex `config.toml`:

```toml
[[hooks.UserPromptSubmit]]
matcher = ""

[[hooks.UserPromptSubmit.hooks]]
type = "command"
command = "MLLANG_MY_BOX=codex python3 /full/path/to/hook_preprompt_codex_wrapper.py"
```

Restart Codex and open `/hooks`; trust the new `UserPromptSubmit` hook. Codex writes the trusted hash under `[hooks.state]`.

Smoke test:

```bash
mllang-mailbox send codex "test the hook surfaces this" --from test --subject "auto-surface test"
```

On the next Codex prompt, the model should see a context entry like:

```text
[mllang-mailbox] 1 unread in box=codex
```

The captured Codex hook stdin schema is committed at:

```text
codex-cli-integration/fixtures/hook_stdin_sample.json
```

## What Gets Logged

`shim-engine` stores packet shape and metrics, not packet values. Each Codex row includes tags:

```text
source=codex-cli
budget_source=B-slot | session-token_count | none
capture_boundary=turn
codex_cli_version=<version>
codex_session_id=<session id>
turn_id=<turn id>
originator=<codex originator>
cwd=<cwd from session_meta>
```

The capture boundary is `turn`, not sub-agent. Sub-agent-only cost slicing is deferred until a real `CollabAgentSpawnEnd` or hook payload fixture exists.

## Local Test

```bash
python3 codex-cli-integration/tests/test_session_parser.py
```

The fixture is a redacted real Codex rollout. User prompts and local paths are replaced with placeholders before committing.

Hook fixture note: `hook_stdin_sample.json` is also redacted. It preserves Codex's real `UserPromptSubmit` fields while replacing concrete local paths, session ids, turn ids, and user prompt text.
