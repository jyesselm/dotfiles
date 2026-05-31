# Yesselman writing voice — scientific style reference

How Joseph Yesselman writes scientific prose. Use this to draft or edit manuscripts,
abstracts, and grant text in his voice. Distilled from his published papers, weighted
toward sole-corresponding work (qMaPseq, NAR 2024; "3D features from DMS reactivity",
NAR 2025). Link it from a project CLAUDE.md (`@~/.claude/standards/writing-style.md`)
or reference it directly in a chat.

## Voice in one line
Formal but plain-spoken; assertive about data, carefully hedged about mechanism; written
for a working bench scientist, with a through-line of **making hard methods accessible**.
Always "we" (never "I"), never hype.

## Abstract — the 6-move spine (his most repeatable pattern)
1. **Context** — one sentence on why the RNA class/phenomenon matters.
2. **Gap** — pivot on *"However,"* / *"Despite…"*: existing methods are low-throughput, inaccessible, or conceptually incomplete.
3. **"Here, we introduce/present [named thing]"** — the method or principle, named, often with an acronym.
4. **System + scale** — the actual numbers done ("98 variants," "7,500 constructs," "one-pot reaction").
5. **Key quantitative results** — R²/fold-change inline; escalate the punchline with *"Surprisingly,"* and *"the first direct evidence that…"* when earned.
6. **Significance close** — *"These results demonstrate that…"* + a virtues triad (accessible · high-throughput · directly links X to Y).

Real example (qMaPseq) — open → close:
> "Structured RNAs often contain long-range tertiary contacts that are critical to their function. Despite the importance of tertiary contacts, methods to measure their thermodynamics are low throughput or require specialized instruments. **Here, we introduce** a new quantitative chemical mapping method (qMaPseq)…"
> "**These results demonstrate that** qMaPseq is broadly accessible, high-throughput and directly links DMS reactivity to thermodynamics."

## Introduction — a 4-paragraph funnel
1. Broad importance, usually a **triad + citation bundle**: *"Structured RNAs play critical roles in cellular functions, are foundational to the life cycle of RNA viruses, and serve as blueprints for new artificial machines (4–9)."*
2. Teach the background the reader needs (how DMS works, two-step folding) — a teaching reflex.
3. Survey prior methods generously, then pivot on *"However,"* to their limitation (*"…not accessible to other scientists"*).
4. State the gap explicitly, then the contribution (*"This study introduces…"*). Often end with a mini-roadmap: *"First we… We then… Furthermore…"*

## Sentence-level signatures
- **The signature opener:** *"To [goal], we [past-tense action]…"* — purpose precedes method. (e.g. "To probe the thermodynamics of tertiary contact formation, we utilized…"). Use it to head Results paragraphs.
- **Explicit sequencing:** *First, … Next, … Furthermore, … Lastly,/Finally, …*
- **The interpretation tail:** end an observation with *"…, indicating/suggesting [interpretation]"* or *"…, indicative of [X]."*
- **Closing move per subsection:** *claim → "These results/findings indicate/demonstrate…" → restated contribution.*
- **Rhythm:** medium declaratives (~20–30 words), often a claim sentence + a consequence sentence. Avoid long Latinate sprawl. Use triads in summary sentences.

## Reporting numbers
Inline and parenthetical, immediately after the claim — never buried or table-only:
- "agree well with measurements from specialized instruments (R2 = 0.64)"
- "excellent reproducibility (R² = 0.99) for the 240,000 DMS measurements"
- fold-changes verbalized ("7-fold higher"), ΔΔG with sign + units ("destabilized by 1.13 kcal/mol"), errors as ± ("0.22 ± 0.004 mM").

## Confidence calibration (a defining feature)
- **Assert flatly:** data and method performance ("We determined the [Mg2+]₁/₂ values for 84 of the 98 mutants").
- **Hedge mechanism:** *suggests, likely, may, posited, hypothesized, consistent with, indicative of* — **one qualifier per claim**, never stacked.
- **Flag your own limits in the same breath:** *"consistent with an A–A platform… but are not definitive and require additional experiments."*
- Separate hypothesis from result openly (*"We hypothesize that…"* before the test).

## Vocabulary
- **Lean on:** accessible/democratize, generalize, high-throughput, one-pot reaction, nucleotide-resolution, continuum, orders of magnitude, scaffold, construct, variant, reactivity, thermodynamics, proof-of-concept, systematically. Interest-flag = *"intriguing"*. Reserve *"Surprisingly,"* for the single biggest finding.
- **Frame significance around** accessibility, throughput/scale, and therapeutic/design payoff — name concrete payoffs (HIV-1, SARS-CoV-2, RNA design).

## DO
1. Open Results/Intro paragraphs with **"To [goal], we [action]…"**.
2. Build abstracts on the 6-move spine; use the **"Here, we introduce…"** hinge and the **"These results demonstrate…"** triad close.
3. Put every number **inline, parenthetically, right after its claim**.
4. **Calibrate confidence to claim type** — assert data, hedge mechanism, state interpretation limits explicitly.
5. Sequence with **First/Next/Furthermore/Lastly**; end observations with an **"…, indicating X"** tail.
6. Carry significance through **utility to others** (who can now do this), not self-praise.
7. Gloss domain terms inline on first use.

## DON'T
1. No first-person singular; no hype superlatives ("revolutionary," "unprecedented," "groundbreaking").
2. Don't stack hedges ("may possibly perhaps").
3. Don't bury a result in a later sentence or table-only.
4. Don't write sprawling multi-clause sentences.
5. Don't praise your own novelty directly; don't leave a mechanistic claim unqualified.

## Pastiche (target voice)
> Structured RNAs frequently rely on transient loop–loop contacts to switch between functional conformations, yet these contacts are critical to their regulatory roles. Despite their importance, methods to map loop–loop pairing partners are low throughput or require specialized crosslinking equipment inaccessible to most laboratories. Here, we introduce a quantitative chemical mapping approach (kMaPseq) that resolves loop-pairing partners across thousands of RNAs in a single one-pot reaction using only standard biochemistry reagents. With kMaPseq, we mapped 1,240 engineered hairpin variants and found that loop DMS reactivity directly reports on pairing probability (R² = 0.71), and, surprisingly, recovers known partners with single-nucleotide resolution. These results demonstrate that kMaPseq is broadly accessible, high-throughput, and directly links DMS reactivity to loop-pairing state.

## Scope note
This is his independent voice (sole-corresponding papers). Collaborative/other-lab papers
dilute these markers (e.g. "revolutionized," rhetorical questions) — that's co-author voice,
not the target. For non-RNA or non-methods writing, keep the structure and confidence
calibration; swap the domain vocabulary.
