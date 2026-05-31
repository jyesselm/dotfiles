---
description: Create a new research note in Obsidian with proper frontmatter
---

Create a new research note in the Obsidian vault. Use the obsidian MCP tools.

## Input: $ARGUMENTS

Parse the arguments to extract:
- Topic/title (required)
- Project folder (default: 200-projects/210_active)
- Tags (optional)

## Note Structure

Create a note with this format:

```markdown
---
date: [TODAY]
week: [CURRENT_WEEK in YYYY-[W]WW format]
month: [YYYY-MM]
type: research
status: active
project: [infer from topic]
tags: [provided or infer]
updated: [TODAY]
---

# [Title]

## Context
[Why this research matters]

## Question
[Specific research question]

## Approach
- [ ] Step 1
- [ ] Step 2

## Notes
[Space for ongoing notes]

## Results
[Space for results]

## Next Steps
- [ ]

## Related
- [[link to related notes]]
```

## Workflow

1. Parse arguments for title and optional metadata
2. Generate filename in kebab-case: `YYYY-MM-DD-title.md`
3. Determine appropriate folder (210_active for new research)
4. Create note using `mcp__obsidian__write_note`
5. Confirm creation and provide the path
