# Global conventions

## Leanness (reuse before you add)

Default to reuse and subtraction. Before writing a new function, file, or doc section, grep for an
existing one and reuse or extend it. Edit don't append; reference don't copy; no new files or docs
unless needed. Abstract on the 3rd duplication, not the 1st. When a change makes something obsolete,
delete it in the same change. Full rules: `~/.claude/standards/leanness.md`.

## Code and writing standards

Python: `~/.claude/standards/python-style.md`. C++: `~/.claude/standards/cpp-style.md`.
Prose (papers, grants, reviewer responses): `~/.claude/standards/writing-style.md` and the guides under
`~/.claude/standards/writing/`. Read the relevant one before non-trivial work in that language.

For non-trivial changes: plan first, show the plan, then implement and review the diff yourself
against the standards before reporting done.

## Machines

Every computer is defined by the yadm dotfiles repo (`~/.config/yadm/setup/README.md`).
`converge sync` converges a machine; `converge status` shows the last run and how to clear each warning. Config edits go in tracked
files; manifests (`Brewfile*`, `apps.json`, `layout.txt`, `~/.config/git-repo-checker/active.yml`) are the
source of truth for packages, apps, directories and repos. Paths are always `$HOME`-relative.

## Joe's tasks (Tasks app only)

Task work goes ONLY to the Tasks app (API :8767); never touch Todoist (Joe, 2026-10-11). Multi-step work is a **chain** in
Joe's approved format: many small steps, each a ≤6-word verb title plus a `note` with 2–4 lines of
exact clicks/URLs (one action per line). Email tasks start with `📧 account · sender · "subject" · date`.
Full rules: memory `task-step-format.md` and `task-sync-and-email-rules.md`.

## Joe's notes app

Notes live in his own app (http://127.0.0.1:8766, files under `~/local/code/web/notes/notes/`), not in Obsidian any more.
Anything that reads or writes a note loads the `notes` skill (`~/.claude/skills/notes/SKILL.md`): page layout, vocabulary, API, rules.
