---
description: Quickly capture a research or project idea
---

Capture an idea quickly before it's lost.

## Input: $ARGUMENTS

The idea description (can be rough/informal).

## Note Structure

```markdown
---
date: [TODAY]
week: [CURRENT_WEEK]
month: [YYYY-MM]
type: idea
status: captured
priority: [tbd]
effort: [tbd]
tags: [idea]
updated: [TODAY]
---

# [Idea Title - extracted from first line]

## The Idea
[Full description from input]

## Why It Matters
[Space to fill in later]

## Initial Thoughts
-

## Questions to Answer
- [ ]

## Next Steps
- [ ] Evaluate feasibility
- [ ]

## Related
- [[]]
```

## Quick Capture

The command is designed for speed:
- Just type the idea, no formatting needed
- Title is extracted from first sentence
- Minimal required fields
- Everything else can be filled in later

## Examples

```
/idea-note What if we used graph neural networks to predict RNA tertiary contacts from DMS data?
```

Creates note with:
- Title: "GNN for RNA tertiary contacts from DMS"
- Full text in "The Idea" section
- Tagged for later review

## Workflow

1. Extract title from first sentence (truncate if long)
2. Generate filename: `YYYY-MM-DD-idea-short-title.md`
3. Save to `200-projects/240_ideas/`
4. Return path
5. Optionally suggest related existing notes
