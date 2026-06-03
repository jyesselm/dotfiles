# Global conventions

## Coding agent pipeline

Non-trivial Python/C++ work runs **planner → coder → reviewer**:

- `/feature-py <task>` and `/feature-cpp <task>` drive the full pipeline.
- Planners (`py-planner`, `cpp-planner`) write the approved plan to `.claude/plans/current-plan.md`.
- Coders (`py-coder`, `cpp-coder`) read that file, implement it, run the toolchain.
- Reviewers (`py-reviewer`, `cpp-reviewer`) are **read-only** and audit the `git diff`.

Subagents do **not** share context — `.claude/plans/current-plan.md` is the handoff. When
delegating manually, restate any critical constraint in the delegation prompt.

Shared code standards live in `~/.claude/standards/python-style.md` and `cpp-style.md`.

## Leanness (reuse before you add)

Default to reuse and subtraction; agents over-add. Before writing a new function, file, or doc
section, grep for an existing one and reuse or extend it. Edit don't append; reference don't copy;
no new files or docs unless needed. Abstract on the 3rd duplication, not the 1st. When a change
makes something obsolete, delete it in the same change. Full rules: `~/.claude/standards/leanness.md`.

## Verification agents (checking other agents' work)

These run in a **fresh, isolated context** and are **read-only** — they re-read files on
disk rather than trusting another agent's "done" claim. Each ends with a machine-readable
verdict line:

- `plan-critic` — reviews a plan before coding (`VERDICT: APPROVED | REVISE`)
- `completeness-verifier` — catches stubs, truncation, skipped requirements (`COMPLETE | INCOMPLETE`)
- `test-adversary` — tries to break the code, finds edge cases (`ROBUST | FRAGILE`)
- `results-verifier` — sanity-checks scientific results/numbers vs the data (`SOUND | SUSPECT`)

## Auto pipelines

`/feature-py-auto` and `/feature-cpp-auto` run plan → plan-critic → code →
(completeness-verifier + test-adversary + reviewer) → fix loop, hands-off, with a
**max of 3 rounds** per loop and a human checkpoint before anything irreversible.
A verdict other than the pass value is blocking. Run in auto-accept-edits mode
(shift+tab) for true hands-off operation.
