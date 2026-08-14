# Blind test log

Running record of matched-pair tests. Design: the same content rendered twice,
once by him and once generated, so only the writing differs. Content is held
constant because topic was what defeated three attempts at a learned voice model
(see `METHOD.md`).

The score is the least useful output. **The tells he names are the point**, since
those become rules and persist; a score does not.

---

## Round 1 — 2026-08-14, 2 items

| Item | Source | Truth | His call |
|---|---|---|---|
| 1A | generated from the facts of the 2019 RNAMake paragraph | generated | "mine" ✗ |
| 1B | 2019 RNAMake, `Yesselman_MiniTTR.Draft.9.docx` | his | — |
| 2A | 2017 RMDB, `Yesselman.RMDB.final.revised.docx` | his | "mine" ✓ |
| 2B | generated from the facts of 2A | generated | — |

**Result: 1/2.** His comment: *"honestly it was hard to tell."*

**What it is worth.** At n = 2 this is a coin flip and carries no statistical
weight. It is the first positive signal on the success criterion, nothing more.

**The one substantive finding.** Item 1A was written by deliberately applying his
*stated* preferences (purpose opener, plain verbs, numbers with scope, short
sentences, no nominalizations) and he read it as his own writing. His actual 2019
prose in 1B contains three things his own guide now flags: a comma splice
("outliers occurred at helix edges"), a nominalization ("supported **the
formation of**"), and in 2A the word "utilized", which he corrected to "use" in
his own tracked edits.

So prose written to his stated preferences read as more like him than his own
older prose did. This is the first evidence for the "stated preference beats
measured corpus" rule that did not come from him simply asserting it.

**Caveats that keep this honest.**
- Both source paragraphs are from 2017 and 2019, a register he has since moved away from. Generated text is competing against his older self.
- 1A and 2B were hand-written with the test in mind. **That is not the same as normal pipeline output**, and the honest version of this test uses prose generated through `plan-writing.md` under ordinary conditions.
- No tells were named this round, so nothing was encoded. That is the round's real failure.

**Next round should:** use ≥15 items, draw his side from 2025-2026 prose, generate
the machine side through the normal drafting pipeline rather than by hand, and ask
for the tell before the verdict.
