---
description: Create literature review notes for a paper
---

Create structured notes for a scientific paper. Use the obsidian MCP tools.

## Input: $ARGUMENTS

Expects either:
- DOI, URL, or paper title
- Or path to a PDF to summarize

## Note Structure

```markdown
---
date: [TODAY]
week: [CURRENT_WEEK]
month: [YYYY-MM]
type: ref/paper
status: active
authors: [list]
year: [publication year]
journal: [journal name]
doi: [if available]
tags: [rna, methods, etc]
updated: [TODAY]
---

# [Paper Title]

## Citation
[Full citation]

## Key Question
[What problem does this paper address?]

## Main Findings
1. [Finding 1]
2. [Finding 2]
3. [Finding 3]

## Methods
[Key methodological approaches]

## Data/Resources
- [Datasets released]
- [Code repositories]
- [Supplementary materials]

## Strengths
- [What's done well]

## Limitations
- [Caveats or weaknesses]

## Relevance to My Work
[How does this connect to your research?]

## Key Figures
[Reference important figures]

## Quotes
> [Important quotes with page numbers]

## Follow-up
- [ ] [Questions to investigate]
- [ ] [Methods to try]
- [ ] [Papers to read next]

## Related Notes
- [[]]
```

## Workflow

1. If DOI/URL provided, fetch paper metadata via web search
2. If PDF path, read and extract key information
3. Generate filename: `YYYY-author-short-title.md`
4. Save to `300-reference/science/`
5. Return path and prompt for any additions
