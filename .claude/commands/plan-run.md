---
description: Produce a resumable runbook (long-run-planner → plan-critic) and stop, ready to execute
argument-hint: <what to build / run>
---

Produce a vetted **runbook** for the task below, then **stop** — do not execute it. A
runbook is a resumable, checkpointed plan where every small step has explicit pass/fail
criteria, built to survive a long autonomous run or a context reset.

**Task:** $ARGUMENTS

1. **Plan** — use `long-run-planner` to write the runbook to `.claude/plans/<slug>.md`.
2. **Critique** — use `plan-critic` to review it. If `REVISE`, send the blocking issues
   back to `long-run-planner`, rewrite the file, and re-critique (max 3 rounds).
3. **Stop** — once `APPROVED`, show me the final runbook, the critic's verdict, and the
   file path. Tell me I can execute it now (checking off each step as its success check
   passes, per the runbook's resume protocol) or edit the runbook first.
