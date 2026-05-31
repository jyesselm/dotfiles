---
description: Run the C++ planner → coder → reviewer pipeline for a feature
argument-hint: <what to build>
---

You are orchestrating a three-stage C++ development pipeline. Subagents do **not** share context, so the handoff between stages is a file: `.claude/plans/current-plan.md`.

**Task:** $ARGUMENTS

Run these stages in order. Do not skip the approval pause.

1. **Plan** — Use the `cpp-planner` subagent to design the implementation for the task above. Instruct it to write its final plan to `.claude/plans/current-plan.md`.
2. **Approve** — Show me the plan and **pause for my approval**. If I request changes, send them back to `cpp-planner` and rewrite the file before continuing.
3. **Implement** — Use the `cpp-coder` subagent. Tell it to read `.claude/plans/current-plan.md`, implement the plan exactly, and run the full toolchain (`clang-format`, `clang-tidy`, `cmake --build`, `ctest`) until it passes.
4. **Review** — Use the `cpp-reviewer` subagent to review the resulting `git diff` against the plan. Relay its verdict and findings to me by priority.
5. **Fix loop** — If the reviewer returns CHANGES REQUESTED with Critical issues, send those specific findings back to `cpp-coder`, then re-run `cpp-reviewer`. Repeat until APPROVE or I tell you to stop.

At the end, give me a one-paragraph summary: what was built, toolchain status, and the reviewer's final verdict.
