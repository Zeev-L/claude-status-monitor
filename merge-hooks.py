#!/usr/bin/env python3
"""Merge the status-monitor hooks into a Claude Code settings.json (idempotent).

Adds the 8 hook events the status monitor needs, preserving any hooks/config the
user already has. Safe to re-run: existing status hooks are detected and skipped.
Backs up the file before writing. Usage: merge-hooks.py [path-to-settings.json]
(defaults to ~/.claude/settings.json).
"""
import sys
import os
import json
import time
import collections

PY3 = "/usr/bin/python3"
CMD = '%s "$HOME/.claude/status-monitor/reporter.py" %s'  # $HOME stays literal

# event -> (status, matcher or None)
WANT = [
    ("SessionStart",     "idle",    "*"),
    ("UserPromptSubmit", "running", None),
    ("PostToolUse",      "running", "*"),
    ("PermissionRequest","waiting", "*"),
    ("Notification",     "waiting", "*"),
    ("Stop",             "done",    None),
    ("StopFailure",      "error",   None),
    ("SessionEnd",       "end",     None),
]

MARK = "status-monitor/reporter.py"


def has_status_hook(hooks, event, status):
    for ent in hooks.get(event, []):
        for h in ent.get("hooks", []):
            c = h.get("command", "")
            if MARK in c and c.rstrip().endswith(" " + status):
                return True
    return False


def make_entry(status, matcher):
    h = collections.OrderedDict()
    h["type"] = "command"
    h["command"] = CMD % (PY3, status)
    h["async"] = True
    e = collections.OrderedDict()
    if matcher is not None:
        e["matcher"] = matcher
    e["hooks"] = [h]
    return e


def main():
    path = os.path.expanduser(sys.argv[1] if len(sys.argv) > 1
                              else "~/.claude/settings.json")

    cfg = collections.OrderedDict()
    if os.path.exists(path):
        try:
            with open(path) as f:
                cfg = json.load(f, object_pairs_hook=collections.OrderedDict)
        except Exception as e:
            print(f"! {path} is not valid JSON ({e}).")
            print("  Refusing to touch it. Add the hooks manually (see README).")
            return 2

    hooks = cfg.setdefault("hooks", collections.OrderedDict())

    added = 0
    for event, status, matcher in WANT:
        if has_status_hook(hooks, event, status):
            continue
        hooks.setdefault(event, []).append(make_entry(status, matcher))
        added += 1

    if added == 0:
        print("Status hooks already present — nothing to do.")
        return 0

    if os.path.exists(path):
        bak = path + ".bak." + time.strftime("%Y%m%d-%H%M%S")
        try:
            with open(path) as f, open(bak, "w") as b:
                b.write(f.read())
            print(f"Backed up existing settings to {bak}")
        except Exception:
            pass

    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)
        f.write("\n")
    print(f"Added {added} status hook(s) to {path}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
