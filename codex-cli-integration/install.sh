#!/usr/bin/env bash
# Install the conservative MLLANG integration for Codex CLI.
#
# Run from a local clone:
#   bash codex-cli-integration/install.sh
#
# Or from GitHub:
#   curl -sL https://raw.githubusercontent.com/jakeliu/mllang/main/codex-cli-integration/install.sh | bash
set -euo pipefail

INSTALL_DIR="${HOME}/.codex/mllang-integration"
LOG_DIR="${HOME}/.codex/mllang-shim"
SRC_REPO="https://github.com/jakeliu/mllang.git"
ADD_ALIASES=false

for arg in "$@"; do
    case "$arg" in
        --add-aliases) ADD_ALIASES=true ;;
        *)
            echo "Unknown option: $arg" >&2
            exit 2
            ;;
    esac
done

mkdir -p "${HOME}/.codex" "$LOG_DIR"

if [[ -f "$(dirname "$0")/scripts/codex_session_parser.py" ]]; then
    SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
    echo "Installing from local clone at $SRC_DIR"
else
    TMP="$(mktemp -d)"
    trap 'rm -rf "$TMP"' EXIT
    echo "Cloning $SRC_REPO into temp..."
    git clone --depth 1 --quiet "$SRC_REPO" "$TMP/mllang"
    SRC_DIR="$TMP/mllang/codex-cli-integration"
fi

if [[ -d "$INSTALL_DIR" ]]; then
    BACKUP="${INSTALL_DIR}.bak.$(date +%Y%m%d_%H%M%S)"
    echo "Existing install found at $INSTALL_DIR; backing up to $BACKUP"
    mv "$INSTALL_DIR" "$BACKUP"
fi

mkdir -p "$INSTALL_DIR"
cp -R "$SRC_DIR/." "$INSTALL_DIR/"
chmod +x "$INSTALL_DIR/scripts/"*.sh "$INSTALL_DIR/scripts/"*.py 2>/dev/null || true

if [[ "$ADD_ALIASES" == true ]]; then
    SHELL_RC="${HOME}/.zshrc"
    if [[ -n "${BASH_VERSION:-}" ]]; then
        SHELL_RC="${HOME}/.bashrc"
    fi
    {
        echo ""
        echo "# MLLANG Codex CLI integration"
        echo "alias codex-mllang-report='${INSTALL_DIR}/scripts/codex-mllang-report.sh'"
        echo "alias codex-mllang-parse='python3 ${INSTALL_DIR}/scripts/codex_session_parser.py'"
    } >> "$SHELL_RC"
    echo "Aliases appended to $SHELL_RC"
fi

cat <<EOF

Installed to $INSTALL_DIR

Next steps:
  1. (optional) pip install 'shim-engine[mllang]'   # enables reports
  2. Run a Codex task. The session is captured under ~/.codex/sessions/.
  3. Parse the latest session:
       python3 ~/.codex/mllang-integration/scripts/codex_session_parser.py --latest
  4. Read the report:
       bash ~/.codex/mllang-integration/scripts/codex-mllang-report.sh

No hooks were installed. This integration uses conservative session-JSONL parsing.
EOF
