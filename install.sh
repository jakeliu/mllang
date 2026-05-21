#!/usr/bin/env bash
# MLLANG one-shot installer.
#
# Usage:
#   curl -sL https://raw.githubusercontent.com/jakeliu/mllang/main/install.sh | bash
#   curl -sL https://raw.githubusercontent.com/jakeliu/mllang/main/install.sh | bash -s -- --my-box=claude-jake
#
# What it does:
#   1. Installs mllang-protocol[mcp] via pipx (brew install pipx if missing)
#   2. Detects Claude Code (~/.claude-jake/) and/or Codex (~/.codex/) installs
#   3. For each found client:
#      - copies slash-command file (Claude Code only — Codex CLI doesn't take them yet)
#      - copies hook scripts
#      - adds MCP server entry to the client's config
#      - wires UserPromptSubmit + PreToolUse + PostToolUse hooks
#      - drops AGENTS.md natural-language instructions
#   4. Suggests MLLANG_MY_BOX env var in shell rc (writes if --my-box passed)
#   5. Prints next steps + verification commands
#
# Re-runnable. Backs up any file it modifies to <file>.bak-<ts>.

set -euo pipefail

MY_BOX=""
DRY_RUN=0
REPO_RAW="https://raw.githubusercontent.com/jakeliu/mllang/main"
TS=$(date +%Y%m%d_%H%M%S)

for arg in "$@"; do
    case "$arg" in
        --my-box=*) MY_BOX="${arg#*=}" ;;
        --dry-run)  DRY_RUN=1 ;;
        --help)
            head -25 "$0" | sed -n '3,25p' | sed 's/^# //; s/^#//'
            exit 0
            ;;
    esac
done

# Logging helpers
log()  { printf '\033[1;34m[mllang]\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }
ok()   { printf '\033[1;32m[ok]\033[0m %s\n' "$*"; }
err()  { printf '\033[1;31m[err]\033[0m %s\n' "$*" >&2; }
do_or_say() {
    if [[ $DRY_RUN -eq 1 ]]; then printf '  would run: %s\n' "$*"; else eval "$@"; fi
}

backup() {
    [[ -f "$1" ]] && cp "$1" "$1.bak-$TS" && log "backed up $1 → $1.bak-$TS"
}

# ── 1. Install mllang-protocol ──────────────────────────────────────────

if ! command -v pipx >/dev/null; then
    log "pipx not found"
    if command -v brew >/dev/null; then
        do_or_say "brew install pipx"
        do_or_say "pipx ensurepath"
    else
        err "Neither pipx nor brew found. Install Python 3.10+ and pipx manually, then re-run."
        exit 1
    fi
fi

if pipx list 2>/dev/null | grep -q "mllang-protocol"; then
    log "mllang-protocol already installed — upgrading"
    do_or_say "pipx upgrade mllang-protocol >/dev/null"
else
    log "installing mllang-protocol[mcp]"
    do_or_say "pipx install 'mllang-protocol[mcp]'"
fi

MLLANG_BIN=$(command -v mllang-mailbox 2>/dev/null || echo "$HOME/.local/bin/mllang-mailbox")
MCP_BIN=$(command -v mllang-mcp-server 2>/dev/null || echo "$HOME/.local/bin/mllang-mcp-server")

if [[ ! -x "$MLLANG_BIN" ]]; then
    err "mllang-mailbox not on PATH after install. Add $HOME/.local/bin to PATH and re-run."
    exit 1
fi
ok "mllang-mailbox at $MLLANG_BIN"
ok "mllang-mcp-server at $MCP_BIN"

# ── 2. Detect clients ───────────────────────────────────────────────────

HAS_CLAUDE_CODE=0
HAS_CODEX=0
CLAUDE_DIR=""

# Claude Code stores config in ~/.claude-<username>/ (alternate) or ~/.claude/
for d in "$HOME/.claude-$(whoami)" "$HOME/.claude-jake" "$HOME/.claude"; do
    if [[ -d "$d" && -d "$d/commands" ]]; then
        CLAUDE_DIR="$d"
        HAS_CLAUDE_CODE=1
        break
    fi
done

[[ -d "$HOME/.codex" ]] && HAS_CODEX=1

[[ $HAS_CLAUDE_CODE -eq 1 ]] && log "found Claude Code at $CLAUDE_DIR"
[[ $HAS_CODEX -eq 1 ]] && log "found Codex CLI at $HOME/.codex"

if [[ $HAS_CLAUDE_CODE -eq 0 && $HAS_CODEX -eq 0 ]]; then
    warn "Neither Claude Code nor Codex CLI detected. mllang-mailbox CLI still installed; skip client wiring."
    exit 0
fi

# ── 3. Make mllang-shim scratch dirs ────────────────────────────────────

mkdir -p "$HOME/.mllang-mailbox"

# ── 4. Claude Code wiring ───────────────────────────────────────────────

if [[ $HAS_CLAUDE_CODE -eq 1 ]]; then
    log "wiring Claude Code at $CLAUDE_DIR"

    # 4a. Slash command file
    mkdir -p "$CLAUDE_DIR/commands"
    do_or_say "curl -sL $REPO_RAW/claude-code-skill/commands/mllang.md > $CLAUDE_DIR/commands/mllang.md"

    # 4b. Skill dir for hook scripts + bootstrap
    mkdir -p "$CLAUDE_DIR/skills/mllang/scripts" "$CLAUDE_DIR/skills/mllang/roles"
    for f in SKILL.md bootstrap.md spec-summary.md install.sh; do
        do_or_say "curl -sL $REPO_RAW/claude-code-skill/$f > $CLAUDE_DIR/skills/mllang/$f 2>/dev/null || true"
    done
    for f in hook_preprompt.py hook_postagent.py report.sh; do
        do_or_say "curl -sL $REPO_RAW/claude-code-skill/scripts/$f > $CLAUDE_DIR/skills/mllang/scripts/$f"
        do_or_say "chmod +x $CLAUDE_DIR/skills/mllang/scripts/$f"
    done
    for role in orchestrator critic implementer synthesizer; do
        do_or_say "curl -sL $REPO_RAW/claude-code-skill/roles/$role.md > $CLAUDE_DIR/skills/mllang/roles/$role.md"
    done

    # 4c. Settings.json hooks
    SETTINGS="$CLAUDE_DIR/settings.json"
    if [[ -f "$SETTINGS" ]] && command -v python3 >/dev/null; then
        backup "$SETTINGS"
        python3 - <<PYEOF
import json, sys
p = "$SETTINGS"
try:
    cfg = json.load(open(p))
except Exception:
    cfg = {}
cfg.setdefault("hooks", {})
hk = cfg["hooks"]
script = "$CLAUDE_DIR/skills/mllang/scripts/hook_preprompt.py"
postagent = "$CLAUDE_DIR/skills/mllang/scripts/hook_postagent.py"
def add(event, cmd, matcher=None):
    entries = hk.setdefault(event, [])
    sig = (matcher, cmd)
    for e in entries:
        for h in e.get("hooks", []):
            if h.get("command") == cmd and e.get("matcher") == matcher:
                return
    block = {"hooks": [{"type": "command", "command": cmd}]}
    if matcher:
        block["matcher"] = matcher
    entries.append(block)
add("UserPromptSubmit", f"python3 {script}")
add("PreToolUse", f"python3 {script}")
add("PostToolUse", f"python3 {postagent}", matcher="Agent")
open(p, "w").write(json.dumps(cfg, indent=2))
print("settings.json updated")
PYEOF
    fi

    ok "Claude Code wired"
fi

# ── 5. Codex CLI wiring ─────────────────────────────────────────────────

if [[ $HAS_CODEX -eq 1 ]]; then
    log "wiring Codex CLI at $HOME/.codex"

    # 5a. MCP server entry in config.toml
    CODEX_CFG="$HOME/.codex/config.toml"
    if [[ -f "$CODEX_CFG" ]] && ! grep -q "mcp_servers.mllang" "$CODEX_CFG"; then
        backup "$CODEX_CFG"
        do_or_say "printf '\n[mcp_servers.mllang]\ncommand = \"%s\"\n' \"$MCP_BIN\" >> $CODEX_CFG"
    fi

    # 5b. AGENTS.md natural-language instructions
    AGENTS_MD="$HOME/.codex/AGENTS.md"
    if ! grep -q "MLLANG mailbox shortcuts" "$AGENTS_MD" 2>/dev/null; then
        do_or_say "curl -sL $REPO_RAW/codex-cli-integration/AGENTS_mllang_snippet.md >> $AGENTS_MD 2>/dev/null || true"
    fi

    # 5c. Hook scripts
    mkdir -p "$HOME/.codex/mllang-integration/scripts"
    do_or_say "curl -sL $REPO_RAW/codex-cli-integration/scripts/hook_preprompt_codex_wrapper.py > $HOME/.codex/mllang-integration/scripts/hook_preprompt_codex_wrapper.py"
    do_or_say "curl -sL $REPO_RAW/claude-code-skill/scripts/hook_preprompt.py > $HOME/.codex/mllang-integration/scripts/hook_preprompt.py"
    do_or_say "chmod +x $HOME/.codex/mllang-integration/scripts/*.py"

    # 5d. [[hooks.UserPromptSubmit]] in config.toml so auto-surface fires
    if [[ -f "$CODEX_CFG" ]] && ! grep -q "hook_preprompt_codex_wrapper.py" "$CODEX_CFG"; then
        BOX_NAME="${MY_BOX:-codex}"
        do_or_say "printf '\n[[hooks.UserPromptSubmit]]\nmatcher = \"\"\n\n[[hooks.UserPromptSubmit.hooks]]\ntype = \"command\"\ncommand = \"MLLANG_MY_BOX=%s python3 %s/.codex/mllang-integration/scripts/hook_preprompt_codex_wrapper.py\"\n' \"$BOX_NAME\" \"$HOME\" >> $CODEX_CFG"
    fi

    ok "Codex CLI wired (main profile). For other profiles, repeat manually with config.toml."
fi

# ── 6. MLLANG_MY_BOX env ────────────────────────────────────────────────

SHELL_RC=""
case "$SHELL" in
    */zsh) SHELL_RC="$HOME/.zshrc" ;;
    */bash) SHELL_RC="$HOME/.bashrc" ;;
esac

if [[ -n "$MY_BOX" && -n "$SHELL_RC" ]]; then
    if ! grep -q "MLLANG_MY_BOX" "$SHELL_RC" 2>/dev/null; then
        do_or_say "echo 'export MLLANG_MY_BOX=$MY_BOX' >> $SHELL_RC"
        ok "MLLANG_MY_BOX=$MY_BOX added to $SHELL_RC"
    else
        warn "MLLANG_MY_BOX already in $SHELL_RC; left alone"
    fi
fi

# ── 7. Done ─────────────────────────────────────────────────────────────

cat <<EOF

──────────────────────────────────────────────────────────────────────
mllang installed.

Next steps:
  1. (one-time) Set your box name if not passed via --my-box:
       echo 'export MLLANG_MY_BOX=<your-name>' >> ${SHELL_RC:-~/.zshrc}
       source ${SHELL_RC:-~/.zshrc}

  2. Restart Claude Code and/or Codex CLI for hooks to load.

  3. From any shell:
       mllang-mailbox send <box> "hi"
       mllang-mailbox check

  4. Inside Claude Code:
       /mllang send <box> hi
       /mllang receive

  5. Inside Codex (natural language — slash command not yet supported by Codex CLI 0.130):
       "send hi to <box>"
       "check my mailbox"

PyPI:   https://pypi.org/project/mllang-protocol/
Source: https://github.com/jakeliu/mllang
──────────────────────────────────────────────────────────────────────
EOF
