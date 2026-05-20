#!/usr/bin/env bash
# Run `codex exec --json` and record completed turns into shim-engine.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

if [[ $# -eq 0 ]]; then
    cat <<'EOF'
Usage:
  codex_exec_wrapper.sh '<prompt>'
  echo '<prompt>' | codex_exec_wrapper.sh -

Environment:
  CODEX_MODEL   Model to pass to codex exec (default: gpt-5.5)
  MLLANG_CODEX_LOG  shim-engine log path (default: ~/.codex/mllang-shim/session.jsonl)
EOF
    exit 2
fi

MODEL="${CODEX_MODEL:-gpt-5.5}"

if [[ "$1" == "-" ]]; then
    PROMPT="$(cat)"
else
    PROMPT="$*"
fi

codex exec --skip-git-repo-check --json -m "$MODEL" - <<< "$PROMPT" \
    | tee >(python3 "${SCRIPT_DIR}/codex_session_parser.py" --stdin-events >/dev/null)
