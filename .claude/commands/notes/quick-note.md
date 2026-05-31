---
description: Quickly capture a thought or note to inbox
---

Quick capture to inbox for later processing.

## Input: $ARGUMENTS

Text to capture.

## Behavior

1. Create a new note in `100-inbox/`
2. Generate filename from first few words + timestamp
3. Mark as type: quick for easy filtering later

## Note Structure

```markdown
---
date: [TODAY]
week: [CURRENT_WEEK]
month: [YYYY-MM]
type: quick
status: captured
tags: [inbox]
updated: [TODAY]
---

# [Title from first line]

[Your content here]

---
*Captured: YYYY-MM-DD HH:MM*
```

## Filename Generation

From content: "Found useful pandas trick for filtering"
→ `100-inbox/2024-01-15-pandas-trick-filtering.md`

## Examples

```bash
# Quick thought
/quick-note Realized the batch effect might be due to different RNA extraction dates

# Code snippet
/quick-note Found useful pandas trick: df.query("col > 5")

# Task idea
/quick-note Need to add error handling to DMS parser
```

## Output

```
Captured to inbox:

[[2024-01-15-batch-effect-rna-extraction]]
→ 100-inbox/2024-01-15-batch-effect-rna-extraction.md

Type: quick | Status: captured

---
Process later with /improve-note or /daily-note to organize.
```

## Processing Quick Notes

Find all quick captures:
```bash
/find-notes --type quick
```

Or process inbox:
```bash
/daily-note 100-inbox/  # Organize all inbox items
```
