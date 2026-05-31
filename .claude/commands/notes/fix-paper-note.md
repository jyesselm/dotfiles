---
description: Fix and enhance a paper note while preserving all content
---

Clean up and enhance an existing paper note in Obsidian. Uses the Obsidian MCP tools.

## Input: $ARGUMENTS

- Paper note path or title (required)
- Optional: `--dry-run` - show changes without applying

## Core Principles

**NEVER remove content** - only reorganize, enhance, and clean up.

## Process

### 1. Read the Note

Use `mcp__obsidian__read_note` to get the current content and frontmatter.

### 2. Fix Frontmatter

Ensure frontmatter matches this schema:

```yaml
---
title: [Paper title - clean, no journal suffix]
date: YYYY-MM-DD          # Creation date
type: ref/paper
status: active
authors:
  - "[[First Author]]"    # Wikilink format for linking
  - "[[Second Author]]"
year: YYYY                # Publication year
journal: [Journal Name]
doi: [DOI if available]
source: [URL to paper]
science-tags: [rna, k-turn, crystallography, etc.]
updated: YYYY-MM-DD       # Today's date
---
```

**Frontmatter fixes:**
- Convert author strings to wikilinks: `"David M. J. Lilley"` → `"[[David M. J. Lilley]]"`
- Extract year from `published` field if present
- Parse journal from title or source URL
- Remove redundant fields (e.g., `published` if `year` exists)
- Add missing `type: ref/paper`
- Calculate `week` and `month` from `date`
- Infer tags from content (methods, organisms, techniques)

### 3. Add Summary Section

If no `## Summary` exists, create one after the Abstract:

```markdown
## Summary

> [2-3 sentence summary of the paper's main contribution and significance]
```

Generate summary from Abstract and Introduction content.

### 4. Add Key Findings Section

If no `## Key Findings` exists, add after Summary:

```markdown
## Key Findings

1. **[Finding 1 title]**: [Brief explanation]
2. **[Finding 2 title]**: [Brief explanation]
3. **[Finding 3 title]**: [Brief explanation]
```

Extract from Results/Discussion sections.

### 5. Fix Citations

**Current format issues to fix:**
- `[^1]` footnote style → keep but ensure References section is clean
- Inline citations like `(ref. [^10])` → `[^10]`
- Clean up spacing around citations: `ions [^10]` not `ions[^10]`
- Ensure all `[^N]:` references are properly formatted in References section

**Reference formatting:**
```markdown
[^1]: Klein, D. J., et al. The kink-turn: a new RNA secondary structure motif. *EMBO J.* **20**, 4214–4221 (2001).
```

### 6. Cross-Reference Other Papers

Search the vault for related papers using `mcp__obsidian__search_notes`:

1. Search for author names mentioned in the paper
2. Search for key terms (k-turn, riboswitch, etc.)
3. Search for cited paper titles

For any paper found in the vault, convert to wikilink:
- `Klein, D. J., Schmeing, T. M., Moore, P. B. & Steitz, T. A.` → check if paper exists
- If `[[Klein 2001 - The kink-turn]]` exists, add link in References or Related section

Add `## Related Notes` section if papers found:
```markdown
## Related Notes

- [[Other Paper Title]]
- [[Another Related Paper]]
```

### 7. Clean Up Markdown

**Formatting fixes:**
- Ensure single H1 title at top (use paper title)
- Fix header hierarchy (H2 for main sections)
- Clean up whitespace (no multiple blank lines)
- Fix list formatting
- Ensure images have alt text
- Convert bare URLs to markdown links
- Fix superscript/subscript: `Mg <sup>2+</sup>` → `Mg²⁺` or keep HTML if complex
- Clean up escaped brackets: `\\[Mg` → `[Mg`
- Ensure code blocks have language specified

**Section ordering (preserve all content):**
1. H1 Title
2. Summary (new)
3. Key Findings (new)
4. Abstract
5. Introduction
6. Results
7. Discussion
8. Methods
9. Additional information
10. References
11. Related Notes (new)

### 8. Apply Changes

Use `mcp__obsidian__write_note` to save the improved note.

## Output Format

```
## Paper Note Fix: [[paper-title]]

### Frontmatter Changes
- Added: type: ref/paper
- Fixed: authors now wikilinked
- Added: week, month fields
- Inferred tags: [rna, k-turn, crystallography]

### New Sections Added
- [x] Summary (generated from abstract)
- [x] Key Findings (3 findings extracted)
- [x] Related Notes (2 papers found in vault)

### Citation Fixes
- Fixed 5 inline citation spacing issues
- Cleaned up reference formatting

### Cross-References Found
- [[Lilley 2007 - The role of specific 2'-hydroxyl groups]]
- [[Klein 2001 - The kink-turn motif]]

### Markdown Cleanup
- Fixed header hierarchy
- Cleaned 3 escaped bracket sequences
- Standardized whitespace

Apply changes? [y/n]
```

## Example

```bash
# Fix a specific paper note
/fix-paper-note 300-reference/science/papers/A critical base pair in k-turns.md

# Preview changes without applying
/fix-paper-note "k-turns Nature Communications" --dry-run
```

## Tag Inference Rules
dont use tags property but science-tags

| Content Pattern | Suggested Tags |
|-----------------|----------------|
| FRET, fluorescence | methods/fret |
| crystallography, X-ray, diffraction | methods/crystallography |
| k-turn, kink-turn | rna/k-turn |
| riboswitch | rna/riboswitch |
| ribosome | rna/ribosome |
| Mg²⁺, metal ions | biochemistry/metal-ions |
| folding, tertiary | rna/folding |
| L7Ae, protein binding | protein/rna-binding |
