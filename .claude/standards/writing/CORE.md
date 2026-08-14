# Writing voice: core (all genres)

## THE CARD — read this even if you read nothing else
Ten rules carry most of the quality. Everything below this section is reference.
Two consecutive blind tests (2026-08-14) failed on rules already in this file
because they sat sixty lines down, so they are hoisted here.

1. **Run the gate before showing any paragraph.** `python3 ~/.claude/standards/writing/bin/voice-lint.py --genre paper|grant FILE`. It has caught every recent miss. Skipping it is the most common failure.
2. **Lead with purpose, at two levels.** Why the question matters, *and* why this measurement answers it. His most frequent margin note on other people's drafts is a demand for the missing why: *"its not clear why mg2+"*.
3. **Sentence length is section-dependent.** Introduction ~17 words median. Results ~24. Measured on his fresh writing. Prefer short; reach for a long sentence deliberately, for interpretation, never by default.
4. **Introductions give background first and climb to the gap.** Four or five sentences of ladder before naming what is missing. Never open on the gap.
5. **Every number carries its n and its uncertainty.** Per subgroup, not just the total. If a number is missing, write the literal `XXX` and keep going. Never fuzz a countable figure ("approximately 5,000" was rejected; "hundreds of thousands" is fine).
6. **Name every entity.** "GC-L4-A91G", not "some constructs". "the 205 discarded", not "low-quality data".
7. **Plain conventional verbs.** determine, contain, provide, measure. **Never** *sets* (0 verb uses in 28,599 words), *carries* (0 uses), *supplies*, *closing on*, *baseline*. This is the mechanism behind "words that don't really fit".
8. **Write sentences OF the science, not ABOUT it.** State the physical fact; do not comment on what your measurement reports, overstates, or is the readout for.
9. **No em-dashes. No hype** (*groundbreaking*, *unprecedented*, *exciting*). **No hedging** (*we hope*, *we believe*, *it is anticipated*). Priority claims are stated flatly: "the first X".
10. **Where his stated preference contradicts the measured corpus, the preference wins.** This has reversed three rules already. The corpus records where he has been.

**Before drafting:** pull 2-3 matching exemplars from `EXEMPLARS.md` and map onto
one, then rewrite once freely. Reuse his verbs verbatim rather than paraphrasing
them; paraphrasing his own MIRA sentence produced *supplies* and *carry*, both rejected.

---

Universal rules for writing in Yesselman's voice. Genre files (papers, grants,
reviewer-responses, short-form) `@import` this and add only their delta.

Rebuilt 2026-06-25 from his own-hand 2025-26 corpus (see "Evidence base" at the
end); stylometric panel re-measured 2026-08-13. Every load-bearing rule below
carries a verbatim quote from that corpus, with the source file in parentheses.
When in doubt, imitate the quoted sentence, do not paraphrase the rule, and reach
for `EXEMPLARS.md` before reaching for any rule here.

## The voice in three words
Clear. Concise. Direct. High-density, unornamented prose that lands a quantitative
claim, then interprets it in one short follow-up. Concise means no wasted words,
not short sentences: his sentences are long and densely packed.

## Stylometric panel (re-measured 2026-08-13 over ~39,000 words, TMO-free)
Use this as a self-check, **not as a voice test**. Measured over prose only,
excluding methods, figure legends, references, and editorial notes, and
excluding the student-written TMO/DMS draft.
- **What he has written, by register: papers median ~25 (RNAMake 2019 n=329 median 25; RMDB 2017 n=80 median 22; d3f rewrites n=51 median 28); grants median ~20 (R01 n=198 median 19; MIRA A n=40 median 22); progress reports median ~16.** Lint with `--genre`; the registers differ enough that a single band misleads.
- **MEASURED ON FRESH WRITING, 2026-08-14: median 17 words.** Asked to draft an introduction opening from scratch, he produced 7 sentences of lengths 17, 17, 15, 14, 20, 29, 22. The generated attempt on the same prompt ran 4 sentences at median 29. **He writes roughly half the sentence length the generator defaults to.** This is the single most reliable tell found so far, and it is a failure to follow a rule already in this file, not a missing rule. Target median 17-20 for fresh prose; the higher numbers below describe older documents.
- **What he WANTS is shorter than that (stated 2026-08-13, and it overrides the panel).** Of a paragraph at median 24, i.e. at his own paper median, he wrote: *"you also have sentences that are too long, definitely want shorter simpler sentences, it cant be all the time but should prefer."* **Prefer short and simple; reach for a long sentence deliberately, for interpretation, not by default.** The numbers above describe his past practice; this line describes his intent, and intent wins. The gate is asymmetric to match: long prose fails, short prose only warns.
- **These bands do NOT identify his voice.** A function-word classifier trained to separate his prose from his student's performs at chance (balanced accuracy 0.53, AUC 0.58), and the student's draft measures *longer* than his own writing (median 26 vs 22-25). What identifies him is the *why*, the specificity, and the verb choices below.
- **The length target is not uniform within a paragraph (2026-08-13 clinic).** Given a staccato paragraph to fix, he merged the *interpretive* sentences ("There the ratio drops to 3.2-fold. Stacking explains part of this." became "There, the ratio drops to 3.2-fold which can be explained by increased stacking") and left a run of *parallel quantitative reports* untouched as three short sentences. Report numbers in clipped parallel sentences; subordinate mechanism and interpretation into the long ones. Do not lengthen a number run to hit the median.
- **Colons and semicolons: avoid them by preference, though not by rule (stated 2026-08-13).** *"we generally want to avoid colons and semicolons although this shouldnt be hard rule."* His existing prose uses them freely (colon 3.5-10 per 1,000 words, semicolon 2-7), and earlier versions of this file called them his load-bearing tics. **That was a description of past practice, not of intent.** Prefer a comma, a parenthesis, or a new sentence; keep a colon when it genuinely introduces a definition and nothing else reads as well. The gate no longer asks for more of them.
- **Em-dashes: banned by his own standing preference, not by corpus frequency.** The own-hand corpus actually contains them (19 in the dms-3d-features rewrites, 5 in MIRA Section A); he is correcting them out. Treat the ban as an instruction, not an observation. See the no-dash override below.
- Enforced automatically by `bin/voice-lint.py` (`--genre paper|grant`).

## Drafting protocol (follow this; reading the rules alone does not transfer the voice)
Rules describe the voice, examples demonstrate it, and imitation is what actually
carries it into a draft. For every paragraph:
1. **Pick the rhetorical job** (abstract-arc, intro-gap, results-open, results-landing, contrast-bridge, discussion-close, grants-gap, grants-aims, grants-impact) and paste 2-3 matching exemplars from `EXEMPLARS.md` into working context.
2. **Map your content onto one exemplar's skeleton**, sentence role by sentence role. Long sentences are the default: aim for a median near 25 words in papers, 20 in grants.
3. **Rewrite the mapped draft once, freely**, so it reads as one connected thought rather than a filled-in template. Skeleton mapping establishes the rhythm; this pass removes the seams.
4. **Reuse his verbs, do not paraphrase them.** If an exemplar states the same claim, take its wording verbatim. In a 2026-08-13 review, paraphrasing his own MIRA sentence produced "supplies" for *provides* and "carry" for *powering*, and he rejected both. When no exemplar covers the claim, choose the plain conventional scientific verb (determine, contain, provide, measure) over any compressed or figurative alternative: *sets*, *carrying*, *closing on*, and *supplies* were each rejected in one pass. **This is the mechanism behind "words that don't really fit".**
5. **Check `REJECTIONS.md`** and cut anything on it.
6. **Run the gate:** `python3 ~/.claude/standards/writing/bin/voice-lint.py --genre paper|grant <file>`. Fix every FAIL and reconsider each WARN before anyone reads the draft.

## Independent validation of these rules (2026-08-14)
A model trained on 337 of his tracked revisions, comparing each edit against the
text it replaced (topic and document held constant), rediscovered several rules in
this file without being told them. His revisions carry **28% more numeric content**
(8.39 vs 6.56 per 100 words), run **15% longer**, and use **fewer nominalizations**
and **shorter words**. That is the "not enough detail" rule and the
"Utilization → Use" rule confirmed in behaviour rather than in what he said.
The same model **fails** at judging finished prose (4/9 on known authorship), so it
is evidence for these rules, not a gate. See `METHOD.md`.

## File map (single-authority rule)
Prose rules live **only in this file**. Everything else carries data, never rules:
`EXEMPLARS.md` (verbatim paragraphs by job), `REJECTIONS.md` (never-say lexicon),
`bin/voice-lint.py` (the automated gate), and the genre deltas (`papers.md`,
`grants.md`, `reviewer-responses.md`, `short-form.md`). If any other file appears
to state a voice rule, this file wins and that file is stale.

## Principles
- **Active voice, first-person plural, for his own work.** "We" carries every claim about what the lab did; "I" is absent from papers. "we systematically analyzed DMS reactivity across a library of 7,500 RNA constructs" (dms-3d-features/abstract_intro_discussion_rewrite.md).
  - **Carve-out (2026-08-13): the passive is correct for describing what the field does.** 18 attested uses, e.g. "Deposited structures **are used** to generate mechanistic hypotheses" and, in his own hand on this grant, "predicted secondary-structure stability **is utilized** to assess whether a structure might be functional". Reserve "we" for his lab's actions; describe common practice impersonally.
- **Commit; police over-hedging.** Verbs are "we show," "we demonstrate," "we recover," not "we suggest" or "it appears." At most one qualifier, only where the data is genuinely partial. He actively removes surviving hedges from his own drafts.
- **Concrete, numbers inline with `=`.** "(R² = 0.51, improving to R² = 0.62 with newly available structures)" (dms-3d-features/abstract_intro_discussion_rewrite.md). Write "R² = 0.51," never "the R² was 0.51."
- **Specificity is the voice, not a garnish (his #1 correction, 2026-08-13 clinic).** Reviewing a clean but general paragraph, his verdict was: "still pretty bad since it doesnt give enough detail to understand, its too general." A sentence that states only the *direction* of an effect is a placeholder, not prose. Every claim carries the quantity actually measured, its number, and its scope: how many constructs, what fraction, which subset. "Reactivity decreases as magnesium increases" is not a finding; "the median [Mg2+]1/2 is 0.84 mM across 1,284 constructs, and 12% titrate above twice that" is. **Name the measured quantity, not the derived one** (he changed "reactivity" to "mutation fraction" in the same edit). If you do not have the number, **write the literal placeholder `XXX`** and move on; do not paper over the gap with a general statement. This is his own convention, used in the clinic ("XXX passed this analysis filter") and throughout his drafts ("XXXXXX" in the TMO abstract, "[X]%" and "Supplemental Figure SXX" in the dms-3d-features rewrites).
- **Lead with purpose. This is the single most important rule in this file (confirmed twice on 2026-08-13: by a minimal-pair test he chose blind, and by 2,892 author-verified tracked edits, where demanding the missing *why* is by a wide margin his most frequent intervention).** His own margin notes: *"XXX why the purine riboswitch?? XXX"*, *"XXX you need to explain why you are doing this, its not clear why mg2+ XXX"*, *"XXX WHY ARE WE BAD AT PREDICTING MULTISTATE RNAS???? XXX This is critical to understand why you are proposing this."* Given two paragraphs with identical content and identical numbers, differing only in their first and last sentence, he chose the one with a purpose opener and an interpretive landing: *"version 2 is better as it explains why we did things."* A results paragraph that reports what was measured without establishing why it was measured is unusable no matter how many numbers it carries. Open with the goal: "To quantify per-nucleotide differences between the two reagents, we defined ΔlnMF = ..." (dms-3d-features); "To determine whether X determines Y, we measured ..." Then close on what the result means, not on a mechanism aside.
  - The *why* may arrive from the preceding paragraph rather than from an explicit opener, in which case a bare method statement is acceptable. Default to the explicit "To [goal], we [action]" form, and use the bare opener only when the motivation has just been established.
- **One interpretive landing per paragraph.** Close on what the data mean, not just what they are: "DMS reactivity thus provides atomic-scale, geometric information for RNA 3D modeling" and "Together, these results establish that DMS reactivity contains predictive 3D structural information accessible through geometric, rather than thermodynamic, modeling" (dms-3d-features/abstract_intro_discussion_rewrite.md).

## Argument order (from 552 tracked edits on student drafts, 2026-08-13)
- **Nothing arrives unprepared.** His recurring complaint is *"this comes out of no where"*, always followed by what should have come first: *"you need to talk about the sequence conservation first"*. Before a claim, supply the concept it depends on.
- **Gloss every term on first use.** *"XXX you need to say what a pseudoknot is! XXX"*
- **Connect consecutive paragraphs.** *"Need a connecting thought to next paragraph"*
- **`XXX ... XXX` is his marker** for both a missing number and an inline note. Use it rather than writing around a gap.

## Sentence structure
**Prefer short, simple sentences** (see the panel: his stated preference overrides
the measured medians). The recurring shape is a claim, a specification, then a
brief mechanistic gloss, but it does not need heavy punctuation to carry it.
- **Colon for a definition or expansion: allowed, not encouraged.** It does the work of "namely", as in "These methods operate at the secondary-structure level: per-residue reactivity is converted to a thermodynamic bonus or penalty that biases whether a nucleotide is assigned to a WC base pair" (dms-3d-features/abstract_intro_discussion_rewrite.md). He now prefers to avoid it where a comma or a new sentence will serve.
- **In-sentence contrast: mirror two conditions in one sentence rather than splitting them.** "Non-WC bases with WC-like protection exhibit increased hydrogen bonding and reduced solvent accessibility, whereas reactive WC pairs flank junctions and correlate with weaker stacking and greater junction dynamics" (dms-3d-features/abstract_intro_discussion_rewrite.md).
  - **Correction 2026-08-13: "whereas" is NOT a signature tic.** It occurs exactly **once** in 39,000 words of his own-hand prose (the sentence above), against 22x that rate in his student's draft. The previous version of this file built a bolded rule out of that single instance. The *move* (mirrored contrast in one sentence) is his; the specific connective is not.
  - **Prefer to restructure rather than reach for "however".** Per 1,000 words, his rate first: *however* 0.18 vs 1.14, *while* 0.54 vs 1.52. He uses both, roughly 3-6x less often than his student. (An earlier version cited a tracked-change substitution "However" → "In contrast" as further support; that edit turned out to be a collaborator's, not his, and the claim now rests on the frequency comparison alone.) These are dispreferences, not bans.
  - **A correction worth remembering:** an earlier pass of this analysis reported "however" as having zero occurrences in his corpus and made it a hard rule. That count was case-sensitive and missed every sentence-initial "However". Two rules in this file's history have now come from undercounting; verify case-insensitively before asserting a zero.
- **Semicolons to chain quantitative facts that are one observation: allowed, but he prefers to avoid them.** Two short sentences usually read better.
- **Enumerated spine for multi-step framing:** "First," "Second," "Third," "Fourth" in introductions; "Together," "Finally," "Critically" for interpretive landings. Avoid "Furthermore," "Moreover," "Indeed," "It should be noted that."

## Paragraph openers (results / analysis)
Open with the action, not a transition. Rotate these; do not lead every paragraph the same way:
- "To test whether...", "We reasoned that...", "We computed / measured / compared..."
- **"We asked whether...": ALLOW SPARINGLY.** Acceptable to frame a genuine open question, not to narrate routine computation. In the corpus it appears about twice per 16,000 words: "Fourth, we asked whether these relationships can be used, not merely observed, to constrain RNA 3D modeling..." (dms-3d-features/abstract_intro_discussion_rewrite.md). Default to "we computed / tested / measured"; reach for "we asked whether" only for a real question.

## Vocabulary and tics (recurrent, his)
*orthogonal* ("orthogonal to the per-residue pairing bias"), *complementary, not redundant* / *not competitive*, *recover / recovery* (the model gets the right answer), *encode* ("the geometric information encoded in DMS reactivity"), *by construction*, *systematic / systematically*, *quantify / quantitative*, *predictive / predictive capability*, *held-out* (preferred over "blind"). Attested in dms-3d-features/* and the MIRA renewal. **Dropped 2026-08-13:** *fingerprint*, *anchor*, and *discriminate* were attested only in the student-written TMO draft and are not established as his.

## Reporting numbers
- **Mean ± SD** for distributions; **"from-to" or "n of N"** for changes, not bare ratios: "0% to 99.5% native cWW recovery"; "brings 7 of 37 previously-failing motifs above 80% native LW-type recovery" (dms-3d-features). **"fold"** for ratios.
- **Absolute change with a percentage-point label** when "%" is ambiguous: prefer "from X% to Y% (Δ = 11 percentage points)" over "raised by 11%."
- Round R² to two decimals; percentages to one decimal when small (7.0%, 12.0%), whole percent when coarse (80%, 99.5%). Do not invent precision.

## Banned (do not produce)
- **Dashes.** No em-dashes (the U+2014 glyph) and no spaced-hyphen connectors. Use a colon (definition/expansion), a comma or parenthesis (aside), a semicolon (joined clauses), or a new sentence. En-dashes (U+2013) are fine in compound terms (Watson–Crick, Leontis–Westhof); ordinary compound hyphens (high-throughput) are fine. His recent clean prose has zero em-dashes; older drafts used them and are being corrected.
- **AI-tells, hard (never produce):** delve, leverage, "it's worth noting"/"it is worth noting" (he deletes the whole sentence, even when it carries real content), "in conclusion," "plays a crucial role."
- **AI-tells, soft (prefer to cut, but not disqualifying):** "moreover," "furthermore," "notably," "interestingly." Two independent lines of evidence downgraded these on 2026-08-13: they occur in his own hand (furthermore 3x, notably 4x across the corpus), and all three survived in the one clinic paragraph he graded "better." Cut them when they are filler; do not treat their presence as proof a draft is machine-written. `bin/voice-lint.py` reports them as WARN, not FAIL.
- **Editorializing adverbs:** "notably," "interestingly," "remarkably," "surprisingly." He removes these from his own drafts. "most strikingly" and "Critically" are allowed, but only when the numbers warrant and only at an interpretive landing.
- **Hedging stacks** ("may possibly suggest"); **passive/nominalizations** ("it was observed that," "the observation of"); **vague intensifiers** ("very," "significant"/"robust" without a number); **defensive phrasing** (let the numbers argue).
- **"observed"** as a reporting verb: dispreferred, not banned. His student uses it at 16x his rate (2.47 vs 0.15 per 1,000 words). Report what happened, not that you observed it.
- **Relative clauses where a participle would serve.** He converts them in his own revisions ("that consist" → "consisting"; "which can be found" → "available"), and *which* runs at 1.13 per 1,000 words in his prose against 2.85 in his student's. Two independent methods agree, which makes this one of the best-supported rules in this file.
- **Nominalizations.** "Utilization:" → "Use." in his own tracked edits, four times over. Prefer the short verb-derived word to the abstract noun.
- **Generic references to named things.** "some constructs", "the mutant", "several reagents" where a name exists: *"XXX we need to define names for each of these mutants XXX"*, *"XXX need to say what each mutation is that is dicussed like A91G etc XXX"*.

## Measured against his student's prose (genre-controlled, 2026-08-13)
Comparing 39,000 words of his own writing with a student draft from the same lab
on the same subject isolates voice from topic. Per 1,000 words, his rate first
(case-insensitive):
- *however* 0.18 vs 1.14 | *whereas* 0.03 vs 0.57 | *observed* 0.15 vs 2.47 | *while* 0.54 vs 1.52
- *is* 3.73 vs 8.55 and *which* 1.13 vs 2.85: he writes with **fewer copulas and fewer relative clauses**. Prefer a strong verb over "is ... which ...".
- *we* 5.48 vs 3.61: more first-person agency.
**Sentence length does NOT separate them** (his median 22-25, the student's 26). Cadence bands are a weak voice signal and should be treated as advisory; the reliable signals are the *why*, the specificity, and the lexical choices above.

## Exemplar bank (imitate the cadence and punctuation, never the RNA subject matter)
1. **Claim, number-led, short:** "DMS reactivity spans four orders of magnitude with ~10% overlap between WC and non-WC nucleotides." (dms-3d-features/abstract_intro_discussion_rewrite.md)
2. **Colon expansion (gloss the term, then the consequence):** "These methods operate at the secondary-structure level: per-residue reactivity is converted to a thermodynamic bonus or penalty that biases whether a nucleotide is assigned to a WC base pair" (dms-3d-features/abstract_intro_discussion_rewrite.md).
3. **Gap statement (names what cannot be done, and why):** "They are highly effective for secondary-structure determination, but they cannot, by construction, encode information about non-canonical base-pair geometry, because non-canonical pairs are absent from the secondary-structure model itself." (dms-3d-features).
4. **Enumerated study aim:** "Fourth, we asked whether these relationships can be used, not merely observed, to constrain RNA 3D modeling at a level inaccessible to existing pseudo-energy methods." (dms-3d-features).
5. **Closing significance, understated, comparative:** "Together, these results establish that DMS reactivity contains predictive 3D structural information accessible through geometric, rather than thermodynamic, modeling." (dms-3d-features).

**Items 2-5 were replaced 2026-08-13**; the originals were quoted from the
student-written TMO draft. Every quote above is now from the dms-3d-features
rewrites.

## Deprecation log (drift over time)
- **Corpus expanded and provenance-checked 2026-08-13.** Now ~39,000 words of confirmed own-hand prose: RNAMake 2019, RMDB 2017, the dms-3d-features rewrites, the 2026 R01 draft, MIRA Sections A and B, and NSF/NIH progress reports. Bands by register: papers median ~25, grants median ~20, progress reports median ~16. **The registers differ enough that a single band is misleading; lint with `--genre`.**
- **His 2017-2019 prose violates several current rules.** RNAMake 2019 contains "we hope" and "interestingly"; the 2026 R01 uses "leverage" in its ordinary technical sense. Where old practice and his stated 2026 preference disagree, **the stated preference wins**, and the word stays advisory rather than becoming a hard gate.
- **TMO/DMS draft REMOVED from the corpus 2026-08-13.** `TMO_DMS_manuscript_draft3_JDY.docx` is **student-written** ("my student wrote that, not mine"; "I havent got to that yet" — the `_JDY` suffix does not mean he rewrote it). It had been supplying 64% of the sentences behind the first re-measurement, so every band derived from it was contaminated. Panel re-measured without it: papers median 28 (was 27), grants median 22, pooled 25 (was 26). All exemplars sourced to `dms_vs_tmo` were deleted from `EXEMPLARS.md`, `papers.md`, and the exemplar bank below. **Anything still citing dms_vs_tmo is contaminated and should be removed on sight.**
- **Panel numbers corrected 2026-08-13.** The n = 474 panel (mean 21.7, median 19, 37% >=25 words) pooled methods text, figure legends, and editorial notes with prose, which pulled the median down by roughly a quarter. Re-measured over prose only: median 26, 55% >=25 words. Drafts written to the old panel came out systematically too short, which is the most likely single cause of "the sentence structure is all off."
- **Em-dash evidence claim corrected 2026-08-13.** The guide asserted zero em-dashes in recent clean prose; that was true only of the TMO draft, which is not his. His actual prose contains them: 19 in the dms-3d-features rewrites, 5 in MIRA Section A. The ban stands as his stated preference; the supporting claim was wrong.
- **"Staccato / short sentences" rule: REMOVED 2026-06-25.** Contradicted by the panel; re-confirmed and strengthened by the 2026-08-13 re-measurement.
- **"We asked" outright ban: REMOVED 2026-06-25, now ALLOW SPARINGLY.** His 2025 drafts use it for genuine questions.
- **Em-dashes: DEPRECATED.** Heavy in pre-2025 drafts, zero in recent clean prose; override stands.
- **"novel": dropped.** Present in 2019 prose ("a novel approach"), absent from 2025-26; do not use.

## Update procedure
When a new own-hand draft lands: add it to the corpus, recompute the stylometric
panel with `bin/voice-lint.py` over **prose only** (exclude methods, figure
legends, references, and editorial notes, which skew the sentence-length
distribution downward), add any new verbatim paragraphs to `EXEMPLARS.md` under
the right rhetorical job, add any new never-say items to `REJECTIONS.md`,
re-date this file, and log any changed rule above. Source only own-hand text;
exclude AI-drafted or heavily co-authored sections. Grant coverage rests on a
single MIRA renewal, so grant bands are the least certain numbers here and
should be re-measured as soon as new own-hand grant prose exists.

## Evidence base (allowed own-hand sources)
2025-26, his hand: dms-3d-features/{abstract_intro_discussion_rewrite, ga_modeling_section_rewrite, response_letter_redraft_4_28_26}.md; 2026 MIRA renewal Section A.
**EXCLUDED, student-written:** dms_vs_tmo/TMO_DMS_manuscript_draft3_JDY.docx (removed 2026-08-13; see deprecation log).
**Unverified:** the MIRA files have an `_ACB_` suffix, suggesting another hand touched them; confirm before treating grant bands as solid. Older first-author papers (2019 PNAS tecto, 2019 Nature Nano RNAMake, 2017 RMDB) are multi-author and used for corroboration only, not as primary voice sources. The current 2025-atp-ttr-switch paper is EXCLUDED (heavily AI-drafted).
