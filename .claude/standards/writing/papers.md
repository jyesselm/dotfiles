# Writing voice: papers / manuscripts

Apply `@~/.claude/standards/writing/CORE.md`. Paper-specific moves below; quotes
are from his own-hand 2025-26 drafts.

## Abstract: context → gap → "To address this, we…" → understated utility close
Open with the established frame, then the gap in the next sentence:
> "Dimethyl sulfate (DMS) chemical mapping probes RNA structure, where low reactivity is generally interpreted as Watson–Crick (WC) base pairs and high reactivity as unpaired nucleotides. ... The frequency of these outliers and the recurring 3D features that produce them remain incompletely characterized." (dms-3d-features/abstract_intro_discussion_rewrite.md)

Announce the contribution with the action and the scale:
> "To address this, we systematically analyzed DMS reactivity across a library of 7,500 RNA constructs containing two-way junctions with known 3D structures." (same)

Close on concrete utility, not hype:
> "DMS reactivity thus provides atomic-scale, geometric information for RNA 3D modeling." (same)

## Introduction openings: give background first, climb to the gap
**Confirmed 2026-08-14 by a blind generation test.** Asked to write the opening of
an introduction, he produced a seven-sentence ladder before naming the gap:

> Structured RNA plays a critical role throughout the cell, from translating proteins, regulating genes to maturing mRNA. To accomplish these tasks, RNAs must fold into complex 3D structures that must respond to cellular stimuli. RNA folds hierarchically, first forming secondary structure followed by long-range interactions known as tertiary contacts. These contacts lock an RNA into its functional form and are critical to function. While we have a reasonable model for predicting the secondary structure of RNAs no such model exists for tertiary contacts. To build such a model we must generate a large amount of experimental data to learn which sequences allow for the formation of a tertiary contact and which don't. DMS chemical mapping offers a potential new avenue to do this allowing the multiplexing of up to 100,000s of unique RNA sequences.

The ladder: biological importance → what folding must achieve → the folding
hierarchy → what the contacts do → **the missing model** → what building one
requires → the method that makes it possible. His own words: *"you need to give
background when its an intro."*

The generated attempt reached the gap in sentence two and was identifiably wrong
for it. **Do not open an introduction on the gap.** This is the same fault he
writes in students' margins: *"this comes out of no where."*

## Specificity is section-dependent (correction, 2026-08-14)
His "too general" verdicts were all delivered on **results paragraphs and grant
aims**. Applying that rule to an introduction opening is a mistake. In the blind
test **his opening was less specific than the generated one**: he wrote "a
reasonable model", "tertiary contacts", "DMS chemical mapping", where the
generated version named Turner, kissing loops, pseudoknots, A-minor motifs and
optical melting.

- **Introductions** open broad and earn specificity as they narrow. Named methods and parameter sets belong later in the intro, not in the first two sentences.
- **Results and aims** demand the number, the n, the error, and the named construct immediately.

## Results
- Open with purpose and action ("To [goal], we [action]…"); one interpretive landing per paragraph (CORE).
- Report finding + why it matters, number inline, "from-to" or "n of N" (CORE numbers rules).

## Significance: understated, comparative, utility-framed
Frame impact as what becomes possible or what it beats, not as a breakthrough boast:
> "Together, these results establish that DMS reactivity contains predictive 3D structural information accessible through geometric, rather than thermodynamic, modeling." (dms-3d-features/abstract_intro_discussion_rewrite.md)

Save the bold, field-level vision for grants (see grants.md).

**Confirmed 2026-08-13.** He rejected a dense, numerically specific close as "way
too boastful", and named the acceptable alternative himself: "we want to be much
more measured in the discussion, we can say we are the first or something." So a
priority claim is fine, stated flatly ("the first X"), and the hype around it is
not: no *groundbreaking*, *unprecedented*, *major advance*, *exciting new
possibilities*, *undoubtedly transform*, and no appeals to "the RNA community" or
"broad interest". Predicting field-level transformation is a grant move and a
paper violation; hype adjectives are a violation in both. `bin/voice-lint.py`
enforces this.

## Methods
Active and terse; include only parameters needed to reproduce. His Methods are
dense procedural prose with reagent/catalog specifics inline.
