#!/usr/bin/env python3
"""Emit every hotkey as Alfred script-filter JSON; Alfred does the fuzzy filtering.

Sources: ~/.cache/hotkeys/entries.json (the Hotkeys app's live list; refreshed by the app on every scan,
or here via scripts/export.js when it is older than a day), plus the rule tables in ~/.config/HOTKEYS.md.
"""
import json, os, re, shutil, subprocess, time
from pathlib import Path

H = Path.home()
CACHE = H / ".cache/hotkeys/entries.json"
EXPORT = H / "local/code/web/hotkeys/scripts/export.js"
items = []

def add(key, action, src):
    key, action = key.strip(), action.strip()
    if len(key) > 2 and key[0] == key[-1] == "`":   # markdown code span, not a backtick key
        key = key[1:-1]
    key = key.replace("⌃⌥⇧⌘", "Hyper+")
    if key and action:
        items.append({"title": f"{key}   →   {action}", "subtitle": src,
                      "arg": key, "match": f"{key} {action} {src}"})

if (not CACHE.exists() or time.time() - CACHE.stat().st_mtime > 86400) and EXPORT.exists():
    node = shutil.which("node", path=os.environ.get("PATH", "") + ":/opt/homebrew/bin:/usr/local/bin")
    if node:
        subprocess.run([node, str(EXPORT)], timeout=20, capture_output=True)

if CACHE.exists():
    for e in json.loads(CACHE.read_text()):
        add(e["keys"], e["action"], f'{e["app"]} · {e["source"]}' + (f' · {e["where"]}' if e["where"] else ""))
else:
    items.append({"title": "Open the Hotkeys app once to build the list", "valid": False})

section = "Rules"
for line in (H / ".config/HOTKEYS.md").read_text().splitlines():
    if line.startswith("#"):
        section = "Rules · " + line.lstrip("# ").strip()
    elif line.startswith("|") and not re.match(r"^\|\s*-", line):
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[0] not in ("Key", "Layer"):
            add(cells[0], cells[1], section)

print(json.dumps({"items": items}))
