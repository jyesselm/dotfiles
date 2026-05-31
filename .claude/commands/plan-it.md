---
description: Produce an approved plan (planner → plan-critic) and stop, ready for review
argument-hint: <what to build>
---

Produce a vetted implementation plan for the task below, then **stop** — do not write code. This gets you an approved plan you can eyeball before committing to implementation.

**Task:** $ARGUMENTS

1. **Plan** — use the right planner for the task (`py-planner` for Python, `cpp-planner` for C++, `research-planner` for an experiment/analysis). Have it write the plan to `.claude/plans/current-plan.md`.
2. **Critique** — use `plan-critic` to review it. If `REVISE`, send the blocking issues back to the planner, rewrite the file, and re-critique (max 3 rounds).
3. **Stop** — once `APPROVED`, show me the final plan and the critic's verdict. Tell me I can run `/feature-py-auto` (or `/feature-cpp-auto`) to implement it, or edit the plan first.
