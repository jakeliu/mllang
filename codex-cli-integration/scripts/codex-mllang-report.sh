#!/usr/bin/env bash
# Wrap shim-engine-report against the Codex MLLANG session log.
set -euo pipefail

LOG="${MLLANG_CODEX_LOG:-${HOME}/.codex/mllang-shim/session.jsonl}"

if ! command -v shim-engine-report >/dev/null 2>&1; then
    cat <<'EOF'
shim-engine is not installed. To enable Codex MLLANG reports:

    pip install 'shim-engine[mllang]'

Then parse a Codex session:

    python3 ~/.codex/mllang-integration/scripts/codex_session_parser.py --latest
EOF
    exit 0
fi

if [[ ! -f "$LOG" ]]; then
    cat <<EOF
No Codex MLLANG records found yet.

Parse the latest Codex session first:

    python3 ~/.codex/mllang-integration/scripts/codex_session_parser.py --latest

Log path: $LOG
EOF
    exit 0
fi

exec shim-engine-report "$@" "$LOG"
