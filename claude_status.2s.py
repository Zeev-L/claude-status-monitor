#!/usr/bin/env python3
# <xbar.title>Claude Code Status</xbar.title>
# <xbar.version>1.0</xbar.version>
# <xbar.author>Zeev</xbar.author>
# <xbar.desc>Shows a colored dot per running Claude Code session: red=working, orange=waiting for you, green=done.</xbar.desc>
# <xbar.dependencies>python3</xbar.dependencies>
#
# SwiftBar refresh interval is encoded in the filename (claude_status.2s.py = 2s).
"""Reads ~/.claude/status/*.json (written by reporter.py) and renders the menu bar."""
import os
import json
import time
import glob

STATUS_DIR = os.path.expanduser("~/.claude/status")
OPENER = os.path.expanduser("~/.claude/status-monitor/open-session.sh")
DISMISS = os.path.expanduser("~/.claude/status-monitor/dismiss.sh")
# Desktop app stores each session's sidebar title here, keyed by cliSessionId.
SESSIONS_DIR = os.path.expanduser(
    "~/Library/Application Support/Claude/claude-code-sessions")


def resolve_titles(session_ids):
    """Map our hook session_ids -> the desktop sidebar title, by matching
    `cliSessionId` in the app's local_*.json files. Scans newest-first and stops
    once every live session is found, so it reads only a handful of files."""
    want = set(session_ids)
    found = {}
    try:
        files = glob.glob(os.path.join(SESSIONS_DIR, "**", "local_*.json"),
                          recursive=True)
        files.sort(key=lambda f: os.path.getmtime(f), reverse=True)
        for f in files:
            if not want:
                break
            try:
                o = json.load(open(f))
            except Exception:
                continue
            cli = o.get("cliSessionId")
            if cli in want:
                t = (o.get("title") or "").strip()
                if t:
                    found[cli] = t
                want.discard(cli)
    except Exception:
        pass
    return found

# status -> (emoji, label, sort priority [lower = more urgent])
STYLE = {
    "waiting": ("🟠", "waiting", 0),
    "error":   ("🟠", "error",   0),
    "running": ("🔴", "running", 1),
    "idle":    ("⚪", "idle",    2),
    "done":    ("🟢", "done",    3),
}

STALE_RUNNING_SECS = 600        # mark a "running" session stale after 10 min idle
PRUNE_SECS = 6 * 3600           # delete orphan files older than 6 h
DONE_KEEP_SECS = 300            # auto-remove a finished (green) session 5 min after it finished


def human_age(secs):
    if secs < 90:
        return "just now"
    if secs < 3600:
        return f"{secs // 60}m"
    if secs < 86400:
        return f"{secs // 3600}h"
    return f"{secs // 86400}d"


def load_sessions():
    now = int(time.time())
    sessions = []
    for path in glob.glob(os.path.join(STATUS_DIR, "*.json")):
        try:
            with open(path) as f:
                rec = json.load(f)
        except Exception:
            continue
        age = now - int(rec.get("updated_at", now))
        # prune orphaned/abandoned sessions
        if age > PRUNE_SECS:
            try:
                os.remove(path)
            except Exception:
                pass
            continue
        rec["_age"] = age
        sessions.append(rec)
    return sessions


def filter_visible(sessions):
    """Always show active (non-done) sessions. A finished (green) session is
    auto-removed from the list once it's been done for DONE_KEEP_SECS (5 min).
    Display-only: the file stays on disk, so if that session gets a new prompt it
    flips back to running and reappears."""
    return [s for s in sessions
            if not (s.get("status") == "done" and s.get("_age", 0) >= DONE_KEEP_SECS)]


def main():
    sessions = filter_visible(load_sessions())

    # ---- menu bar title: compact counts per color ----
    counts = {"🟠": 0, "🔴": 0, "🟢": 0, "⚪": 0}
    for s in sessions:
        emoji = STYLE.get(s.get("status", "idle"), STYLE["idle"])[0]
        counts[emoji] = counts.get(emoji, 0) + 1

    if not sessions:
        print("○ claude")
    else:
        title = " ".join(f"{e}{counts[e]}" for e in ("🟠", "🔴", "🟢", "⚪") if counts[e])
        print(title or "○ claude")

    print("---")
    if not sessions:
        print("No active Claude Code sessions | color=#888888")
    else:
        # sort by urgency, then most-recently-updated
        sessions.sort(key=lambda s: (STYLE.get(s.get("status", "idle"), STYLE["idle"])[2], s["_age"]))
        # label = desktop sidebar title; fall back to first message, then project
        titles = resolve_titles(s.get("session_id", "") for s in sessions)

        def label_of(s):
            return (titles.get(s.get("session_id", ""))
                    or (s.get("name") or "").strip()
                    or s.get("project", "session"))

        labels = [label_of(s) for s in sessions]
        for s in sessions:
            status = s.get("status", "idle")
            emoji, statlabel, _ = STYLE.get(status, STYLE["idle"])
            title = label_of(s)
            extra = ""
            if labels.count(title) > 1:
                extra = f" #{s.get('session_id', '')[:6]}"
            note = ""
            if status == "running" and s["_age"] > STALE_RUNNING_SECS:
                note = " · stale?"
            line = f"{emoji} {title}{extra} — {statlabel} · {human_age(s['_age'])}{note}"
            sid = s.get("session_id", "")
            # clicking focuses the session's desktop window
            print(f"{line} | bash=\"{OPENER}\" param1=\"{sid}\" terminal=false refresh=true")
            # submenu (hover): project path + a manual "remove now" action
            sub = s.get("project", "") or s.get("cwd", "")
            if sub:
                print(f"-- {sub} | color=#888888 font=Menlo size=11")
            print(f"-- ✕ Remove from list | bash=\"{DISMISS}\" param1=\"{sid}\" terminal=false refresh=true")

    print("---")
    done_n = sum(1 for s in sessions if s.get("status") == "done")
    if done_n:
        print(f"Clear finished ({done_n}) | bash=\"{DISMISS}\" param1=\"--done\" terminal=false refresh=true")
    print("Refresh | refresh=true")


if __name__ == "__main__":
    main()
