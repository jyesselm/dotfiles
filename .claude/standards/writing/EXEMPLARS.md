# Writing voice: exemplar bank (imitate these, verbatim)

Data file: verbatim own-hand paragraphs organized by rhetorical job, each with a
one-line skeleton. Rules live ONLY in `CORE.md`; this file carries examples.

**Sources (2026-08-13, TMO-free):** dms-3d-features rewrites (d3f) and MIRA
Section A (mira). `[dash-normalized]` = em-dashes in the source were converted per
CORE.md's no-dash override; everything else is untouched.

**REMOVED 2026-08-13:** all 12 exemplars sourced to the TMO/DMS draft. That draft
is student-written, not his hand. Do not restore them, and treat any exemplar
citing `dms_vs_tmo` as contaminated.

**How to use (the drafting protocol in plan-writing.md enforces this):** pick the
job below that matches the paragraph you need, paste 2-3 of its exemplars into
working context, write the new paragraph by mapping your content onto one
exemplar's skeleton sentence-role by sentence-role, then rewrite it once freely
so it reads as one connected thought, not an assembly.

## abstract-arc (context → gap → "To address this, we…" → numbers → understated close)
Skeleton: established frame; known deviation; the unknown, named precisely; action + scale; 3-4 quantitative findings; utility close.
> Dimethyl sulfate (DMS) chemical mapping probes RNA structure, where low reactivity is generally interpreted as Watson–Crick (WC) base pairs and high reactivity as unpaired nucleotides. Studies examining DMS reactivity of RNAs with known 3D structures have identified nucleotides that deviate from this interpretation, with distinct solvent accessibility and hydrogen-bonding patterns. The frequency of these outliers and the recurring 3D features that produce them remain incompletely characterized. To address this, we systematically analyzed DMS reactivity across a library of 7,500 RNA constructs containing two-way junctions with known 3D structures. DMS reactivity spans four orders of magnitude with ~10% overlap between WC and non-WC nucleotides. Non-WC bases with WC-like protection exhibit increased hydrogen bonding and reduced solvent accessibility, whereas reactive WC pairs flank junctions and correlate with weaker stacking and greater junction dynamics. Reactivity in non-canonical pairs correlates with specific atomic distances, encoding geometric information that is orthogonal to the per-residue pairing bias used by current DMS-guided secondary-structure methods. Using a single reactivity-derived phosphate–phosphate distance restraint in Rosetta FARFAR, we recover correct G-A base-pair geometries, bringing 7 of 37 previously-failing motifs above 80% native LW-type recovery, and the relationships transfer to a held-out set of 23 G-A motifs solved after our dataset was assembled. DMS reactivity thus provides atomic-scale, geometric information for RNA 3D modeling. (d3f) [dash-normalized]

## intro-context-and-gap (prior work → what existing methods do → what they cannot do, by construction → what remains unknown)
Skeleton: "Recently, we demonstrated…"; the motivation sentence; existing methods named with citations; colon into how they work; "highly effective for X, but cannot, by construction, do Y, because Z"; the counter-evidence; the three unknowns in one closing sentence.
> Recently, we demonstrated a direct relationship between DMS reactivity values and the thermodynamics of tertiary contact formation (13). This ability to provide quantitative information about RNA 3D structure motivated us to address a gap in current DMS use. Existing methods incorporate DMS reactivity through pseudo-free-energy terms (e.g., RNAstructure with DMS pseudo-energies, ViennaRNA SHAPE-guided folding, M2-net). These methods operate at the secondary-structure level: per-residue reactivity is converted to a thermodynamic bonus or penalty that biases whether a nucleotide is assigned to a WC base pair. They are highly effective for secondary-structure determination, but they cannot, by construction, encode information about non-canonical base-pair geometry, because non-canonical pairs are absent from the secondary-structure model itself. At the same time, decades of studies indicate that DMS reactivity reports on features beyond pairing state: cases where non-WC residues are protected, where WC pairs are reactive, and where sheared G-A adenines are hyper-reactive despite being base-paired (12, 20, 36–39). The structural mechanisms driving these patterns stem from variations in solvent accessibility, hydrogen bonding, and local geometry (40–43). The frequency of occurrence, the precise 3D features that generate them, and whether this information can be used predictively to constrain 3D modeling remain unknown. (d3f) [dash-normalized]

## intro-study-aims (enumerated aim → what was done → how it was validated)
Skeleton: "Fourth, we asked whether these relationships can be used, not merely observed, to…"; the action and what it recovers; the held-out validation named as a blind test.
> Fourth, we asked whether these relationships can be used, not merely observed, to constrain RNA 3D modeling at a level inaccessible to existing pseudo-energy methods. We incorporated a single reactivity-derived phosphate–phosphate distance constraint into Rosetta FARFAR and showed that it recovers native G-A base-pair geometries that unconstrained modeling fails to find. We then validated this predictive capability on a held-out set of 23 G-A-containing motifs whose 3D structures were deposited after our dataset was assembled, providing a blind test of the regression. (d3f)

## results-open (purpose first, then the design, with the placeholder convention on display)
Skeleton: what the previous result suggests, then "but a stronger test is whether…"; why this subset was chosen; "Starting only from X, we used Y to do Z"; the design with n's and the two evaluation criteria.
> The correlations above suggest reactivity encodes geometric information, but a stronger test is whether they yield correct structural inferences when used predictively. We focused on G-A pairs because they are the largest, best-validated subset and because their LW class (cWW, tHS, tWH, cWH) is geometrically diverse, making the prediction non-trivial. Starting only from sequence and the measured DMS reactivity of the adenine, we used the reactivity to P–P distance regression to assign a target distance to each G-A pair, then incorporated this as a [harmonic / flat-bottom XXX] constraint between the two phosphates in Rosetta FARFAR. For each of the 54 motifs containing one or more G-A pairs, we generated 1,000 models with and without the constraint and evaluated the top 100 by Rosetta score on (i) native LW-type recovery and (ii) RMSD to the deposited structure. (d3f) [dash-normalized]

Note the `XXX` and `[X]%` placeholders: he writes them rather than fudging a number.

## results-open-with-purpose (the confirmed required form: "To [goal], we [action]")
Skeleton: "To test whether X generalizes beyond Y, we performed Z"; where the inputs came from; what the result confirms.
> To test whether this predictive capability generalizes beyond the structures used to fit the regression, we performed a blind validation on 23 G-A-containing motifs whose 3D structures were deposited after our original dataset was assembled and were therefore held out from regression fitting. Reactivity values for these motifs came from our original DMS-MaPseq library; the held-out structures provided ground truth. The same single-distance constraint produced comparable improvements in LW-type recovery and RMSD, confirming that the relationship transfers to structures not used to derive it. (d3f)

## results-exclusion-and-effect (say what was excluded and why, then the effect with n of N)
Skeleton: what was already correct and therefore dropped; "On the remaining N motifs, [intervention] raised X from A to B and brought n additional motifs above [threshold]"; the no-harm clause.
> Seventeen motifs were already modeled correctly by unconstrained FARFAR (≥80% LW-type recovery) and were excluded from further analysis. On the remaining 37 motifs, the single reactivity-derived constraint raised mean native LW-type recovery from [X]% to [X]% and brought 7 additional motifs above the 80% recovery threshold; performance was never substantially degraded by the constraint. (d3f)

## results-illustrative-case (one motif carries the mechanism)
Skeleton: "The X illustrates the failure mode and how the fix works"; what the native structure is versus what the method does, with percentages; what the fix produces; the generalization, plus what the method did NOT have to be told.
> The 2×2 junction GGAC&GGAC illustrates the failure mode and how the constraint fixes it. The native structure contains two cWW G-A pairs, but unconstrained FARFAR converges on two sheared (tHS) pairs in 100% of top-scoring models, with Rosetta score insensitive to which geometry is sampled. Adding the reactivity-derived P–P distance produces a clean energy funnel toward the native cWW geometry, recovering it in 99.5% of top-scoring models. Across the 37-motif set, the constraint improves both LW-type recovery and per-pair RMSD, and does so without the constraint specifying which LW class to adopt: the model arrives there from the geometric information alone. (d3f) [dash-normalized]

## contrast-bridge (position new work against existing methods: complementary, not competitive)
Skeleton: existing methods named with examples; colon into how they work; "highly effective for X but cannot, by construction, do Y, because Z"; "operates one level deeper"; the two-clause landing "A determines topology; B determines geometry".
> Existing methods that incorporate DMS reactivity into RNA structure prediction (e.g., RNAstructure with DMS pseudo-energies, ViennaRNA SHAPE/DMS-guided folding, M2-net) operate at the level of secondary structure: per-residue reactivity is converted to a thermodynamic bonus or penalty that biases whether a nucleotide is assigned to a Watson–Crick base pair. These approaches are highly effective for secondary-structure determination but do not, by construction, encode information about non-canonical base-pair geometry, because non-canonical pairs are absent from the secondary-structure model itself. The reactivity-derived distance constraint we describe below operates one level deeper: it uses the same DMS measurement to place a geometric restraint on the 3D arrangement of a non-canonical pair, information that is invisible to the pseudo-energy framework. The two approaches are therefore complementary: pseudo-energy determines pairing topology; the distance constraint determines pairing geometry. (d3f) [dash-normalized, condensed]

## discussion-close (the finding, the numbers, the orthogonality claim, then "Together, these results establish…")
Skeleton: "Finally, X provides Y"; the correlation with R² inline; the additional cases; "Critically, this is orthogonal to Z:" with the two-clause split; the headline result with the most striking case inline; the blind-set transfer; "Together, these results establish…".
> Finally, DMS reactivity patterns provide quantitative geometric information for RNA tertiary structure modeling. The phosphate–phosphate distance in G-A pairs correlates with adenine reactivity (R² = 0.51, improving to R² = 0.62 with newly available structures), distinguishing cWW, tHS, tWH, and cWH conformations. Additional non-canonical pairs (C–A, C–C) display analogous distance–reactivity relationships. Critically, this geometric information is orthogonal to the per-residue pairing bias used by current DMS-guided structure prediction methods: pseudo-energy formulations determine pairing topology, while reactivity-derived distance constraints determine pairing geometry. Incorporating a single such constraint into Rosetta FARFAR recovers correct G-A geometries in motifs where unconstrained sampling fails, most strikingly the GGAC&GGAC 2×2 junction, where two cWW G-A pairs are recovered in 99.5% of top-scoring models with the constraint vs. 0% without, and brings 7 of 37 previously-failing motifs above 80% native LW-type recovery. The relationships transfer to a blind set of 23 G-A motifs whose 3D structures were deposited after our regression was fit, demonstrating that the predictive capability is not an artifact of the training set. Together, these results establish that DMS reactivity contains predictive 3D structural information accessible through geometric, rather than thermodynamic, modeling. (d3f) [dash-normalized]

## grants-gap (name the gap, prove it with the field's failures, end on "our platform closes it")
Skeleton: bold gap header claim; what exists and why it works; "No equivalent exists for…"; evidence of field-level failure with named benchmarks; "These failures stem from missing data."; our platform + throughput + "provides the throughput needed to close this gap."
> The Turner nearest-neighbor model provides ~300 free energy parameters that enable reliable secondary structure prediction [8,9], powering algorithms like RNAstructure and ViennaRNA [10,11]. This model works because secondary structure follows additive nearest-neighbor rules. No equivalent exists for the tertiary contacts, pseudoknots, kissing loops, or A-minor motifs that define functional 3D folds. Even though kissing loops and pseudoknots form through Watson-Crick base pairing, their thermodynamic stability diverges significantly from Turner predictions [13]. These non-nearest-neighbor contributions (coaxial stacking, loop entropy, and cooperativity) require thousands of systematic variants to disentangle, far beyond the throughput of traditional methods [14,15]. In CASP16, no computational method accurately predicts novel RNA 3D structures, with failures at exactly these features [14]; AlphaFold3 performs markedly worse on RNA than on proteins [15]. These failures stem from missing data. Our qMaPseq platform, which measures tertiary contact thermodynamics via Mg²⁺-dependent DMS chemical mapping at a scale of thousands of variants per experiment [18], provides the throughput needed to close this gap. (mira) [dash-normalized]

Skeleton: gold standard named with its unique achievement; "However, it requires X, restricting use to Y"; alternatives dismissed with precision; "No accessible method simultaneously…"; "Our framework extends naturally to this problem:" + the move.
> RNA-MaP [22] remains the gold standard for massively parallel binding measurements, yielding the only predictive thermodynamic model for an RNA-binding protein (Pumilio) [23]. However, it requires modified Illumina sequencers and fluorescent protein labeling, restricting use to a few labs worldwide. Complementary approaches (RBNS [24], eCLIP [25]) provide sequence preferences but not quantitative Kd or kinetic parameters. No accessible method simultaneously measures binding parameters and RNA structural context at scale. Our qMaPseq framework extends naturally to this problem: it replaces Mg²⁺ titrations with protein concentration titrations, reading out binding through DMS protection at the interface, an approach independently validated by Thurm et al. (2026) for MS2 coat protein [26]. (mira) [dash-normalized]

## grants-aims (action verb + method (defined in parentheses) + scale + differentiator + why it compounds)
Skeleton: "We will develop X (definition in parentheses) to measure Y for thousands of Z without [barrier]"; validation systems named; "Because [mechanism], every measurement includes [bonus], enabling [capability]."
> We will develop qBind-MaPseq (protein concentration titrations monitored by DMS chemical mapping) to measure Kd for thousands of RNA-protein interactions without specialized equipment. We will validate on benchmark systems (L7Ae/kink-turns, PUM2, MS2) and apply to disease-relevant RNA-binding proteins (TDP-43, MBNL1, RBFOX2). Because DMS simultaneously reports on RNA structure, every binding measurement includes a matched structural profile, enabling direct assessment of how RNA conformational ensembles modulate protein recognition. (mira) [dash-normalized]

Skeleton: "Using our X platform, we will measure…"; "From these datasets, we will derive the first…"; "We will validate predictive accuracy on…".
> Using our qMaPseq platform, we will measure thermodynamic parameters for thousands of kissing loop, pseudoknot, a-minor interactions, and other non-canonical contacts. From these datasets, we will derive the first free energy parameters for tertiary contacts and integrate them into the RNAstructure folding algorithm. We will validate predictive accuracy on a panel of natural RNAs with known 3D structures. (mira)

## grants-impact (bold vision backed by enumerated concrete outputs)
Skeleton: "Together, [these aims] will produce [big quantity] that currently do not exist"; semicolon-chained deliverables each tagged to its theme; the translational hook grounded in named diseases.
> Together, research within these themes is expected to produce tens of thousands of quantitative measurements that currently do not exist; tertiary contact free energies for integration into RNAstructure (Theme 1); the largest matched chemical-probing/3D-structure database for improving RNA modeling constraints (Theme 2); and the first large-scale quantitative binding data for structured RNA-protein recognition (Theme 3). The disease relevance of Theme 3 protein targets (TDP-43/ALS, MBNL1/myotonic dystrophy, and FMRP/Fragile X) ensures these datasets have translational value for understanding how mutations in RNA regulatory regions alter protein binding. (mira)

## cadence pairs (his before → after edits, from the 2026-08-13 clinic)
How he restructures. These come from his own live edits and are unaffected by the
TMO removal. Imitate the *move*, not the subject matter.

**Merge interpretation by subordinating with "which".**
- before: "There the ratio drops to 3.2-fold. Stacking explains part of this."
- after: "There, the ratio drops to 3.2-fold which can be explained by increased stacking."

**Merge and drop the redundant follow-up; flag the unknown number rather than fudging it.**
- before: "The signal-to-noise ratio exceeded 4 for 2,141 of them. We discarded the rest."
- after: "We applied a constraint of over 2000 reads, XXX passed this analysis filter."

**Leave runs of parallel measurements clipped.** In the same edit he left this
untouched as three short sentences, so do not pad a number run to hit the median:
- "Mutation fractions at unpaired adenines averaged 0.042. Paired adenines averaged 0.004. The ratio is about 10-fold."

**Collapse a vacuous lead into the measurement itself.**
- before: "The data show interesting patterns. Reactivity decreases as magnesium increases."
- after: "We observed the mutation fraction decrease as magnesium increased."

**Strip the hedging frame, keep the claim.**
- before: "It is anticipated that this will enable the measurement of structural features..."
- after: "This will enable the measurement of structural features..."

## GAPS (jobs with no own-hand exemplar since the TMO removal)
These previously drew on the student draft and now have nothing behind them.
Do not invent replacements; fill them from his next own-hand draft.
- **intro-context-open** (the broad opening frame of an introduction)
- **results-landing** (a short interpretive close to a results paragraph; the discussion-close above is the nearest available model)
- **discussion-open** (restating what was done, then the global finding)
