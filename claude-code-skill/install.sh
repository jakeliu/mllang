#!/usr/bin/env bash
# Install the MLLANG Claude Code skill.
#
# Run from anywhere:
#   curl -sL https://raw.githubusercontent.com/jakeliu/mllang/main/claude-code-skill/install.sh | bash
#
# Or, from a local clone of github.com/jakeliu/mllang:
#   bash claude-code-skill/install.sh
set -euo pipefail

SKILL_DIR="${HOME}/.claude/skills/mllang"
SRC_REPO="https://github.com/jakeliu/mllang.git"

mkdir -p "${HOME}/.claude/skills"

# Detect source: local clone vs remote curl-pipe install.
if [[ -f "$(dirname "$0")/SKILL.md" ]]; then
    SRC_DIR="$(cd "$(dirname "$0")" && pwd)"
    echo "Installing from local clone at $SRC_DIR"
else
    TMP=$(mktemp -d)
    trap 'rm -rf "$TMP"' EXIT
    echo "Cloning $SRC_REPO into temp..."
    git clone --depth 1 --quiet "$SRC_REPO" "$TMP/mllang"
    SRC_DIR="$TMP/mllang/claude-code-skill"
fi

if [[ -d "$SKILL_DIR" ]]; then
    BACKUP="${SKILL_DIR}.bak.$(date +%Y%m%d_%H%M%S)"
    echo "Existing install found at $SKILL_DIR — backing up to $BACKUP"
    mv "$SKILL_DIR" "$BACKUP"
fi

mkdir -p "$SKILL_DIR"
cp "$SRC_DIR/SKILL.md" "$SKILL_DIR/"
cp "$SRC_DIR/bootstrap.md" "$SKILL_DIR/"
cp "$SRC_DIR/spec-summary.md" "$SKILL_DIR/"
cp -r "$SRC_DIR/roles" "$SKILL_DIR/"
cp -r "$SRC_DIR/scripts" "$SKILL_DIR/"
chmod +x "$SKILL_DIR/scripts/"*.sh "$SKILL_DIR/scripts/"*.py 2>/dev/null || true

mkdir -p "${HOME}/.claude/mllang-shim"

echo
echo "Installed to $SKILL_DIR"
echo
echo "Next steps:"
echo "  1. (optional) pip install 'shim-engine[mllang]'   # enables /mllang report"
echo "  2. In Claude Code, type:  /mllang"
echo
echo "Skill files:"
ls -1 "$SKILL_DIR"
