# How this guide gets built (read before extending it)

Written 2026-08-14 after two days of building. This file exists so the same
mistakes are not repeated. It records what worked, what failed, and the rules for
adding anything new.

## What actually works

**His corrections on real drafts, encoded immediately with a corpus count.**
This is the only mechanism that has produced durable rules. On 2026-08-13, five
rejections across two paragraphs produced five rules that still stand, each
verified against the corpus (*carrying* 2 uses vs *containing* 32; *set* as a
verb 0 of 32 occurrences; *supplies* 3 vs *provides* 32). By contrast, 39,000
words of corpus mining produced a **wrong** sentence-length rule, because the
corpus was contaminated.

**Ratio to remember: a handful of his corrections beat tens of thousands of words
of text.** Text says what he wrote. Corrections say what he wants, and the two
differ often enough that the second overrides the first.

**`bin/voice-lint.py` is the working judge.** Symbolic, readable, editable, and
every rule traceable to a correction plus a count.

## What failed (do not retry without new data)

Three machine-learning attempts to score "how much does this read like him", all
failing the same held-out sanity test on text of known authorship:

1. **Function words + logistic regression** — chance (balanced accuracy 0.53, AUC 0.58).
2. **Character n-grams, his prose vs AI prose** — AUC 0.984, but the top features were `will`, `motif`, `ttr` versus `switch`, `tmo`, `mut`. It learned **topic**, not voice. Scored his own paper prose 0.213 and deliberately bad AI prose 0.715.
3. **Paired tracked-revision model** (33 engineered features, topic controlled by construction) — AUC 0.814 on its own task, but **4/9 on the authorship sanity test, worse than chance**. It learned to tell inserted revision fragments from deleted ones, which does not transfer to finished paragraphs.

Adding 6,024 masked n-grams to attempt 3 made it **worse** (0.754 vs 0.814):
337 training pairs support roughly 30 features, not thousands. **The bottleneck
is labeled data, not feature count.**

Conclusion: what he responds to is semantic (is the *why* stated, are the n and
error bars present, is the verb *determines* or *sets*) and close to invisible in
surface statistics. Do not build another learned judge without several thousand
labeled paragraphs.

## What the failed models did prove

The paired-revision analysis independently rediscovered rules derived from his
verbal feedback, which is the only external validation those rules have. Comparing
his revisions against the text they replaced (337 pairs, 93 documents):

| Measure | His revision | What it replaced |
|---|---|---|
| numeric density | 8.39 | 6.56 (**+28%**) |
| length | 48.9 words | 42.6 |
| nominalizations | 2.91 | 3.26 |
| mean word length | 5.11 | 5.16 |
| relative "that" | lower | higher |

He edits by **adding numbers and length, and cutting nominalizations and long
words**. That is "not enough detail" and "Utilization → Use" measured in behavior
rather than stated as a preference.

## Provenance: the first question about any source

Five contamination classes have been found, four of them after a rule had already
been built on the bad data:

1. **Student-written drafts.** `TMO_DMS_manuscript_draft3_JDY.docx` carried his initials and was his student's. It had supplied 64% of the sentences behind the stylometric panel.
2. **Collaborator tracked changes.** `Pepper-sequence_ms_15-JDY.docx` holds 987 revisions by Catherine Eichhorn and 3 by him; an unfiltered pass attributed a lexical rule set to him that was hers.
3. **My own output.** The `2025-atp-ttr-switch` manuscript refinement cycles and `2026-3d-structure-issues/claims_ledger.md` are agent-generated. Training on them would close a self-confirmation loop.
4. **Postdoc-era grants.** 2016-2017 material under Das is substantially Das's writing.
5. **Non-prose.** Letters, budgets, biosketches, and letters of support are a different register entirely.

**Rules that follow:**
- A `_JDY` suffix is **not** evidence of authorship. Neither is a file living in his Dropbox.
- Filter tracked changes by the `w:author` attribute, always. Match the substring `Yesselman`; his name appears as both "Joseph Yesselman" and "Joseph David Yesselman".
- Verify counts **case-insensitively**. A case-sensitive grep once produced a confident, wrong claim that "however" never appears in his prose (it appears 7 times).
- When his stated preference contradicts the measured corpus, **the stated preference wins**. This reversed the sentence-length rule and the colon/semicolon rule; both had described his past practice rather than his intent.

## Not yet mined (highest value first)

- **312 margin comments** in `word/comments.xml` across his docx files, author-attributed. Missed entirely at first because the extractor read only `word/document.xml`. Use them as a **failure-mode checklist, never as a prose source**: they are deficiency reports, so a model trained on them learns "always add more detail" and produces over-explained prose.
- **Comment → next-version linkage.** Where a comment states a problem and a later draft resolves it, the pair gives problem plus solution, which escapes the critique bias above.
- **Version-chain diffs.** 283 near-duplicate files were folded during deduplication; each successive pair is a decision he made.
- **Corpus expansion** pending his provenance calls: 210 files, 501,021 words across 36 projects, in `~/Downloads/voice-corpus-final.csv`.

## Before adding volume, add retrieval

The guide is already ~21,000 tokens. Loading more exemplars into context crowds
out the draft. A larger corpus only helps once something selects the two or three
relevant exemplars per paragraph. **Build retrieval before importing more text.**
