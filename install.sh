#!/usr/bin/env bash
# install.sh — set up the Claude Code menu-bar status monitor on this machine.
# Idempotent and safe to re-run. One command for a fresh install (new machine/user).
#
# It is self-sufficient: it links the scripts, MERGES the status hooks into your
# ~/.claude/settings.json (preserving anything already there, with a backup), and
# installs + launches SwiftBar. macOS only.
set -uo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # .../status-monitor
CLAUDE_DIR="$HOME/.claude"
LINK="$CLAUDE_DIR/status-monitor"

echo "==> 1. Link ~/.claude/status-monitor -> repo"
if [ -L "$LINK" ] || [ ! -e "$LINK" ]; then
  ln -sfn "$REPO_DIR" "$LINK"
  echo "    linked: $LINK -> $REPO_DIR"
elif [ -d "$LINK" ]; then
  echo "    ! a real directory exists at $LINK — leaving it untouched."
  echo "      (remove it and re-run to use the repo copy.)"
fi

echo "==> 2. Merge status hooks into ~/.claude/settings.json (idempotent, backed up)"
/usr/bin/python3 "$REPO_DIR/merge-hooks.py" "$CLAUDE_DIR/settings.json" \
  || echo "    ! could not merge hooks automatically — see README to add them by hand."

echo "==> 3. Runtime status dir + executables"
mkdir -p "$CLAUDE_DIR/status"
chmod +x "$REPO_DIR/reporter.py" "$REPO_DIR/claude_status.2s.py" "$REPO_DIR/open-session.sh" "$REPO_DIR/merge-hooks.py" 2>/dev/null || true

echo "==> 4. SwiftBar (menu-bar app)"
if [ -d "/Applications/SwiftBar.app" ] || [ -d "$HOME/Applications/SwiftBar.app" ]; then
  echo "    already installed."
elif command -v brew >/dev/null 2>&1; then
  brew install --cask swiftbar || echo "    ! brew install failed — install SwiftBar manually from https://swiftbar.app"
else
  echo "    ! Homebrew not found. Install SwiftBar from https://swiftbar.app, then re-run."
fi

echo "==> 5. Point SwiftBar at the plugin folder + launch at login"
# Use the REAL repo path (not the ~/.claude symlink): SwiftBar's folder watcher
# is unreliable when the plugin dir is reached through a symlinked parent.
defaults write com.ameba.SwiftBar PluginDirectory "$REPO_DIR/swiftbar-plugins" 2>/dev/null || true
defaults write com.ameba.SwiftBar SwiftBarLaunchAtLogin -bool true 2>/dev/null || true
open -a SwiftBar 2>/dev/null || true

echo
echo "Done. Open a Claude Code session and look at the menu bar (top-right)."
echo "If dots don't appear, quit and reopen SwiftBar."
