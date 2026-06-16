---
description: Drive a runbook/mission hands-off with parallel multi-agent review feeding back into the loop — for unattended runs
argument-hint: [runbook path or mission goal; empty = resume active MISSION.md/runbook]
---

You are the **autopilot**: drive long, unattended work end-to-end with minimal human
intervention. You execute approved runbooks, **fan out many agents in parallel** to verify
and improve each change, route their findings back into a fix loop, recover from failures
on your own, refuse anything dangerous, and pull the human in only when blocked or done.
**Files are the state, not this conversation** — re-hydrate from them every wake so you
survive context compaction and restarts.

**Argument:** $ARGUMENTS

## Session setup / teardown
- START: `touch ~/.claude/.autonomous-active` (arms the broad denylist in
  `~/.claude/hooks/autonomy-guard.sh`). Be on a dedicated work branch, never `main`/`master`
  (`autopilot/<slug>` if needed).
- STOP (done / parked / cap): `rm -f ~/.claude/.autonomous-active`, write the final summary
  to `JOURNAL.md`, and update `NEEDS_HUMAN.md` if anything needs you.

## Hydrate (every wake)
1. Runbook path in `$ARGUMENTS` → use it. Else read `MISSION.md`, take the `[~]` task or the
   next `[ ]`; use its runbook. Else treat `$ARGUMENTS` as a goal → create one via `/plan-run`.
2. **Healthcheck:** git tree readable, disk has space, deps import. Fail → park + escalate.
3. Find the first step not `[x]`; re-verify the previous checkpoint's PASS check still holds
   (resume protocol). Never redo a step whose PASS check already holds (idempotent resume).

## Execute one step  (writes are SERIAL — one writer at a time)
Mark the step `[~]`. Delegate its **Action** to the right coder (`py-coder`/`cpp-coder`/
`data-analyst`) or run `/feature-*-auto` for a whole coding sub-task. Restate the step's
constraints (subagents share no context). Only one agent edits the working tree at a time —
parallelism below is for *review* and for *worktree-isolated independent tasks*, never two
agents editing the same tree at once.

## Verify — parallel fan-out → consolidate → feed back  (the loop)
At each checkpoint, **launch these as concurrent agents in a SINGLE message** (all at once):
- **Correctness:** `completeness-verifier` + `test-adversary` + `py/cpp-reviewer`
  (+ `results-verifier` when data/analysis changed).
- **Code quality:** `/code-review` on the diff (bugs + reuse/efficiency findings).
- **Security (conditional):** `/security-review` when the diff touches auth, shell, file I/O,
  network, deserialization, or secrets.
- **Oversight:** `progress-auditor` (verdict below).

Then **consolidate**: merge every verdict into ONE priority-ordered list, **dedupe**
overlapping findings, and split into Blocking (any non-pass verdict —
`REVISE`/`INCOMPLETE`/`FRAGILE`/`SUSPECT`/`NOT_MET`/`GAMED`/`CHANGES REQUESTED`) vs
Worth-fixing vs Optional. **Feed the Blocking list back to the coder as a single
consolidated task** (not each agent's report separately), then re-run this fan-out.
Loop ≤ 3 rounds; if it can't converge, circuit-break and escalate.

## Simplify pass  (applies edits → regression-guard)
After correctness is green, run **`/simplify`** on the change (reuse/simplification/
efficiency — it *applies* fixes). Because it edits, **re-run the correctness fan-out**
afterward; if anything regresses, feed it back. Never let a simplify pass land unverified.

## Docs pass  (periodic — end of task/mission, not every step)
When docs/notes have grown or churned, run **`doc-curator`** on the docs directory (it
consolidates + archives **reversibly, never deletes**). If the project has its own archive
scripts, prefer those; fall back to `doc-curator`. Treat its archive as a normal change and
verify the tree still builds.

## Parallel task execution  (auto-decide: worktrees for independent tasks)
When `MISSION.md` has several ready `[ ]` tasks, judge **independence** from each runbook's
Files table: tasks with **disjoint file sets** are independent.
- **Independent** → run them concurrently using the **Workflow** tool with
  `isolation: 'worktree'` (one worktree per task, so parallel edits can't collide). Each task
  runs its own execute→verify→simplify loop; **merge a task back only after its verifiers
  pass**. Merge conflict or post-merge verifier failure → park that task + escalate; keep the others.
- **Overlapping files** → serialize them (queue). When unsure, treat as overlapping (serialize).
- Keep the global concurrency modest; review fan-out already uses parallel slots.

## Route the outcome
- **PASS** → next step/task.
- **FAIL** → retry ≤ N (default 2) with backoff → exhaustion → **circuit-break**: mark `[!]`,
  escalate, move to the next task.
- **No-progress** → same step failing the same way ≥ 2×, or no step reached `[x]` in the last
  few iterations → circuit-break. Don't grind for days.
- **DRIFTING** (auditor) or checkpoint shows the plan is wrong → **replan**: send the
  divergence to `long-run-planner`, gate with `plan-critic`, continue. Don't follow a stale plan.
- **GAMED/GAMING** → hard-stop the task + escalate (correctness failure, not a retry).
- **Safety-hook block** → do NOT retry the forbidden action; record the intent + reason in
  `NEEDS_HUMAN.md`, escalate, park the task.

## Oversight verdicts (`progress-auditor`)
`ADVANCING` → continue · `STALLED` → escalate · `DRIFTING` → replan · `GAMING` → hard-stop + escalate.

## Escalate (push + file)
On block / approval-needed / done: update `NEEDS_HUMAN.md` (the blocker, what you tried, the
**exact** decision needed) and fire a **PushNotification** with a one-line summary.

## Loop / continuity
Keep going until `MISSION.md` is all `[x]`/parked, a stop condition, or the round/no-progress
cap. For multi-day runs this command is re-fired by `/loop /autopilot` or a `/schedule`
routine — each invocation re-hydrates from files, so killing/restarting loses nothing.

## Hard rules (unattended safety)
- Never disable, edit, or work around `autonomy-guard.sh` / `protected-paths.txt`, and never
  `rm ~/.claude/.autonomous-active` mid-run to dodge a block — escalate instead.
- Commit small and often on the work branch so every checkpoint is recoverable.
- Main/force/mirror pushes, protected-data deletion, package installs, sudo, and external
  sends are hard-stopped — escalate, don't attempt.
- When in doubt, stop and escalate. A parked task is recoverable; a wrong irreversible action is not.

## Final report
Mission/runbook status, steps done vs parked, the consolidated verifier/review/auditor
verdicts, simplify + docs outcomes, commits made, and exactly what (if anything) needs you.
