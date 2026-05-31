---
description: Save a code snippet as a reusable reference note
---

Create a code snippet reference note in Obsidian.

## Input: $ARGUMENTS

Either:
- Description of snippet to create
- OR file:line range to extract (e.g., `src/utils.py:45-60`)
- OR clipboard content description

## Note Structure

```markdown
---
date: [TODAY]
week: [CURRENT_WEEK]
month: [YYYY-MM]
type: ref/code
status: active
language: [detected]
code-tags: [inferred]
packages: [if any imports detected]
source: [file path if extracted]
updated: [TODAY]
---

# [Descriptive Title]

## Purpose
[What this snippet does and when to use it]

## Code

```[language]
[the code]
```

## Usage Example

```[language]
[example of how to use it]
```

## Parameters
| Name | Type | Description |
|------|------|-------------|
| | | |

## Notes
- [Any gotchas or important details]

## Related
- [[similar snippets]]
```

## Smart Detection

When extracting from a file:
1. Read the specified lines
2. Detect language from extension
3. Parse imports for packages
4. Extract function/class name for title
5. Infer tags from content

## Workflow

1. Get code (from args, file, or ask)
2. Detect/confirm language
3. Generate descriptive title
4. Create frontmatter with detected metadata
5. Save to `300-reference/snippet/`
6. Return path
