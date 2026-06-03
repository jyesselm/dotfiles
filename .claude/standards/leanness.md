# Leanness & Reuse

Default to reuse and subtraction. AI agents (and people) over-add: an analysis of 211M lines of
AI-assisted code found cloned blocks rose ~8x while refactoring collapsed from 24% to 9.5% of
changes (GitClear, 2025). Counteract that bias deliberately, on every task.

## Before adding anything
- **Search first.** Before writing a new function, file, or doc section, grep for an existing one.
  Reuse or extend it. Say what you reused, or that you checked and found nothing.
- **Edit, don't append. Reference, don't copy.** Prefer changing an existing file or section over
  creating a new one. Link to the source of truth instead of duplicating its content.
- **No new files or docs unless needed.** Don't add READMEs, helper modules, or doc files unless
  asked or clearly necessary.

## When to abstract (avoid the opposite mistake)
- **Rule of Three.** Duplication is cheaper than the wrong abstraction. Don't extract on the 1st
  or 2nd use; extract a shared helper on the 3rd, when the real pattern is visible.
- A new abstraction with a single caller is premature; inline it.
- A tangled shared abstraction is worse than duplication: re-inline it, then re-abstract once the
  pattern is clear.

## Subtract as you go
- **Leave it no larger than it must be.** When a change makes code or docs obsolete, delete them in
  the same change. Deleting is real work, not an afterthought.
- **The removal test** (docs, rules, comments): for each line, ask "would removing this cause a
  mistake?" If not, cut it.

Keep this file lean too.
