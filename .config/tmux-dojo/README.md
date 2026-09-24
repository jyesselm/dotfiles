---
date: '2026-09-24'
type: ref/tool
status: active
aliases: [Tmux Dojo, Tmux Shortcut Practice]
tool-tags: [tmux, terminal, hotkeys]
---
# Tmux Dojo

Run `tmux-dojo` from a tmux shell. It opens a colorful practice popup; your actual panes stay in place. Outside tmux, it runs directly in the terminal.

Start with **1** for a short daily round or **2** for pane movement. Press the real shortcut shown by the task. **?** gives a hint, **Esc** skips, and **Ctrl+C** exits. After an answer, press **a** if the shortcut felt awkward, then **Enter** to continue. Press **q** to finish and view your results.

The game records mistakes, hints, timing, and awkward flags. Daily practice favors recent trouble spots. Choose **9** for progress or **0** for a shortcut reference. `tmux-dojo --report` prints your results from the shell.

## Try a different shortcut before changing it

Choose **8** for an A/B comparison:

| Action | Current keys | Trial keys |
| --- | --- | --- |
| Previous window | Ctrl+Space, then Ctrl+p | Ctrl+Space, then p |
| Paste | Ctrl+Space, then p | Ctrl+Space, then ] |

These trials only change the practice exercise. They do not change real tmux bindings. Targets are displayed, so times measure pressing a shown sequence rather than remembering it. Try several rounds and compare mistakes and comfort as well as time.

The current split between **leader+1–3 for panes** and **leader+4–9 for windows** is another possible simplification. Learn what feels awkward before choosing a replacement.

## The everyday keys

- **Ctrl+h/j/k/l:** move left/down/up/right between panes.
- **Leader+n:** next window. **Leader+Ctrl+p:** previous window.
- **Option+w/r:** work/remotes. **Leader+Tab:** previous session.
- **Leader+f:** search sessions and windows.
- **Leader+?:** action menu and cheat sheet.
- **Leader+y:** Yazi file browser.

Leader means **Ctrl+Space**, release, then the next key. Option shortcuts need the terminal to send Option as Esc+; your Mac's left Option is configured this way.

## On Swan

The old running tmux server is version 2.7. The updated setup uses the installed **tmux/3.6a** module and a separate socket named `modern`.

1. If inside old tmux, detach with **Ctrl+Space, then d**.
2. From the cluster shell, run `~/.local/bin/tmux-modern`.
3. Run `tmux-dojo` inside the new session.

The old server and its running panes remain available with `/usr/bin/tmux -L default attach`. A yadm pull updates files; it does not upgrade an already-running server.

Separate terminal tabs for local and cluster tmux let you use the same leader. When nested with Ctrl+Space on both, press **Ctrl+Space twice, then the command** to reach the inner tmux. Lesson **7** explains both arrangements.

## Colors and configuration

Session tabs use eight Catppuccin colors, assigned by tmux's session ID: teal, purple, peach, blue, yellow, pink, green, and lavender. Colors repeat after eight sessions and can differ after server restarts. The selected session is filled; inactive sessions have colored labels. Only the sessions label turns red and reads **PREFIX** when the leader is active.

Trainer source: `~/.config/tmux-dojo/tmux_dojo.py`.
Launcher: `~/.local/bin/tmux-dojo`.
Progress: `~/.local/state/tmux-dojo/progress.json` (local to each computer).

`tmux-dojo --check-bindings` checks the live shortcuts against the lesson snapshot. If you change bindings, update the lesson and snapshot together before continuing. Keep progress out of yadm; it is personal practice history.
