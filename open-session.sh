#!/bin/bash
# Click handler for the SwiftBar menu. Given a session_id (passed as $1), focuses
# the desktop app window/instance running that Claude Code session.
#
# Primary method: `open <app-path>` — LaunchServices brings the exact app bundle
# to the front. Proven to work on this Mac with no special permissions, and it
# correctly distinguishes separate app instances (e.g. Claude-RTL vs Claude-RTL-2).
# Fallbacks below cover edge cases (missing path, or two windows of one bundle).

LOG="$HOME/.claude/status-monitor/click.log"
sid="$1"
echo "$(date '+%H:%M:%S') click sid='$sid' args='$*'" >>"$LOG"

f="$HOME/.claude/status/$sid.json"
if [ ! -f "$f" ]; then
  echo "  -> no status file for sid" >>"$LOG"
  open -a "Claude" 2>/dev/null || true
  exit 0
fi

field() { /usr/bin/python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get(sys.argv[2]) or '')" "$f" "$1" 2>/dev/null; }
app_pid="$(field app_pid)"
app_path="$(field app_path)"
echo "  -> app_pid='$app_pid' app_path='$app_path'" >>"$LOG"

# 1) Open the specific bundle by path (works without permissions).
if [ -n "$app_path" ] && [ -e "$app_path" ]; then
  open "$app_path" 2>>"$LOG" && { echo "  -> opened by path" >>"$LOG"; exit 0; }
fi

# 2) Focus the exact instance by PID via System Events (needs Accessibility).
if [ -n "$app_pid" ]; then
  if osascript -e "tell application \"System Events\" to set frontmost of (first process whose unix id is $app_pid) to true" 2>>"$LOG"; then
    echo "  -> focused by pid" >>"$LOG"; exit 0
  fi
fi

# 3) Last resort: bring any Claude desktop app to the front.
echo "  -> fallback open -a Claude" >>"$LOG"
open -a "Claude" 2>/dev/null || true
