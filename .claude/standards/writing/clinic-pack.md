# Voice clinic pack (~40 min, one sitting)

**Disposable.** Its outputs fold into `REJECTIONS.md` and the cadence-pairs
section of `EXEMPLARS.md`; delete this file once that is done.

Purpose: capture the one thing the corpus cannot show, which is what you would
never write. Answer fast and by instinct; do not deliberate. The answer key for
Parts 2 and 3 is deliberately NOT in this file.

---

## Part 1 (~20 min): line-edit three generated paragraphs

Edit these as you would edit a student's draft: cross out, replace, restructure.
Every substitution becomes a `REJECTIONS.md` entry and every restructuring a
cadence pair. **Highest-value part. If you run out of time, doing only this is
still a win.**

### 1A (results-open, generated)
> We investigated the effect of magnesium on RNA folding using our chemical probing approach. The data show interesting patterns. Reactivity decreases as magnesium increases. This was observed for most constructs in the library. Notably, some constructs behaved differently. These results suggest that magnesium plays a crucial role in stabilizing tertiary structure, which is significant for understanding RNA folding.

### 1B (discussion-close, generated)
> In conclusion, our study delves into the relationship between chemical reactivity and RNA structure. We have leveraged a novel high-throughput approach to obtain robust results. The findings are significant and could potentially suggest new avenues for future research. Moreover, this work represents an important step forward for the field, and we believe it will be of broad interest to the RNA community.

### 1C (grants-aims, generated)
> Aim 2 will explore how different chemical probes can be used to study RNA structure. We plan to test several reagents and compare the results. This will hopefully allow us to better understand which probes are most informative. The expected outcome is an improved understanding of RNA structural features, which may be useful for the field going forward.

---

## Part 2 (~12 min): eight forced-choice pairs

Content is matched within each pair, so subject matter will not tell you which is
which. For each: **which is yours, and name the one word or move that gave the
other away.** The naming matters more than the choice. Two pairs are repeats with
the order swapped; do not try to spot them.

### Pair 1
**A.** RNA molecules play a crucial role in many biological processes. They act as intermediates between DNA and protein. They also regulate transcription, translation, and RNA processing. These functions depend on RNA folding into complex three-dimensional shapes and responding to various stimuli. Therefore, it is important to determine RNA structure, as this helps us understand mechanisms and diagnose disease.

**B.** RNA molecules have a range of biological functions, including acting as an intermediate between DNA and protein and regulating transcription, translation, and RNA processing (1-5). These functions arise from RNA folding into intricate three-dimensional shapes and from its response to stimuli (6-8). Determining RNA structure is therefore a prerequisite for mechanistic understanding and for diagnosing how structural dysregulation contributes to disease.

### Pair 2
**A.** Yet because DMS is the only probe applied at this scale, it is not possible to separate DMS-specific features from features that reflect generic WC-edge accessibility using DMS data alone. Resolving this requires a second probe that reads the same atoms using a chemically distinct reaction, one that, if it produces the same per-nucleotide signal as DMS, would establish that the readout is geometry-specific; if not, it would reveal which features of the DMS signal are probe-specific.

**B.** However, DMS is currently the only probe used at this scale. This makes it difficult to distinguish DMS-specific features from those reflecting generic WC-edge accessibility. A second probe would help to resolve this issue. Ideally, such a probe would target the same atoms through a different chemical reaction. If the signals match, this would suggest that the readout is geometry-specific. If not, it may reveal which features are probe-specific.

### Pair 3
**A.** The two classes showed clearly different distributions. GA-GA pairs were strongly enriched toward negative ratios. In fact, over 99% of GA-GA pairs were found in the most DMS-biased region, dropping to just 1.1% in the most TMO-favored region. Interestingly, GG-AA pairs showed the opposite pattern. They comprised nearly 99% of pairs in the most TMO-favored region and were virtually absent from the strongly DMS-biased tail.

**B.** The distributions of reactivity ratio for these two classes are clearly separated: GA-GA pairs are heavily enriched toward strongly negative ratios, with over 99% of GA-GA pairs found in the most DMS-biased region of the distribution, dropping to just 1.1% in the most TMO-favored region. In contrast, GG-AA pairs show the opposite pattern, comprising nearly 99% of pairs in the most TMO-favored region of the distribution while being virtually absent from the strongly DMS-biased tail.

### Pair 4
**A.** Existing methods that incorporate DMS reactivity into RNA structure prediction (e.g., RNAstructure with DMS pseudo-energies, ViennaRNA SHAPE/DMS-guided folding, M2-net) operate at the level of secondary structure: per-residue reactivity is converted to a thermodynamic bonus or penalty that biases whether a nucleotide is assigned to a Watson-Crick base pair. These approaches are highly effective for secondary-structure determination but do not, by construction, encode information about non-canonical base-pair geometry, because non-canonical pairs are absent from the secondary-structure model itself. The reactivity-derived distance constraint we describe below operates one level deeper: it uses the same DMS measurement to place a geometric restraint on the 3D arrangement of a non-canonical pair, information that is invisible to the pseudo-energy framework.

**B.** Several existing methods incorporate DMS reactivity into RNA structure prediction, such as RNAstructure, ViennaRNA, and M2-net. These methods work at the secondary structure level. Reactivity is converted into a thermodynamic bonus or penalty that influences base pair assignment. While these approaches are very effective for secondary structure determination, they cannot capture non-canonical base pair geometry. This is because non-canonical pairs are not part of the secondary structure model. Our distance constraint operates at a deeper level and captures information that pseudo-energy methods cannot access.

### Pair 5
**A.** The Turner nearest-neighbor model provides ~300 free energy parameters that enable reliable secondary structure prediction [8,9], powering algorithms like RNAstructure and ViennaRNA [10,11]. This model works because secondary structure follows additive nearest-neighbor rules. No equivalent exists for the tertiary contacts, pseudoknots, kissing loops, or A-minor motifs that define functional 3D folds. In CASP16, no computational method accurately predicts novel RNA 3D structures, with failures at exactly these features [14]; AlphaFold3 performs markedly worse on RNA than on proteins [15]. These failures stem from missing data.

**B.** The Turner nearest-neighbor model has been very successful for secondary structure prediction, providing around 300 free energy parameters used by algorithms such as RNAstructure and ViennaRNA. However, there is currently no equivalent model for tertiary contacts such as pseudoknots, kissing loops, and A-minor motifs. This represents an important gap in the field. Recent benchmarking efforts have shown that computational methods struggle with novel RNA 3D structures, and AlphaFold3 also performs less well on RNA than on proteins. It is likely that these failures are due to a lack of available data.

### Pair 6
**A.** We plan to develop a new method called qBind-MaPseq, which will use protein concentration titrations with DMS chemical mapping as a readout. This should allow us to measure Kd values for many RNA-protein interactions without requiring specialized equipment. We will first validate the approach on well-characterized systems and then apply it to several disease-relevant RNA-binding proteins. An advantage of this approach is that DMS also reports on RNA structure, so structural information will be obtained alongside the binding measurements.

**B.** We will develop qBind-MaPseq (protein concentration titrations monitored by DMS chemical mapping) to measure Kd for thousands of RNA-protein interactions without specialized equipment. We will validate on benchmark systems (L7Ae/kink-turns, PUM2, MS2) and apply to disease-relevant RNA-binding proteins (TDP-43, MBNL1, RBFOX2). Because DMS simultaneously reports on RNA structure, every binding measurement includes a matched structural profile, enabling direct assessment of how RNA conformational ensembles modulate protein recognition.

### Pair 7
**A.** However, DMS is currently the only probe used at this scale. This makes it difficult to distinguish DMS-specific features from those reflecting generic WC-edge accessibility. A second probe would help to resolve this issue. Ideally, such a probe would target the same atoms through a different chemical reaction. If the signals match, this would suggest that the readout is geometry-specific. If not, it may reveal which features are probe-specific.

**B.** Yet because DMS is the only probe applied at this scale, it is not possible to separate DMS-specific features from features that reflect generic WC-edge accessibility using DMS data alone. Resolving this requires a second probe that reads the same atoms using a chemically distinct reaction, one that, if it produces the same per-nucleotide signal as DMS, would establish that the readout is geometry-specific; if not, it would reveal which features of the DMS signal are probe-specific.

### Pair 8
**A.** The Turner nearest-neighbor model has been very successful for secondary structure prediction, providing around 300 free energy parameters used by algorithms such as RNAstructure and ViennaRNA. However, there is currently no equivalent model for tertiary contacts such as pseudoknots, kissing loops, and A-minor motifs. This represents an important gap in the field. Recent benchmarking efforts have shown that computational methods struggle with novel RNA 3D structures, and AlphaFold3 also performs less well on RNA than on proteins. It is likely that these failures are due to a lack of available data.

**B.** The Turner nearest-neighbor model provides ~300 free energy parameters that enable reliable secondary structure prediction [8,9], powering algorithms like RNAstructure and ViennaRNA [10,11]. This model works because secondary structure follows additive nearest-neighbor rules. No equivalent exists for the tertiary contacts, pseudoknots, kissing loops, or A-minor motifs that define functional 3D folds. In CASP16, no computational method accurately predicts novel RNA 3D structures, with failures at exactly these features [14]; AlphaFold3 performs markedly worse on RNA than on proteins [15]. These failures stem from missing data.

---

## Part 3 (~8 min): six-item lineup

Three of these are yours; three came out of the rebuilt pipeline (exemplar-mapped
and lint-passed). Classify each as **mine** or **generated**, and for each also
answer: **did you recognize this exact paragraph from memory?** Recognized items
are discarded from scoring, because recognizing your own sentences is not the
same as detecting your own style.

Note honestly: because the pipeline fixes are already in place, this measures the
*rebuilt* pipeline, not a pre-fix baseline. A true pre-intervention number is no
longer obtainable.

**Item 1.** To assess whether solvent exposure could help explain the observed differences in reactivity, we examined the Solvent Accessible Surface Area (SASA) of both DMS and TMO. DMS showed a low correlation (R2 = 0.41) with SASA, suggesting that SASA alone does not account for nucleotide methylation. We hypothesized that TMO, due to its smaller size, would show a stronger correlation. Unexpectedly, however, the correlation between TMO mutation fraction and SASA was even weaker (R2 = 0.35) than that observed for DMS, suggesting that additional structural or chemical factors may govern TMO reactivity.

**Item 2.** We compared per-nucleotide reactivity between the two probing temperatures across the full construct set (1,042 junctions; 9,860 A and C residues). Reactivity measured at 37 °C is systematically higher than at 20 °C, by 22% per nucleotide, consistent with the increased rate of the alkylation reaction at elevated temperature. The offset is global but not uniform. Constructs containing three or more consecutive non-canonical pairs deviate from the global trend, and these are precisely the constructs whose junctions are most conformationally heterogeneous in the deposited structures. Comparing raw mutation fractions across the two conditions is therefore a poor summary: in linear space the two temperatures are only weakly correlated (R2 = 0.47), whereas after log transformation they are strongly proportional (R2 = 0.79), as expected for a single reaction whose rate constant changes but whose target atoms do not.

**Item 3.** Analysis of 1×1 two-way junction motifs containing non-canonical C-U pairs reveals a consistent bias toward DMS reactivity across the dataset. The mean reactivity ratio is negative for these motifs, indicating that DMS reports higher modification levels than TMO under these local structural conditions. This trend holds across all observed stacking contexts adjacent to the C-U mismatch; however, the magnitude of DMS bias varies with flanking stack identity. UU-stacks show the weakest negative shift, with approximately 39% of residues exhibiting comparatively higher TMO reactivity, whereas AU-stacks display the strongest DMS bias and are uniformly DMS-reactive across all residues.

**Item 4.** Reactivity at the closing pair of the loop tracks the number of hydrogen bonds it accepts, falling from a median mutation fraction of 0.031 for single-hydrogen-bond geometries to 0.004 for those accepting three, a factor of roughly eight across the range. The trend holds separately for adenine and cytosine, and it holds within each junction size class, indicating that it does not arise from a confound between hydrogen bonding and loop size. Pairs that fall off the trend are enriched for direct magnesium coordination in the deposited structures, where the metal ion rather than a base partner occludes the Watson-Crick edge. This distinction matters for interpretation: a protected nucleotide reports that its Watson-Crick edge is occupied, not that it is base-paired, and the two situations carry different structural consequences for modeling.

**Item 5.** Within 2×2 junctions containing two consecutive A-G pairs, the strand arrangement further stratifies probe bias. The GA-GA arrangement (mixed-strand) accounts for 65.4% of all 2×2 A-G pairs, while the GG-AA arrangement (adenines on one strand, guanines on the opposing strand) comprises the remaining 34.6%. These GA-GA motifs are conformationally heterogeneous and can adopt either cWW or tHS geometries; junctions adopting tHS interactions are almost exclusively DMS-biased, and even those adopting cWW geometry retain an average DMS bias, distinguishing them from the GG-AA class.

**Item 6.** Deriving thermodynamic parameters from probing data requires that the measured signal respond to the folding equilibrium rather than to the probing reaction itself. We tested this by varying the probing time from 2 to 20 min and asking whether the extracted [Mg2+]1/2 values shifted, since a reaction that perturbs the equilibrium would produce a systematic drift. Across 340 constructs the extracted midpoints are stable within error (mean shift 0.03 mM, well below the 0.11 mM median fitting uncertainty), confirming that the measurement reports the underlying equilibrium across this window. Extending the probing time beyond 20 min does introduce a measurable drift toward apparent stabilization, which sets the practical upper bound on the assay.

---

## After the clinic
Claude writes the results into `REJECTIONS.md` (tagged `human-edit` and
`ab-choice`) and the cadence-pairs section of `EXEMPLARS.md`, reports your
detection accuracy, then deletes this file.
