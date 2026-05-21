#!/usr/bin/env bash
# Install /mail Claude Code skill
set -e
SRC="$(cd "$(dirname "$0")" && pwd)"
DEST="${HOME}/.claude/skills/mail"
mkdir -p "$DEST"
cp "$SRC/SKILL.md" "$DEST/"
echo "Installed /mail skill to $DEST"
echo "Restart Claude Code to activate."
