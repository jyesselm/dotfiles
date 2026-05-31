---
description: Iterate code until it meets a defined quantitative goal (match a value/output, or hit a threshold)
argument-hint: <goal, e.g. "melting_temp matches tests/reference_tm.json exactly">
---

Drive an **objective-metric loop**: implement and adjust until a measurable goal is MET. The discipline that makes this terminate is **locking the metric up front and never moving it.**

**Goal:** $ARGUMENTS

## 0. Lock the metric (do this FIRST)
Turn the goal into a measurable spec and write it to `.claude/plans/current-goal.md`:
- **metric** (what number), **measurement** (exact command that prints it), **target** + **comparison** (`==` / `≥` / `≤` / within ±tol).
If the goal isn't yet measurable, ask me the minimum needed to make it so, THEN lock it. **Do not start the loop without a locked, machine-checkable metric** — an unmeasurable goal never terminates.

## Loop (max 5 rounds)
1. **Implement / adjust** — `py-coder` (or `cpp-coder`): make the change. It may NOT edit the goal file, the reference data, or the measurement/tests.
2. **Evaluate** — `goal-evaluator`: measure and emit `MET` / `NOT_MET` / `GAMED`.
3. **Branch**:
   - `MET` → Done.
   - `GAMED` → reject; tell the coder the result must be achieved legitimately (no hardcoding/overfitting/weakening the check); redo the round (counts toward the cap).
   - `NOT_MET` → feed the measured value + gap + diagnosis back to the coder. **Log the round's value** so we can see the trajectory.

## Stop conditions
- `MET` → Done.
- Round cap hit, or the metric plateaus across 2 rounds → STOP. Report the trajectory (value per round) and say whether this looks like a fixable bug or a target that may be infeasible with this approach. Do not thrash.

## Done report
Final measured value vs target, the round-by-round trajectory, and confirmation the integrity check is clean.
