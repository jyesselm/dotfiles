# CLAUDE.md quality checklist (self-check before finishing)

## Must pass
- [ ] **Under ~150 lines** (hard-warn past 200). If longer, split into `.claude/rules/` or `@import`s.
- [ ] **Exact commands present and verified** — install, format, lint, test, and a *single-test* invocation. No guessed commands; unverified ones marked `# TODO: confirm`.
- [ ] **Every line passes the test**: "would removing this cause Claude to make a mistake?" If not, it's cut.
- [ ] **Rules are imperative and specific** — `ALWAYS`/`NEVER` one-liners, not prose. "Use 2-space indent" not "format nicely."
- [ ] **Shared standards are @imported, not restated** (`@~/.claude/standards/...`).
- [ ] **Generated/forbidden dirs are marked** "do not edit."
- [ ] **Most important rules first** (Claude reads top-down).

## Anti-patterns to remove
- ❌ **Bloat** — 300+ lines, dozens of sub-sections, full CLI dumps. The #1 failure mode; Claude starts ignoring it.
- ❌ **Duplicating the README** — link it (`See @README.md`) instead.
- ❌ **Restating content already in the global `~/.claude/CLAUDE.md`** (it's already loaded every session).
- ❌ **Self-evident filler** — "write clean code", "use good names", language conventions Claude already knows.
- ❌ **A linter's job** — enumerated formatting/quote/line-length rules. Name the tool or a hook instead.
- ❌ **File-by-file codebase narration** — describe only the non-obvious structure.
- ❌ **Stale version banners / commands** — if a refactor changed the build, the file must change too.
- ❌ **Vague rules Claude can't verify compliance with** — make them concrete or drop them.

## Layering reminder (where content belongs)
- **Always-true facts about this repo** → CLAUDE.md.
- **Cross-project preferences** → global `~/.claude/CLAUDE.md` (loaded everywhere).
- **A multi-step procedure that grew too big** → a skill (loads only when used).
- **A rule that must be enforced, not suggested** → a hook (CLAUDE.md is context, not enforcement).
- **Path-specific rules in a large repo** → `.claude/rules/<area>.md` scoped by `paths:`.
