#!/usr/bin/env python3
"""Claude Code status reporter.

Invoked by Claude Code hooks (see ~/.claude/settings.json). Reads the hook JSON
from stdin, takes a status word as argv[1], and writes one status file per session
to ~/.claude/status/<session_id>.json. The SwiftBar plugin (claude_status.2s.py)
reads those files and draws the menu-bar dots.

Must fail silently and fast: hooks block the session, so any error here must never
raise and must finish well under ~100ms.
"""
import sys
import os
import json
import time
import subprocess

STATUS_DIR = os.path.expanduser("~/.claude/status")


def find_gui_app(start_pid):
    """Walk up the process tree from start_pid to find the GUI .app the session
    runs under (NOT the Claude Code engine, which lives under
    .../claude-code/.../claude.app). Returns (pid, app_path) or (None, None).

    Desktop: each session is its own app instance, so the click handler focuses
    the exact window. Terminal/IDE: this resolves to Terminal.app / iTerm / VS
    Code etc., so the click brings that app to the front (exact tab not targeted).
    """
    pid = start_pid
    try:
        for _ in range(15):
            if not pid or pid in (0, 1):
                break
            out = subprocess.run(
                ["ps", "-o", "ppid=,command=", "-p", str(pid)],
                capture_output=True, text=True, timeout=2,
            ).stdout.strip()
            if not out:
                break
            parts = out.split(None, 1)
            ppid = int(parts[0])
            cmd = parts[1] if len(parts) > 1 else ""
            if (".app/Contents/MacOS/" in cmd
                    and "/claude-code/" not in cmd
                    and "/Contents/Helpers/" not in cmd
                    and "/Contents/Frameworks/" not in cmd):
                app_path = cmd[:cmd.index(".app/")] + ".app"
                return pid, app_path
            pid = ppid
    except Exception:
        pass
    return None, None


def first_user_text(transcript_path, cap=400):
    """Cheaply extract the session's first real user message to use as its name.
    Reads only up to the first matching line (early break) — never the whole file.
    """
    try:
        if not transcript_path or not os.path.exists(transcript_path):
            return ""
        with open(transcript_path, errors="ignore") as fh:
            for i, line in enumerate(fh):
                if i > cap:
                    break
                if '"user"' not in line:
                    continue
                try:
                    o = json.loads(line)
                except Exception:
                    continue
                if o.get("type") != "user":
                    continue
                c = (o.get("message", {}) or {}).get("content")
                if isinstance(c, list):
                    c = "".join(p.get("text", "") for p in c
                                if isinstance(p, dict) and p.get("type") == "text")
                if isinstance(c, str):
                    c = " ".join(c.split())
                    if c and not c.startswith("<") and not c.startswith("Caveat"):
                        return c[:50]
    except Exception:
        return ""
    return ""


def main():
    status = sys.argv[1] if len(sys.argv) > 1 else "running"

    raw = sys.stdin.read() if not sys.stdin.isatty() else ""
    data = json.loads(raw) if raw.strip() else {}

    sid = data.get("session_id") or "unknown"
    os.makedirs(STATUS_DIR, exist_ok=True)
    path = os.path.join(STATUS_DIR, sid + ".json")

    if status == "end":
        try:
            os.remove(path)
        except FileNotFoundError:
            pass
        return

    cwd = (data.get("cwd") or "").rstrip("/")
    now = int(time.time())

    existing = {}
    try:
        with open(path) as f:
            existing = json.load(f)
    except Exception:
        existing = {}

    # The GUI app PID is stable for a session — compute once and reuse.
    app_pid = existing.get("app_pid")
    app_path = existing.get("app_path")
    if not app_pid:
        app_pid, app_path = find_gui_app(os.getppid())

    transcript = data.get("transcript_path", "") or existing.get("transcript_path", "")

    # Session name = its first user message. Compute once, then reuse.
    name = existing.get("name") or ""
    if not name:
        p = data.get("prompt") or data.get("user_prompt") or ""
        if isinstance(p, str):
            p = " ".join(p.split())
            if p and not p.startswith("<"):
                name = p[:50]
    if not name:
        name = first_user_text(transcript)

    rec = {
        "session_id": sid,
        "name": name,
        "project": os.path.basename(cwd) or cwd or "session",
        "cwd": cwd,
        "transcript_path": transcript,
        "status": status,
        "app_pid": app_pid,
        "app_path": app_path,
        "started_at": existing.get("started_at", now),
        "updated_at": now,
    }

    tmp = path + ".tmp"
    with open(tmp, "w") as f:
        json.dump(rec, f)
    os.replace(tmp, path)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
