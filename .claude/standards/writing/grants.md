# Writing voice: grants & specific aims

Apply `@~/.claude/standards/writing/CORE.md`. The one shift from papers: in grants
the significance goes **bold**. Quotes from the 2026 MIRA renewal (his hand).

## Vision / significance: go big, claim a first
State the field-level change you will enable; future-tense "we will," and "first":
> "The resulting datasets will support the first predictive thermodynamic models for RNA 3D folding and molecular recognition, and we will link these models directly to biological function." (2026 MIRA renewal)
> "Closing this gap would enable the first structure-aware predictive models of RNA-protein recognition, connecting sequence variation to binding affinity and ultimately to disease phenotype." (same)

Back the boldness with concrete execution; never hedge the vision.

## Aims: action + the concrete method in parentheses
> "We will combine same-site differential probing (10+ methylating reagents with distinct steric and electrostatic properties) with biophysical titrations (pKa, Tm, [Mg2+]1/2) to generate multi-dimensional probing data at every probed nucleotide across thousands of RNAs that contain motifs with known 3D structures." (2026 MIRA renewal)
> "We will develop qBind-MaPseq (protein concentration titrations monitored by DMS chemical mapping) to measure Kd for thousands of RNA-protein interactions without specialized equipment." (same)

Note the move: name the new method, define it in parentheses, state the scale ("thousands"), and the differentiator ("without specialized equipment").

**Required check (from the 2026-08-13 clinic, where a generic aim was rejected as
"too general"):** an aim sentence must fill all four slots. Name the method, define
it in parentheses, state the scale as a number or "thousands", and name what it
beats or avoids. An aim that says it will "explore", "test several reagents", or
"compare the results" has filled none of them and is a placeholder, not an aim.
Also name the validation systems and the application targets, as in the
L7Ae/PUM2/MS2 then TDP-43/MBNL1/RBFOX2 pattern above.

## Project summary structure (from a full conversion, 2026-08-13)
Learned while rewriting an LSC summary into the shape of his multi-state RNA
summary. These are structural, and none of them are visible at the sentence level.

- **The setup paragraph ends on the goal.** Do not strand "In this project, the overall goal is to..." in its own short paragraph. It closes the paragraph that introduces the discovery, and the objectives follow immediately. A setup paragraph that ends on a description of the finding never says what will be done about it.
- **Every objective needs a distinct output, or they collapse into each other.** His own framing: discover the rules, use them to identify, use them to design. The outputs then differ by kind, a **rule** (with units), a **classifier benchmarked against the incumbent method**, an **algorithm**. Later objectives should explicitly consume the earlier ones ("the rules from Objective 1"), which makes the dependency visible and stops three parallel analyses masquerading as a program.
- **Each objective ends on what it produces, not on the method.** "Validated by chemical mapping" is a method and a weak close; *"each validated class yields a compensation rule, the stem stability required per kcal/mol of loop destabilization"* is a deliverable with units. If the objective title promises "quantitative rules", the body must state what a rule is.
- **State the standard approach before naming its failure.** The sentence he added to a generated opening was *"Commonly, predicted secondary-structure stability is utilized to assess whether a structure might be functional"*, which the draft had skipped on its way from problem to failure.
- **Objectives run 75-100 words.** They must fit the page. When he said an objective "lacks detail", a 144-word version was rejected as "too long with too much detail", and the fix was the *same length* as the original with four concrete additions: a named exemplar, the stratifying variable, the control, and the criterion for a hit. **Detail means facts, not words. Explanation is what to cut.**

## Throughout
Active voice, numbers where they sharpen a claim (CORE). Bold on vision, concrete
on execution. The long-articulated sentence is fine here too; the panel bands in
CORE still apply.
