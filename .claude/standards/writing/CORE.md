# Writing voice: core (all genres)

Universal rules for writing in Yesselman's voice. Genre files (papers, grants,
reviewer-responses, short-form) `@import` this and add only their delta.

Rebuilt 2026-06-25 from his own-hand 2025-26 corpus (see "Evidence base" at the
end). Every load-bearing rule below carries a verbatim quote from that corpus,
with the source file in parentheses. When in doubt, imitate the quoted sentence,
do not paraphrase the rule.

## The voice in three words
Clear. Concise. Direct. High-density, unornamented prose that lands a quantitative
claim, then interprets it in one short follow-up.

## Stylometric panel (measured over the 2025-26 own-hand corpus, n = 474 sentences)
Use this as a self-check; a drafted paragraph should land inside these bands.
- **Sentence length: mean 21.7 words, median 19, 10th-90th percentile 7-40.** 37% of sentences are >=25 words, 10% are >=40. He is NOT staccato; he writes medium-to-long, well-articulated sentences with a short interpretive sentence mixed in.
- **Colon ~4-10 per 1,000 words; semicolon ~3-8 per 1,000.** Both are heavy, load-bearing tics (definition/expansion and fact-chaining).
- **Em-dash count = 0** in recent clean prose (MIRA grant, TMO/DMS draft). See the no-dash override below.

## Principles
- **Active voice, first-person plural.** "We" carries every claim; "I" is absent from papers. "we systematically analyzed DMS reactivity across a library of 7,500 RNA constructs" (dms-3d-features/abstract_intro_discussion_rewrite.md).
- **Commit; police over-hedging.** Verbs are "we show," "we demonstrate," "we recover," not "we suggest" or "it appears." At most one qualifier, only where the data is genuinely partial. He actively removes surviving hedges from his own drafts.
- **Concrete, numbers inline with `=`.** "(R² = 0.51, improving to R² = 0.62 with newly available structures)" (dms-3d-features/abstract_intro_discussion_rewrite.md). Write "R² = 0.51," never "the R² was 0.51."
- **Lead with purpose.** Open explanatory paragraphs with the goal: "To quantify per-nucleotide differences between the two reagents, we defined ΔlnMF = ..." (dms-3d-features).
- **One interpretive landing per paragraph.** Close on what the data mean, not just what they are: "DMS reactivity thus provides atomic-scale, geometric information for RNA 3D modeling" and "Together, these results establish that DMS reactivity contains predictive 3D structural information accessible through geometric, rather than thermodynamic, modeling" (dms-3d-features/abstract_intro_discussion_rewrite.md).

## Sentence structure (the heart of the voice)
Long-ish, well-articulated sentences, one or two structural marks (colon or
semicolon) rather than commas alone. The recurring shape is a claim, a punctuated
specification, then a brief mechanistic gloss.
- **Colon to introduce a definition or expansion** (does the work of "namely"): "These methods operate at the secondary-structure level: per-residue reactivity is converted to a thermodynamic bonus or penalty that biases whether a nucleotide is assigned to a WC base pair" (dms-3d-features/abstract_intro_discussion_rewrite.md).
- **"whereas" for in-sentence contrast** (mirror two conditions, do not split into two sentences): "Non-WC bases with WC-like protection exhibit increased hydrogen bonding and reduced solvent accessibility, whereas reactive WC pairs flank junctions and correlate with weaker stacking and greater junction dynamics" (dms-3d-features/abstract_intro_discussion_rewrite.md).
- **Semicolons to chain quantitative facts that are one observation** (see exemplar bank).
- **Enumerated spine for multi-step framing:** "First," "Second," "Third," "Fourth" in introductions; "Together," "Finally," "Critically" for interpretive landings. Avoid "Furthermore," "Moreover," "Indeed," "It should be noted that."

## Paragraph openers (results / analysis)
Open with the action, not a transition. Rotate these; do not lead every paragraph the same way:
- "We previously showed that DMS reactivity carries information beyond secondary structure..." (dms_vs_tmo/TMO_DMS_manuscript_draft3_JDY.docx)
- "To test whether...", "We reasoned that...", "We computed / measured / compared..."
- **"We asked whether...": ALLOW SPARINGLY.** Acceptable to frame a genuine open question, not to narrate routine computation. In the corpus it appears about twice per 16,000 words: "Fourth, we asked whether these relationships can be used, not merely observed, to constrain RNA 3D modeling..." (dms-3d-features/abstract_intro_discussion_rewrite.md). Default to "we computed / tested / measured"; reach for "we asked whether" only for a real question.

## Vocabulary and tics (recurrent, his)
*orthogonal* ("orthogonal to the per-residue pairing bias"), *complementary, not redundant* / *not competitive*, *recover / recovery* (the model gets the right answer), *encode* ("the geometric information encoded in DMS reactivity"), *by construction*, *systematic / systematically*, *quantify / quantitative*, *predictive / predictive capability*, *fingerprint*, *anchor*, *discriminate*, *held-out* (preferred over "blind"). All attested in dms-3d-features/* and dms_vs_tmo/*.

## Reporting numbers
- **Mean ± SD** for distributions; **"from-to" or "n of N"** for changes, not bare ratios: "0% to 99.5% native cWW recovery"; "brings 7 of 37 previously-failing motifs above 80% native LW-type recovery" (dms-3d-features). **"fold"** for ratios.
- **Absolute change with a percentage-point label** when "%" is ambiguous: prefer "from X% to Y% (Δ = 11 percentage points)" over "raised by 11%."
- Round R² to two decimals; percentages to one decimal when small (7.0%, 12.0%), whole percent when coarse (80%, 99.5%). Do not invent precision.

## Banned (do not produce)
- **Dashes.** No em-dashes (the U+2014 glyph) and no spaced-hyphen connectors. Use a colon (definition/expansion), a comma or parenthesis (aside), a semicolon (joined clauses), or a new sentence. En-dashes (U+2013) are fine in compound terms (Watson–Crick, Leontis–Westhof); ordinary compound hyphens (high-throughput) are fine. His recent clean prose has zero em-dashes; older drafts used them and are being corrected.
- **AI-tells:** delve, leverage, "moreover"/"furthermore" as filler, "it's worth noting," "in conclusion," "plays a crucial role."
- **Editorializing adverbs:** "notably," "interestingly," "remarkably," "surprisingly." He removes these from his own drafts. "most strikingly" and "Critically" are allowed, but only when the numbers warrant and only at an interpretive landing.
- **Hedging stacks** ("may possibly suggest"); **passive/nominalizations** ("it was observed that," "the observation of"); **vague intensifiers** ("very," "significant"/"robust" without a number); **defensive phrasing** (let the numbers argue).

## Exemplar bank (imitate the cadence and punctuation, never the RNA subject matter)
1. **Claim, number-led, short:** "DMS reactivity spans four orders of magnitude with ~10% overlap between WC and non-WC nucleotides." (dms-3d-features/abstract_intro_discussion_rewrite.md)
2. **Colon expansion (gloss the term inline, then the consequence):** "Dimethyl Sulfate (DMS) methylates the N1 of adenine and the N3 of cytosine, the same atoms used in WC base pairing, and therefore reports specifically on whether the WC edge of A or C is engaged" (dms_vs_tmo/TMO_DMS_manuscript_draft3_JDY.docx).
3. **Gap statement (names what cannot be done, and why):** "Yet because DMS is the only probe applied at this scale, it is not possible to separate DMS-specific features from features that reflect generic WC-edge accessibility using DMS data alone." (dms_vs_tmo).
4. **Study-aims sentence, enumerated:** "In this study, we directly address (i) whether TMO reports the same per-nucleotide structural information as DMS across a structurally diverse RNA library, and (ii) where the two probes disagree, are those disagreements reproducible features of specific structural contexts?" (dms_vs_tmo).
5. **Closing significance, understated, comparative:** "These analyses establish that differential chemical mapping with TMO and DMS is a scalable strategy for identifying 3D structural features, outperforming both probes alone." (dms_vs_tmo).

## Deprecation log (drift over time)
- **"Staccato / short sentences" rule: REMOVED 2026-06-25.** Contradicted by the panel (median 19 words, 37% >=25). Was an over-correction in the 2026-06-01 guide.
- **"We asked" outright ban: REMOVED 2026-06-25, now ALLOW SPARINGLY.** His 2025 drafts use it for genuine questions.
- **Em-dashes: DEPRECATED.** Heavy in pre-2025 drafts, zero in recent clean prose; override stands.
- **"novel": dropped.** Present in 2019 prose ("a novel approach"), absent from 2025-26; do not use.

## Update procedure
When a new own-hand draft lands: add it to the corpus, recompute the stylometric
panel (a sentence-length and punctuation pass), add any new verbatim quotes here,
re-date this file, and log any changed rule above. Source only own-hand text;
exclude AI-drafted or heavily co-authored sections.

## Evidence base (allowed own-hand sources)
2025-26, his hand: dms-3d-features/{abstract_intro_discussion_rewrite, ga_modeling_section_rewrite, response_letter_redraft_4_28_26}.md; dms_vs_tmo/TMO_DMS_manuscript_draft3_JDY.docx; 2026 MIRA renewal draft. Older first-author papers (2019 PNAS tecto, 2019 Nature Nano RNAMake, 2017 RMDB) are multi-author and used for corroboration only, not as primary voice sources. The current 2025-atp-ttr-switch paper is EXCLUDED (heavily AI-drafted).
