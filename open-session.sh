#!/bin/bash
# Click handler for the SwiftBar menu. Given a session_id, focuses that session's
# window in the Claude desktop app.
#
# Modern desktop model: several sessions run as separate WINDOWS of ONE app
# process, so focusing the right one means raising the window whose title equals
# the session title. That requires System Events (Accessibility permission for
# SwiftBar). Without the permission we fall back to bringing the app to the front.

LOG="$HOME/.claude/status-monitor/click.log"
sid="$1"
echo "$(date '+%H:%M:%S') click sid='$sid'" >>"$LOG"
f="$HOME/.claude/status/$sid.json"

# The window title equals the session's sidebar title — look it up by cliSessionId.
title="$(/usr/bin/python3 - "$sid" <<'PY' 2>/dev/null
import json, os, glob, sys
sid = sys.argv[1]
base = os.path.expanduser("~/Library/Application Support/Claude/claude-code-sessions")
for fp in glob.glob(os.path.join(base, "**", "local_*.json"), recursive=True):
    try:
        o = json.load(open(fp))
    except Exception:
        continue
    if o.get("cliSessionId") == sid:
        t = (o.get("title") or "").strip()
        if t:
            print(t)
        break
PY
)"
echo "  title='$title'" >>"$LOG"

# Layer 1: raise the exact window by title (needs Accessibility permission).
if [ -n "$title" ]; then
  res="$(osascript - "$title" 2>>"$LOG" <<'APPLESCRIPT'
on run argv
  set theTitle to item 1 of argv
  tell application "System Events"
    repeat with p in (every process whose name contains "Claude")
      repeat with w in (windows of p)
        if name of w contains theTitle then
          set frontmost of p to true
          perform action "AXRaise" of w
          return "ok"
        end if
      end repeat
    end repeat
  end tell
  return "none"
end run
APPLESCRIPT
)"
  echo "  applescript=$res" >>"$LOG"
  [ "$res" = "ok" ] && exit 0
fi

# Layer 2: bring the app to the front (best effort — no per-window focus).
app_path=""
[ -f "$f" ] && app_path="$(/usr/bin/python3 -c "import json,sys;print(json.load(open(sys.argv[1])).get('app_path') or '')" "$f" 2>/dev/null)"
if [ -n "$app_path" ] && [ -e "$app_path" ]; then
  echo "  fallback: open $app_path" >>"$LOG"
  open "$app_path" 2>>"$LOG" && exit 0
fi
open -a "Claude" 2>/dev/null || true
