---
description: Brainstorm widely with several independent strategists in parallel, synthesize the best strategy against explicit success criteria, then stress-test it with a skeptic until it holds up
argument-hint: <the decision, goal, or problem to strategize>
---

Produce a **detailed, structured, multiply-vetted strategy** for the problem below, then **stop**. This is for non-coding strategic thinking: research directions, experiments, manuscripts/grants, project or career decisions — anything where the goal is the best *plan of action*, not code. The point is that the strategy you read is the survivor of wide, genuinely-independent brainstorming and real adversarial review, judged against a rubric you set up front, with backup ideas kept on the table.

**Problem / goal:** $ARGUMENTS

First, if the problem is underspecified (missing the real goal, constraints, success criteria, timeline, or what's already been tried), **ask me 2-4 sharp clarifying questions and wait** before strategizing.

Then **pin the rubric**: write a short **"What winning looks like"** block — the goal in one line, the hard constraints, and 2-4 *measurable* success criteria. This is what every later step is judged against. Restate it verbatim to every agent you spawn.

1. **Brainstorm widely, in parallel** — spawn **3-4 independent `general-purpose` strategist agents at once** (in a single message, so they run concurrently and cannot influence each other). Give each the full problem, my answers, and the rubric. Tell each to commit to ONE approach, and assign each a **different stance** so they do not converge: e.g. the fastest/cheapest path, the highest-upside/ambitious bet, the lowest-risk/most-robust play, and one deliberately unconventional angle. Each agent returns, **in its final message** (do NOT have them write to a shared file — parallel agents clobber each other's work):
   - a short sketch of the approach and the bet it is making,
   - **pros / cons**, key risks and assumptions it depends on,
   - the **failure mode + fallback/Plan B** if it goes wrong,
   - rough cost/effort, time horizon, and the biggest unknown,
   - a quick **self-score against each success criterion**.
2. **Synthesize and pick** — review all the proposals (yourself, or via one synthesizer agent). Recommend ONE strategy with a crisp justification for why it beats the others against the success criteria, **grafting the best ideas from the runners-up** rather than discarding them. Expand the winner into concrete steps/milestones, each with a decision point, a leading indicator of success/failure, and a contingency. Keep the rejected approaches in a short **"Alternatives considered"** section so the reasoning survives.
3. **Stress-test, repeatedly** — spawn an **independent skeptic** (`general-purpose` agent, fresh context, told to *attack* the strategy, not validate it): hunt unsupported assumptions, ignored risks, success criteria that are weak or not actually met, better alternatives that were dismissed, and ways it quietly fails. It must **score the strategy against each success criterion** and end with `VERDICT: APPROVED` or `VERDICT: REVISE` plus the blocking issues. If `REVISE`, send those issues back to the synthesis step, rewrite the strategy, and re-review. Loop **up to 3 rounds**, stating each round's verdict so the vetting is visible. For research/manuscript problems you may use `paper-adversary` as the skeptic instead.
4. **Stop** — once `APPROVED` (or after 3 rounds, flagging any unresolved issues), show me the final strategy, the "What winning looks like" rubric with how the strategy scores against it, the "Alternatives considered" section, and the skeptic's final verdict. Do not start executing — this gets me a vetted strategy to decide on.
