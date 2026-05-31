---
description: Improve an existing note's content, structure, and frontmatter
---

Analyze and enhance an existing Obsidian note.

## Input: $ARGUMENTS

- Note path or title (required)
- Optional: `--frontmatter` - only fix frontmatter
- Optional: `--structure` - only improve structure
- Optional: `--full` - comprehensive improvement (default)

## Improvement Areas

### 1. Frontmatter Fixes

**Add missing fields:**
```yaml
---
date: [extract from filename or add today]
type: [infer from content]
status: [default: active]
tags: [infer from content]
updated: [today]
---
```

**Infer type from content:**
| Content Signals | Inferred Type |
|-----------------|---------------|
| Code blocks, functions | ref/code |
| Citations, DOI, journal | ref/paper |
| Steps, procedure | howto or protocol |
| Attendees, agenda | meeting |
| Hypothesis, experiment | research |
| TODO heavy, goals | project |

**Infer tags from content:**
- Scan for keywords: python, RNA, DMS, analysis, etc.
- Extract from headers
- Identify packages/tools mentioned

### 2. Structure Improvements

**Check and fix:**
- [ ] Single H1 title at top
- [ ] Logical header hierarchy (no skipping levels)
- [ ] Consistent header style
- [ ] Code blocks have language specified
- [ ] Lists are properly formatted
- [ ] Tables are aligned

**Add missing sections based on type:**

| Type | Expected Sections |
|------|-------------------|
| ref/code | Purpose, Code, Usage, Notes |
| ref/paper | Key Findings, Methods, Relevance |
| howto | Prerequisites, Steps, Troubleshooting |
| research | Question, Approach, Results, Next Steps |
| meeting | Attendees, Agenda, Action Items |

### 3. Content Enhancements

- Add `## Related` section if missing
- Convert bare URLs to markdown links
- Add checkbox syntax to TODO items
- Ensure consistent formatting

## Process

1. Read note using `mcp__obsidian__read_note`
2. Analyze current state
3. Show proposed changes
4. Ask for confirmation
5. Apply changes using `mcp__obsidian__write_note` or `mcp__obsidian__patch_note`

## Output Format

```
## Note Analysis: [[note-title]]

### Current State
- Type: [detected/missing]
- Frontmatter: [complete/incomplete - X fields missing]
- Structure: [good/needs work]

### Proposed Changes

**Frontmatter:**
- Add: type: ref/code
- Add: language: python
- Add: tags: [dms, analysis, normalization]
- Add: packages: [pandas, numpy]
- Update: updated: 2024-01-15

**Structure:**
- Add missing `## Related` section
- Fix header hierarchy (H4 after H2)
- Add language to 2 code blocks

**Content:**
- Convert 3 bare URLs to links
- Add checkboxes to 5 TODO items

Apply changes? [y/n/selective]
```

## Selective Mode

If user chooses selective:
```
Select changes to apply:
[x] 1. Add frontmatter fields
[ ] 2. Fix header hierarchy
[x] 3. Add Related section
[ ] 4. Convert URLs

Enter numbers to toggle, 'done' to apply:
```

## Batch Mode

```
/improve-note 300-reference/code/ --frontmatter
```

Scans all notes in directory and fixes frontmatter only.
