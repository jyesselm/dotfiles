---
description: Import a markdown or text file into Obsidian with proper frontmatter
---

Convert any markdown or text file into a properly formatted Obsidian note.

## Input: $ARGUMENTS

- File path to import (required)
- Optional: destination folder in vault
- Optional: note type (ref/code, ref/paper, research, meeting, etc.)

## Process

1. **Read** the source file
2. **Analyze** content to infer metadata:
   - Detect language if code-heavy (python, cpp, bash, etc.)
   - Extract any existing title (first H1 or filename)
   - Identify key topics/tags
   - Detect if it's documentation, notes, or reference material
3. **Generate** appropriate frontmatter
4. **Transform** content if needed:
   - Ensure single H1 title
   - Fix relative links if applicable
   - Add sections if missing structure
5. **Save** to Obsidian vault using `mcp__obsidian__write_note`

## Frontmatter Template

```yaml
---
date: [TODAY]
week: [CURRENT_WEEK]
month: [YYYY-MM]
type: [inferred or specified]
status: active
source: [original file path]
language: [if code-related]
tags: [inferred from content]
updated: [TODAY]
---
```

## Type Detection

| Content Pattern | Inferred Type |
|-----------------|---------------|
| Code blocks, function refs | ref/code |
| Citations, abstracts | ref/paper |
| Meeting, attendees | meeting |
| TODO lists, goals | project |
| How-to, steps | howto |
| General notes | note |

## Destination Mapping

| Type | Default Location |
|------|------------------|
| ref/code | 300-reference/code/ |
| ref/paper | 300-reference/science/ |
| howto | 300-reference/howto/ |
| meeting | 000-journals/ |
| project | 200-projects/210_active/ |
| note | 100-inbox/ |

## Output

1. Show detected metadata
2. Ask for confirmation or adjustments
3. Create note in vault
4. Return the new note path
