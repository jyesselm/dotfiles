---
description: Run the Python planner → coder → reviewer pipeline for a feature
argument-hint: <what to build>
---

You are orchestrating a three-stage Python development pipeline. Subagents do **not** share context, so the handoff between stages is a file: `.claude/plans/current-plan.md`.

**Task:** $ARGUMENTS

Run these stages in order. Do not skip the approval pause.

1. **Plan** — Use the `py-planner` subagent to design the implementation for the task above. Instruct it to write its final plan to `.claude/plans/current-plan.md`.
2. **Approve** — Show me the plan and **pause for my approval**. If I request changes, send them back to `py-planner` and rewrite the file before continuing.
3. **Implement** — Use the `py-coder` subagent. Tell it to read `.claude/plans/current-plan.md`, implement the plan exactly, and run the full toolchain (`ruff`, `mypy`, `pytest --cov`) until it passes.
4. **Review** — Use the `py-reviewer` subagent to review the resulting `git diff` against the plan. Relay its verdict and findings to me by priority.
5. **Fix loop** — If the reviewer returns CHANGES REQUESTED with Critical issues, send those specific findings back to `py-coder`, then re-run `py-reviewer`. Repeat until APPROVE or I tell you to stop.

At the end, give me a one-paragraph summary: what was built, toolchain status, and the reviewer's final verdict.
