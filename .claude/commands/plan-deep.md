---
description: Build a vetted strategy by exploring 2-3 alternative approaches, picking the best, then stress-testing it with an independent skeptic until it holds up
argument-hint: <the decision, goal, or problem to strategize>
---

Produce a **detailed, structured, multiply-vetted strategy** for the problem below, then **stop**. This is for non-coding strategic thinking: research directions, experiments, manuscripts/grants, project or career decisions — anything where the goal is the best *plan of action*, not code. The point is that the strategy you read is the survivor of real alternatives and real adversarial review, with backup ideas kept on the table.

**Problem / goal:** $ARGUMENTS

First, if the problem is underspecified (missing the real goal, constraints, success criteria, timeline, or what's already been tried), **ask me 2-4 sharp clarifying questions and wait** before planning. A good strategy needs to know what "winning" means.

1. **Explore alternatives** — spawn a `general-purpose` strategist agent (give it the full problem + my answers). Tell it NOT to commit to one path yet. It must produce **2-3 genuinely distinct strategies** (not variations of one idea). For EACH:
   - a short sketch of the approach and the bet it's making,
   - **pros / cons**, key risks and assumptions it depends on,
   - the **failure mode + fallback/Plan B** if it goes wrong,
   - rough cost/effort, time horizon, and the biggest unknown.
2. **Pick the best** — have the strategist recommend ONE strategy with a crisp justification for why it beats the others against the success criteria, then expand it into concrete steps/milestones, each with a decision point, a leading indicator of success/failure, and a contingency. Keep the rejected strategies in a short **"Alternatives considered"** section so the reasoning survives. Write the whole thing to `.claude/plans/current-strategy.md`.
3. **Stress-test, repeatedly** — spawn an **independent skeptic** (`general-purpose` agent, fresh context, told to *attack* the strategy, not validate it): hunt unsupported assumptions, ignored risks, weak success criteria, better alternatives that were dismissed, and ways it quietly fails. It must end with `VERDICT: APPROVED` or `VERDICT: REVISE` plus the blocking issues. If `REVISE`, send those issues back to the strategist, rewrite the file, and re-review. Loop **up to 3 rounds**, stating each round's verdict so the vetting is visible. For research/manuscript problems you may use `paper-adversary` as the skeptic instead.
4. **Stop** — once `APPROVED` (or after 3 rounds, flagging any unresolved issues), show me the final strategy, the "Alternatives considered" section, and the skeptic's final verdict. Do not start executing — this gets me a vetted strategy to decide on.
