#!/usr/bin/env python3
"""Emit every documented hotkey as Alfred script-filter JSON; Alfred does the fuzzy filtering.

Sources: ~/.config/HOTKEYS.md (every two-column table, section heading = subtitle),
~/.config/tmux/shortcuts.txt, ~/.config/nvim/KEYBINDINGS.md.
"""
import json, re
from pathlib import Path

H = Path.home()
items = []

def add(key, action, src):
    key, action = key.strip(), action.strip()
    if len(key) > 2 and key[0] == key[-1] == "`":   # markdown code span, not a backtick key
        key = key[1:-1]
    if key and action:
        items.append({"title": f"{key}   →   {action}", "subtitle": src,
                      "arg": key, "match": f"{key} {action} {src}"})

def md_tables(path, label):
    """Yield (key, action, section) from markdown tables; skips header and rule rows."""
    section = label
    for line in path.read_text().splitlines():
        if line.startswith("#"):
            heading = re.sub(r"\s*\(.*\)$", "", line.lstrip("# ").strip())
            section = f"{label} · {heading}"
        elif line.startswith("|") and not re.match(r"^\|\s*-", line):
            cells = [c.strip() for c in line.strip("|").split("|")]
            if len(cells) >= 2 and cells[0] not in ("Key", "Modifier"):
                yield cells, section

for cells, section in md_tables(H / ".config/HOTKEYS.md", "Hotkeys"):
    if section == "Hotkeys · Hotkey layers":          # the layer map: Modifier | Owner | Scope
        add(cells[0], f"{cells[2]} ({cells[1]})", "Layer map")
    else:
        add(cells[0], cells[1], section.split(" · ", 1)[1])

for line in (H / ".config/tmux/shortcuts.txt").read_text().splitlines():
    m = re.match(r"^  (\S.*?\S)\s{2,}(\S.*)$", line)
    if m: add(m.group(1), m.group(2), "tmux")

for cells, section in md_tables(H / ".config/nvim/KEYBINDINGS.md", "nvim"):
    add(cells[0], cells[1], section)

print(json.dumps({"items": items}))
