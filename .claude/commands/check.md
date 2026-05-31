---
description: Fan out the verification agents on the current work in parallel
argument-hint: [optional focus, e.g. "the diff in src/foo.py"]
---

Run the appropriate checkers **in parallel** (a single message, multiple agents) on the current changes${ARGUMENTS:+ — focus: $ARGUMENTS}, then consolidate.

1. Look at what changed (`git diff`, `git status`).
2. Choose checkers by content and launch them **at the same time**:
   - Python code changed → `completeness-verifier` + `test-adversary` + `py-reviewer`
   - C++ code changed → `completeness-verifier` + `test-adversary` + `cpp-reviewer`
   - Analysis / data / results changed → `results-verifier` (+ `completeness-verifier`)
3. Collect every verdict line and merge findings into one priority-ordered list:
   - **Blocking** (any non-pass verdict: REVISE / INCOMPLETE / FRAGILE / SUSPECT / CHANGES REQUESTED)
   - **Worth fixing**
   - **Optional**
4. End with the combined verdict and, if anything is blocking, the exact next fix.

Do not edit code — this is a read-only check. If everything passes, say so plainly.
