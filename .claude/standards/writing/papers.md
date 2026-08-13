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
