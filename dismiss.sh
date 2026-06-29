#!/bin/bash
# Manually remove sessions from the status list (used by the SwiftBar menu).
#   dismiss.sh <session_id>   remove one session now
#   dismiss.sh --done         remove all finished (green) sessions
#   dismiss.sh --all          remove every session
#
# This deletes the status file immediately, so a session disappears without
# waiting for the auto-hide timer. A still-active session will simply reappear
# on its next hook event — which is correct (it's not actually gone).
d="$HOME/.claude/status"

case "$1" in
  --all)
    rm -f "$d"/*.json
    ;;
  --done)
    for f in "$d"/*.json; do
      [ -e "$f" ] || continue
      /usr/bin/python3 -c "import json,sys;sys.exit(0 if (json.load(open(sys.argv[1])).get('status')=='done') else 1)" "$f" 2>/dev/null && rm -f "$f"
    done
    ;;
  *)
    [ -n "$1" ] && rm -f "$d/$1.json"
    ;;
esac
exit 0
