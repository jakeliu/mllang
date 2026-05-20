#!/usr/bin/env bash
# Wraps shim-engine-report against the MLLANG session log.
# Used by /mllang report and /mllang status.
set -e

LOG="${HOME}/.claude/mllang-shim/session.jsonl"

if ! command -v shim-engine-report >/dev/null 2>&1; then
    cat <<EOF
shim-engine is not installed. To enable MLLANG savings reports:

    pip install 'shim-engine[mllang]'

(Or 'mllang-protocol[shim]' — same thing, both packages pulled.)

After install, sub-agent calls in this Claude Code session will be
recorded automatically by the PostToolUse hook, and you can run
/mllang report any time.
EOF
    exit 0
fi

if [[ ! -f "$LOG" ]]; then
    cat <<EOF
No MLLANG calls recorded yet this session.

The PostToolUse hook starts logging the first time the Agent tool
spawns a sub-agent whose response contains an MLLANG packet.

Log path: $LOG
EOF
    exit 0
fi

exec shim-engine-report "$@" "$LOG"
