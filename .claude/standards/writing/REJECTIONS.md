# Writing voice: rejection lexicon (never-say → say-instead)

## Machine-read block
`bin/voice-lint.py` reads **only** this block, and only for context-free words
that are never right. Contextual substitutions (compared → relative, showed →
the specific verb) live in the prose below and are applied by the writer, not the
gate: they cannot be checked mechanically without failing his own papers.

<!-- LINT:HARD -->
- groundbreaking
- unprecedented
- undoubtedly
- delve
- delves
- delving
<!-- /LINT:HARD -->


Data file: words and moves he rejects, each backed by evidence. Rules live ONLY
in `CORE.md`; this file carries data. Sources tagged: `human-edit` (he edited it
out of a draft), `ab-choice` (he flagged it in a forced-choice calibration),
`machine-tell` (a blind discriminator cited it when spotting generated text),
`corpus-drift` (present in old prose, absent from 2025-26).

Format: one entry per line: `rejected → replacement | tag | evidence`

## words
- novel → new, first, previously uncharacterized → | corpus-drift | in 2019 prose, absent 2025-26 (CORE.md deprecation log)
- delve / leverage / robust (unquantified) / significant (no number) → name the actual quantity or cut | machine-tell | CORE.md banned list, seeded

## moves
- em-dash asides → colon (expansion), parentheses (aside), semicolon (joined clauses) | human-edit | he is actively correcting these out of older drafts (CORE.md)
- "which is significant as it's a…" (self-justifying parenthetical) → let the numbers carry it | human-edit | d3f rewrite note 7: "Reads defensive. Drop."
- "rarely has any significant negative effect" (soft failure gloss) → name the failure conditions explicitly | human-edit | d3f rewrite note 5: "too soft"
- "we also did this" framing for the strongest result → name it a blind test / held-out validation explicitly | human-edit | d3f rewrite note 6

## clinic entries (2026-08-13, item 1A)
- our [X] approach → [X] | human-edit | "using our chemical probing approach" → "using chemical probing"; he drops the possessive and the word "approach"
- The data show interesting patterns. → (delete) | human-edit | cut wholesale; a sentence that announces a result without stating it is dead weight
- interesting → (delete, or name the specific quantity) | human-edit | same edit as above
- reactivity (for the raw measurement) → mutation fraction | human-edit | "Reactivity decreases as magnesium increases" → "We observed the mutation fraction decrease as magnesium increased"; he names the quantity actually measured, not the derived one
- bare direction-of-effect statement → the quantity + its number + the scope | human-edit | his verdict on the whole edited paragraph: "still pretty bad since it doesnt give enough detail to understand, its too general"

### cadence pair (1A)
- before: "The data show interesting patterns. Reactivity decreases as magnesium increases."
- after: "We observed the mutation fraction decrease as magnesium increased."
- what he did: deleted the vacuous lead sentence, collapsed two sentences into one, replaced the derived quantity with the measured one, and shifted to active past tense.

## clinic entries (2026-08-13, item 1B)
- delves into → investigated | human-edit | direct confirmation of the CORE.md ban on "delve"
- could potentially suggest → suggest | human-edit | he strips the hedge stack down to the bare verb, keeping the claim
- bare direction-of-effect statement → the quantity + its number + the scope | human-edit | verdict on the whole paragraph, repeated from 1A: "its just too general"

**Caveat on both 1A and 1B:** he made two or three surgical word fixes, then
abandoned the paragraph as unsalvageable at the content level. Surviving text is
NOT endorsed. "Notably", "plays a crucial role", "In conclusion", "leveraged",
"novel", "robust", "Moreover", and "we believe" all survive in his versions only
because he stopped polishing once he saw the real problem. Do not read survival
as approval.

## TRACKED-CHANGE CORPUS (2026-08-13): 2,892 edit-runs, author-filtered to him
Extracted from every `.docx` on disk (2,206 scanned) and filtered by the
`w:author` attribute so that only revisions attributed to Yesselman are counted:
2,892 edit-runs across 138 files. This is the largest and most reliable evidence
in this file, because it records what he actually changes in real work.

### His dominant demand, by a wide margin: WHY
Verbatim margin comments, **verified as his by author attribution** (from the
atp-ttr-switch drafts and `RUI_written_draft_Danushi_JDY.docx`):
> "XXX why the purine riboswitch?? XXX"
> "XXX you need to explain why you are doing this, its not clear why mg2+ XXX"
> "XXX I didn't finish rewriting this but you need to put what the mutatiosn are and why do we think this is happening! XXX"
> "XXX why do we need to build our own? XXX"
> "XXX WHY ARE WE BAD AT PREDICTING MULTISTATE RNAS???? XXX This is critical to understand why you are proposing this."

### Name every entity; do not refer to things generically
> "XXX we need to define names for each of these mutants XXX"
> "XXX need to say what each mutation is that is dicussed like A91G etc XXX"
> "XXX similar to previous section there needs to be mutant names for each mutant or its really [confusing] XXX"

This is the concrete form his "too general" verdict takes in real work: a
construct, mutant, or condition referred to as "some constructs" or "the mutant"
must be given its actual name.

This independently confirms the minimal-pair result ("version 2 is better as it
explains why we did things"). Motivation is not a stylistic nicety in his voice;
it is the thing he most often adds when fixing someone else's prose. **Every
section must establish why before it reports what.**

### "This comes out of nowhere": establish the prerequisite first
> "This feels like it comes out of no where"
> "XXX this comes out of no where you need to talk about the sequence conservation first, other functional RNAs use the primary sequence and thus have no interesting structure XXX"

A claim that depends on a concept must be preceded by that concept. Order the
argument so nothing arrives unprepared.

### Gloss every term on first use
> "XXX you need to say what a pseudoknot is! XXX"

### Connect paragraphs
> "Need a connecting thought to next paragraph"

### Specifics, again (confirms the clinic's "too general" verdict at scale)
> "XXX give more details are you making a library are you systematically mutating things etc XXX"

### `XXX ... XXX` is his inline comment delimiter as well as a number placeholder
**69 insertions of `XXX` in author-filtered edits**, his strongest single lexical
habit. He uses it both for a missing value ("XXX passed this analysis filter")
and to wrap a note ("XXX add our new results XXX"). Use it for both; never fudge
around a gap.

### RETRACTED 2026-08-13 (same session): a lexical list that was not his
An earlier pass mined `~/Downloads/*JDY*.docx` without checking the `w:author`
attribute on each revision. The largest file, `Pepper-sequence_ms_15-JDY.docx`,
carries 987 revisions by **Catherine Eichhorn** and 3 by him, so 314 of the 552
"his" edits were a collaborator's. The following rules came from that
contamination and are **withdrawn**: compared to → relative to; showed → the
specific verb; While/However → In contrast; have/had → are; interactions →
hydrogen bonds; numerous → multiple classes of; impact → influence; permits → can
form; The most X → Constructs with the greatest X; and the aggregate add/remove
counts built on the same set.

**Method note for anyone extending this file: filter tracked changes by
`w:author` before drawing any conclusion.** Re-extracted with that filter, the
corpus is 2,892 edit-runs genuinely his across 138 files.

### Sentence length: STATED PREFERENCE OVERRIDES MEASURED CORPUS (2026-08-13)
> "you also have sentences that are too long, definitely want shorter simpler
> sentences, it cant be all the time but should prefer"

He said this of a paragraph whose median was 24 words with a longest of 38, i.e.
**already at his own measured corpus median of 25 for papers**. So he is asking
for prose shorter than his historical writing. Treat the panel as a description
of what he has written, and this line as what he wants written.

**Resolution: prefer short and simple; reach for a long sentence deliberately,
not by default.** Long sentences remain correct for subordinating interpretation
(see the cadence pairs, where he merged interpretive sentences), and runs of
parallel measurements stay clipped. What he does not want is uniformly long prose.

**Honest note on this file's history.** The 2026-06-01 guide said "short
sentences". A measurement pass on 2026-06-25 removed that rule as contradicted by
the corpus, and a second pass on 2026-08-13 strengthened the reversal. His stated
preference here indicates the original rule captured his intent, and the
measurements captured only his past practice. **Where the two disagree, his
stated preference wins.** The `bin/voice-lint.py` gate now fails long prose and
only warns on short prose, rather than treating both as equal violations.

### State current practice BEFORE stating its failure (2026-08-13, his rewrite)
Rewriting an opening paragraph of his own grant, the sentence he **added** was:
> "Commonly, predicted secondary-structure stability is utilized to assess whether
> a structure might be functional."

The generated version went straight from "researchers cannot establish whether
RNAs are functional" to "MFE cannot distinguish them", with no statement of what
the field currently does. **Name the standard approach, then say what it fails
at.** This is the same demand as his margin note *"this comes out of no where,
you need to talk about the sequence conservation first"*.

### Cut qualifiers that add no information
From the same rewrite, all deleted without replacement:
- "High-throughput methods **now** identify..." → the *now* went
- "...identify **well-structured** candidate non-coding RNAs" → the *well-structured* went
- "...whether **any of them** is functional" → "whether **they are** functional"
- **Structured RNAs → Non-coding RNAs.** Use the standard name of the class, not a descriptive substitute.

### Compress: he cut six sentences to four
His rewrite merged two sentences into one ("a functional structure cannot be
distinguished from random or shuffled sequences by predicted global MFE",
covering both the mechanism and the shuffled-sequence evidence) and deleted three
more. **When two sentences state a claim and its evidence, try them as one.**

*Observation, not a rule:* his draft uses "it has been demonstrated that", which
has **zero occurrences** in his finished prose. Treat it as a drafting
construction, not as a target to imitate.

### Write sentences OF the science, not ABOUT the science
The single most repeated failure across the 2026-08-13 review. Each of these was
rejected, and they share one fault: the sentence comments on the measurement
instead of stating the physical fact.
- "we measured each contribution directly **rather than inferring it from secondary structure prediction**" | human-edit | *"no one would say that"*. A defensive contrast against an alternative nobody proposed. State what was done; do not argue with a hypothetical.
- "Magnesium titration **is the readout because** the tertiary contact forms only above a threshold" | human-edit | *"this is also said in a strange way"*. **The fault is the framing "X is the readout", not the word "because"**, which he uses 18 times (0.63 per 1,000 words), frequently leading a sentence: *"Because Rosetta already contains this underlying functionality, this is primarily..."*. State the physical fact and let it supply the rationale.
- "Interpreting a single reactivity measurement as evidence of base pairing **overstates what the measurement determines**" | human-edit | *"doesnt seem to make sense"*. Say what cannot be concluded.
- "Reactivity **reports the immediate structural neighborhood**" | human-edit | *"odd and not scientific"*.

**Test before writing any sentence: is this a fact about the RNA, or a comment
about my own measurement? If the latter, rewrite it as the former.** The why
still has to be there, but it arrives as physical fact ("the contact forms only
above 0.5 mM magnesium, while the flanking helices stay folded throughout"),
not as methodological justification.

### The WHY has two levels, and the second is the one that gets missed
> "To determine whether the loop sequence or the closing pair contributes more to
> kissing-loop stability, we measured magnesium titrations for 1,284 variants"
> — *"could of been expanded more, why are we doing the titrations"*

A purpose opener that gives the scientific question is only half. He also wants
**why this measurement answers it**: why a magnesium titration rather than
something else. His own margin note on a student draft is the same complaint
word for word: *"XXX you need to explain why you are doing this, its not clear
why mg2+ XXX"*. Two independent instances, so this is a rule, not a mood.

**Write both: why the question matters, and why this measurement is the one that
answers it.**

### "Enough detail" means method, subgroup n, and uncertainty, not just numbers
Of a paragraph containing 1,284 variants, 0.61 kcal/mol, and 1.2 kcal/mol, his
verdict was still *"doesnt give enough details but is generally clear"*. Numbers
alone do not satisfy him. What that paragraph lacked:
- **how** the quantity was obtained (titration range, number of points, fitting model)
- **quality control** (what was discarded and how much survived)
- **the n behind each subgroup**, not just the total
- **uncertainty** on every reported value (± SD)

A number without its n and its error is still a general statement.

### A sentence whose only content is an unknown is an empty sentence
- "Existing measurements cover fewer than XXX contacts in total." | human-edit | *"sentence doesnt make a lot of sense"*. `XXX` is correct for a missing detail inside a sentence that still carries meaning ("XXX passed this analysis filter"). It is wrong when the number **is** the entire claim, which leaves the sentence saying nothing. Supply the number or cut the sentence.

### Non-scientific register: spatial and figurative descriptions
- **"tertiary contacts assemble on top of it" → name the mechanism and the relationship** | human-edit | *"'on top of it' is strange and not scientific"*. His own rewrite: *"RNA folds hierarchically, first forming secondary structure through WC pairing, followed by tertiary contacts that form between secondary structure elements."* Note what he supplies that the original omitted: the **mechanism** (WC pairing) and the **relationship** (between secondary structure elements). A spatial metaphor is standing in for both.

### Do not name a problem when you can state it
- **"the under-determination problem" / "leaves the fold under-determined" → "cannot select the functional fold from the many alternatives that score nearly as well"** | human-edit | he queried the word on sight. **"under-determin" has 0 occurrences** in his 28,599-word corpus; it is a philosophy-of-science import, not RNA vocabulary. His attested word for this family is *ambiguous* (10 uses).
- The term originated in **his own draft**, which is the useful part: a label can look load-bearing while adding nothing the following clause does not already say. Same family as "the first stage / the second stage" (forces the reader to carry a label) and "overstates what the measurement determines" (comments on the claim instead of making it).

**Rule: prefer the plain statement to the named abstraction. If a labelling
sentence is followed by a clause that explains the label, delete the label and
keep the clause.**

### Invented abstract compounds where a named factor belongs
- **"structural neighborhood" → "local geometry", or name the factors** | human-edit | *"'structural neighborhood' is odd and not scientific"*. **"neighborhood" occurs 0 times** in his corpus; his terms are *local geometry* (2) and *structural context* (1). More often he enumerates the physical causes instead of naming a collective: *"variations in solvent accessibility, hydrogen bonding, and local geometry"*. Prefer the enumeration to the abstraction.

### Sentences that are grammatical but hard to parse
Both of his clarity complaints on one paragraph, and what caused them:
- *"this sentence is hard to follow"*, of: "A protected nucleotide indicates only that its Watson-Crick edge **is occupied**, and **occupancy** by a base partner, by a coordinated magnesium ion, and by an adjacent stack **produce** indistinguishable reactivity values." Three faults compound: a word repeated in nominalized form (occupied → occupancy), a triple parallel "by X, by Y, by Z", and a subject separated from its verb by 18 words.
- *"this sentence doesnt seem to make sense"*, of: "Interpreting a single reactivity measurement as evidence of base pairing therefore overstates what the measurement determines." The fault is writing *about* the measurement in the abstract instead of stating the concrete fact. **Say what cannot be concluded, not what an interpretation "overstates".**

**Rule: do not nominalize a word you just used as a verb, do not stack more than
two parallel prepositional phrases, and keep the subject next to its verb.**

### Back-references that force the reader to hold something in memory
- **"the first stage ... the second stage" → repeat the noun** | human-edit | *"first and second stage are not great since it forces the reader to remember"*. Any label that requires the reader to recall an earlier enumeration ("the former", "the latter", "the first case") should be replaced with the thing itself.

### Blind-generation round 3 (2026-08-14): two more, both already gated
- **carries / carry / carrying → containing, or restructure** | human-edit | *"'carries' is not used often"*. Third rejection of this family. Corpus: **carries 0 uses**, the whole family 5, against *containing* 32. **The linter already flagged this and it was sent anyway.**
- **baseline → (drop, or name the quantity)** | human-edit | *"not big on baseline, you should generally not use those words"*. Corpus: 3 uses, 0.10 per 1,000 words. Rare rather than absent, so a dispreference.
- **"sets the baseline"** compounded both faults: *set* as a verb (0 verb uses in the corpus) plus *baseline*.

**Process rule, and the more important finding.** Both words were caught by
`bin/voice-lint.py` before he saw the paragraph, and the draft went out without
the gate being run. In the previous round the generated prose ran at double his
sentence length against a rule already written in `CORE.md`. **Two consecutive
rounds failed on rules the guide already contained.** Run the gate on every
paragraph before showing it; the recurring failure is not missing rules but
unenforced ones.

### The "words that don't fit" mechanism, identified 2026-08-13
Reviewing generated prose that was otherwise correct, his objections were all of
one kind: a **slightly compressed or literary construction where the plain
standard scientific verb belongs**. Each is corpus-verified.
- **X sets Y → X determines Y** | human-edit | *"'sets the magnesium dependence' is odd, I would use determine instead of sets"*. **Every one of the 32 occurrences of set/sets/setting in his 28,599-word corpus is a noun** ("set of motifs", "data set", "set up"). He has never used it as a verb. Also rejected in the same paragraph: "sets a baseline stability".
- **carrying → containing** | human-edit | *"carrying is also odd here"*. Corpus: *containing* 32 uses (1.12 per 1,000 words), *carrying* 2 (0.07). A 16x preference.
- **"variants closing on G-C" → "variants with a G-C closing pair"** | human-edit | *"closing on is strange, maybe like with flanking pair or closing pair"*. Keep the structural element as a **noun phrase** ("closing pair", "flanking pair", both his terms) rather than verbing it.

- **supplies → provides** | human-edit | *"supplies is uncommon wording"*. Corpus: *provide/provides/providing* 32 uses (1.12 per 1,000 words), *supply/supplies* 3 (0.10). A 10x preference.
- **"parameters that carry RNAstructure and ViennaRNA" → "powering algorithms like RNAstructure and ViennaRNA"** | human-edit | *"carry again, this is very odd"*. Second rejection of the carry family in two paragraphs; corpus rate 0.17 per 1,000 words.
- **estimated → computed** | human-edit | his stated preference in this context ("computed rather than measured"). Weak corpus support (*estimated* 4, *computed* 2), recorded as a preference rather than a rule.
- **"rather than" as the predicate of an opening claim** | human-edit | *"rather than is strange"*. **Not a ban:** he uses it 9 times (0.31 per 1,000 words), but as a *contrastive modifier* between two terms, as in "accessible through geometric, rather than thermodynamic, modeling". Keep it inside a phrase; do not build the sentence's main assertion on it.

**The general rule this implies:** when a plain, conventional scientific verb
exists (determine, contain, provide, measure), use it. Do not reach for a
compressed or figurative alternative, however economical: *sets*, *carrying*,
*carry*, *supplies*, *closing on* were all rejected in a single review pass for
exactly this reason. **This is the mechanism behind "uses a lot of words that
don't really fit".**

**Process rule that follows.** Three of these rejections happened while
paraphrasing a claim his own corpus already states. His MIRA reads *"The Turner
nearest-neighbor model provides ~300 free energy parameters that enable reliable
secondary structure prediction, powering algorithms like RNAstructure and
ViennaRNA"*; the generated version said "supplies" and "carry" and was rejected
on both. **If `EXEMPLARS.md` contains a sentence making the same claim, reuse its
verbs verbatim instead of paraphrasing them.**

### Lexical patterns from his OWN edits (author-filtered, n = 2,892 runs)
- **Nominalization → plain word.** "Utilization:" → "Use." (4 occurrences). Prefer the short verb-derived word over the abstract noun.
- **Relative clause → participial phrase.** "that consist" → "consisting"; "which determines / of which contribute" → "determining, contributing"; "which can be found" → "available". **Independently corroborated** by the genre-controlled corpus counts: *which* runs at 1.13 per 1,000 words in his prose against 2.85 in his student's. Two separate methods agree, which makes this one of the better-supported rules in this file.
- **Compression of noun phrases.** "the assembly of motifs together" → "motif assembly".
- **Terminology precision.** "unpaired" → "non-WC" (he replaces the loose descriptor with the defined term).
- Most of his remaining tracked edits are reference and figure-label formatting ("Supplemental 9" → "S9"), not voice.

## clinic entries (2026-08-13, item 2D: hedging stripped from an aim)
His stated rule: **"we really dont want 'hope' or 'believe'"** (said of papers,
applied by him to a grant aim, so it holds for both).
- It is anticipated that this will enable → This will enable | human-edit
- We believe that [X] → [X] | human-edit
- it is hoped that [X] → [X] | human-edit
- a technique known as [X] → a [X] method | human-edit | he cuts the "known as" framing and makes the name do the work
- ~~**kept:** "approximately 5,000"~~ **CORRECTED same session:** "yea approximately isnt great either". A fuzzed count is not acceptable; give the exact number or write `XXX`.
- approximately/around/roughly [round count] → the exact number, or `XXX` | human-edit | "approximately 5,000 constructs" rejected
- **but not a blanket ban on approximation.** Rounded magnitudes and ratios are attested throughout his corpus and are fine: "~10% overlap", "~90-fold faster", "approximately 39% of residues", "approximately 1.67-fold less reactive", and he left "The ratio is about 10-fold" untouched in 2A. The rule is about **countable experimental quantities you are responsible for knowing** (constructs, reads, residues, samples), not about derived ratios and percentages.
- **Order-of-magnitude scale statements are also fine** | 2026-08-13 | asked whether "hundreds of thousands of natural RNAs" and "thousands of designed constructs" needed exact numbers, he answered "hundreds of thousands is fine". **The distinction is hedging versus scale.** "Approximately 5,000 constructs" fuzzes a specific number he is responsible for knowing; "hundreds of thousands" states an order of magnitude and claims no precision. Write the exact number when one exists, an order of magnitude when that is the honest claim, and `XXX` when the number is missing. Never attach "approximately" to a countable figure.
- **kept:** "we propose to develop". He did not upgrade it to "We will develop", though his real MIRA aims all use "We will". Weak evidence; not encoded as a rule.
- **mixed evidence:** "could potentially". He cut it in 1B ("could potentially suggest" became "suggest") but kept it in 2D ("could potentially offer"). Treat hedge stacks as strip-by-default, but do not treat a surviving "could" as a voice violation.

## clinic entries (2026-08-13, item 2C: hype rejected outright)
He declined to edit 2C at all: "way too boastful... we want to be much more
measured in the discussion, we can say we are the first or something."
The permitted move is a **plain priority claim**; what is banned is the
intensifying vocabulary around it.
- represent a major advance in the field of → (state what the result establishes) | human-edit
- unprecedented → (delete, or give the number that makes the point) | human-edit
- groundbreaking → (delete) | human-edit
- opens exciting new possibilities for the RNA community → (name the specific capability that becomes possible) | human-edit
- will undoubtedly transform how the field approaches X → (delete; do not predict field-level impact in a paper) | human-edit
- for the RNA community / of broad interest to the field → (delete; audience-flattery) | human-edit
- **allowed instead:** "the first [X]", "outperforming both probes alone", "establish that [X]". Priority stated flatly, comparative framing, utility close.

**Genre split (his clarification):** this measured register is for papers; grants
may go bolder. But the boldness in his grants comes from the *scope of the claim*,
never from intensifying adjectives: "the first predictive thermodynamic models for
RNA 3D folding", "thus transforming our understanding of RNA folding and function"
(MIRA). Even a grant never says groundbreaking, unprecedented, exciting, or
undoubtedly, none of which appear anywhere in the corpus. So: **a field-level
transformation claim is a grant move and a paper violation; hype adjectives are a
violation in both.**

## clinic entries (2026-08-13, item 2B: density controlled, connectives varied)
- It is worth noting that [X]. → (delete the whole sentence, or state X plainly) | human-edit | he cut "It is worth noting that this pattern held across both adenine and cytosine" even though it carried real content; the frame is disqualifying, not just the words
- Interestingly / Furthermore / Moreover → **NOT disqualifying** | ab-choice | all three survived in the one paragraph he graded "better". Corroborates the corpus counts (furthermore 3x, notably 4x in his own hand). Prefer to cut them, but they are WARN-level, not FAIL-level: see the two-tier treatment in `bin/voice-lint.py`.

**CONFIRMED 2026-08-13 by minimal-pair test.** Two paragraphs, identical content
and identical numbers, differing only in the first and last sentence. He chose the
version with the purpose opener and the interpretive landing: **"version 2 is
better as it explains why we did things."**

So the missing *why* was the residual problem in 2A, not cadence and not word
choice. Density is necessary and not sufficient: a paragraph that reports what was
measured without establishing why it was measured is still unusable, however many
numbers it carries.

Scope note, kept honest: he named the **purpose opener** explicitly ("explains why
we did things"). The interpretive landing co-varied in the same test version, so it
is supported by association rather than independently confirmed. Both are encoded;
the landing could be separated by a further minimal pair if it ever matters.

## clinic entries (2026-08-13, item 2A: density controlled, cadence varied)
- We discarded the rest. → (delete) | human-edit | redundant once the filter and the pass count are stated
- signal-to-noise ratio exceeded 4 → constraint of over 2000 reads | human-edit | when one filter must be named, he names the read-count threshold; both appear in his real Methods
- missing number → `XXX` | human-edit | he writes the literal placeholder rather than a vague substitute: "XXX passed this analysis filter". Corroborated by his own drafts ("XXXXXX" in the TMO abstract, "[X]%" and "Supplemental Figure SXX" in the d3f rewrites). **Never paper over a missing number with a general statement; write XXX and move on.**

### cadence pairs (2A) — the key finding
- before: "There the ratio drops to 3.2-fold. Stacking explains part of this."
- after: "There, the ratio drops to 3.2-fold which can be explained by increased stacking."
- what he did: merged two short sentences by subordinating the second with "which", and added the comma after the fronted adverb.

- before: "The signal-to-noise ratio exceeded 4 for 2,141 of them. We discarded the rest."
- after: "We applied a constraint of over 2000 reads, XXX passed this analysis filter."
- what he did: merged two sentences into one comma-joined clause, dropped the redundant second statement, and flagged the unknown number.

**He did NOT merge the number run.** "Mutation fractions at unpaired adenines
averaged 0.042. Paired adenines averaged 0.004. The ratio is about 10-fold."
survived untouched as three short sentences. So the long-sentence target is not
uniform across a paragraph: **parallel quantitative reports stay short and
clipped; interpretation and mechanism get subordinated into longer sentences.**
Lengthening the number run would have been a mistake.

**Verdict on 2A: "better but still pretty bad."** Density was necessary but not
sufficient. Unresolved as of this entry.

## clinic entries (2026-08-13, item 1C)
- hopefully → (delete) | human-edit | "This will hopefully allow us" → "This study will allow us"
- This will → This study will | human-edit | he names the referent rather than leaving a bare demonstrative
- bare direction-of-effect statement → the quantity + its number + the scope | human-edit | verdict, third consecutive time: "too general"

**Confirmed pattern (3 of 3 paragraphs, across results, discussion, and aims):**
his first and only substantive verdict on generated prose is that it is too
general. In every case he made one to three surgical fixes (a hedge, a banned
word, a vacuous sentence) and then abandoned the paragraph over its content.
Word-level tells are what he cleans up in passing; underspecification is what
makes the prose unusable. A draft that is clean but general has not been
improved, it has only been polished.
