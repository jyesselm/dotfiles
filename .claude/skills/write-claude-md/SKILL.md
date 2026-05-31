---
name: write-claude-md
description: Generate or improve a project's CLAUDE.md (or AGENTS.md) following current best practices. Auto-detects the exact build/test/lint commands, keeps the file lean (target 60-150 lines), encodes rules as imperative NEVER/ALWAYS lines, and @imports shared standards instead of duplicating them. Use when a repository has no CLAUDE.md, has a bloated or stale one, or the user asks to write or improve project memory, agent instructions, or an AGENTS.md.
argument-hint: [path | improve | agents-md]
---

# write-claude-md

Produce a CLAUDE.md that makes Claude more effective in **this** repo — not a generic README. CLAUDE.md loads into context every session, so every line must earn its place.

## The one test
For each line, ask: **"Would removing this cause Claude to make a mistake?"** If not, cut it. Bloated files get ignored (Anthropic's own guidance). Target **60-150 lines**; warn the user if it exceeds ~200 and suggest splitting into `.claude/rules/` or an `@import`.

## Workflow
1. **Analyze the repo — read, don't guess.**
   - Detect stack & build system: `pyproject.toml`/`setup.py`, `package.json`, `CMakeLists.txt`/`Makefile`, `Cargo.toml`, `go.mod`, `environment.yml`, `justfile`, `Taskfile`.
   - Extract the EXACT commands: install, format, lint, typecheck, test, and crucially **"run a SINGLE test"** (the highest-value, hardest-to-guess line).
   - Map the top-level directory layout; flag generated / vendored / forbidden dirs ("do not edit").
   - Skim `README`, `CONTRIBUTING`, and CI (`.github/workflows/*`) for the commands the project actually uses.
   - **Improving an existing file?** Read it first; keep what's load-bearing, cut filler, fix stale commands, dedupe anything already in the global `~/.claude/CLAUDE.md`.
2. **Draft** using the structure in `template.md` (read it). Fill only the sections that apply.
3. **Factor out static content.** Instead of restating code style, `@import` the shared standard (`@~/.claude/standards/python-style.md`, `@~/.claude/standards/cpp-style.md`). Never duplicate rules that already live in a global or imported file.
4. **Encode rules as imperative one-liners.** `ALWAYS run \`make test\` after Python changes.` `NEVER edit \`data/raw/\` — it's generated.` Bold **NEVER/ALWAYS/CRITICAL** for the few that matter most.
5. **Push enforcement to the right layer.** Don't send an LLM to do a linter's job — if a rule is mechanically checkable (formatting, line length), name the tool/hook; don't enumerate the rule.
6. **Self-check** against `checklist.md` (read it). Report the final line count and flag any line that fails the "would removing this cause a mistake?" test.

## Modes (from $ARGUMENTS)
- *(default, or a path)* → write `CLAUDE.md` at the project root.
- `improve` → audit and prune the existing CLAUDE.md in place; show before/after line count and what you cut and why.
- `agents-md` → write a tool-agnostic `AGENTS.md` and make `CLAUDE.md` a one-line `@AGENTS.md` pointer (works across Claude Code, Cursor, Codex).

## Output
Write the file, then summarize: line count, sections included, `@imports` added, and anything you deliberately left out (and why). **Never invent a command you didn't verify** — if unsure, mark it `# TODO: confirm` rather than guessing.
