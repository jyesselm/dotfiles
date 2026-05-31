---
description: Hands-off Python pipeline — plan → critique → code → verify (completeness + adversarial + review) → fix loop
argument-hint: <what to build>
---

You are running the Python feature pipeline in **AUTO mode**: drive it end-to-end with minimal human intervention, but refuse to declare success until independent fresh-context checkers confirm the work. Subagents do not share context — the handoff file is `.claude/plans/current-plan.md`.

**Task:** $ARGUMENTS

## Rules
- A checker's verdict line is the gate. Anything other than the pass verdict (`APPROVED`, `COMPLETE`, `ROBUST`, `APPROVE`) is **blocking**.
- **Max 3 rounds** per loop. If a loop can't converge in 3 rounds, STOP and summarize the unresolved issues — do not keep grinding.
- When looping back, send the specific findings to the agent, not the whole task again.
- For hands-off editing, I should be in auto-accept-edits mode (shift+tab) or have launched with `--permission-mode acceptEdits`.

## Stages
1. **Plan** — `py-planner`: design the task; write the plan to `.claude/plans/current-plan.md`.
2. **Critique the plan** — `plan-critic`: review it. If `REVISE`, send blocking issues back to `py-planner`, rewrite the file, re-critique. Loop (≤3) until `APPROVED`.
3. **Implement** — `py-coder`: read the plan, implement it exactly, run `ruff`/`mypy`/`pytest --cov` until green.
4. **Verify** — run THREE checkers, each in a fresh context, against the `git diff`:
   - `completeness-verifier` → catches stubs, truncation, skipped requirements
   - `test-adversary` → finds edge cases and breaking inputs
   - `py-reviewer` → quality, style, toolchain
5. **Fix loop** — collect every blocking finding from stage 4 into one list, send it to `py-coder`, then re-run stage 4. Loop (≤3) until all three pass.
6. **Human checkpoint** — pause and ask me before anything irreversible (git push, deleting files, data/schema migrations), and whenever a loop hits its round cap unresolved.

## Final report
What was built, the three verdicts, toolchain status, and any unresolved items.
