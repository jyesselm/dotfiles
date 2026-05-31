---
description: Create a how-to guide or tutorial note
---

Create a structured how-to guide in Obsidian.

## Input: $ARGUMENTS

- Topic/title of the how-to guide
- Optional: category (python, bash, lab, analysis, etc.)

## Note Structure

```markdown
---
date: [TODAY]
week: [CURRENT_WEEK]
month: [YYYY-MM]
type: howto
status: draft
category: [specified or inferred]
difficulty: [beginner/intermediate/advanced]
time-estimate: [if applicable]
tags: [howto, category]
updated: [TODAY]
---

# How to [Title]

## Overview
[Brief description of what this guide covers and why it's useful]

## Prerequisites
- [ ] Requirement 1
- [ ] Requirement 2

## Quick Reference
```[language]
# The essential command/code
```

## Step-by-Step Guide

### Step 1: [Title]
[Explanation]

```[language]
# Code or command
```

### Step 2: [Title]
[Explanation]

### Step 3: [Title]
[Explanation]

## Common Issues

| Problem | Solution |
|---------|----------|
| | |

## Tips
-

## See Also
- [[related howto]]
- [External resource](url)
```

## Category Detection

| Keywords | Category |
|----------|----------|
| pip, conda, venv | python/env |
| ssh, rsync, scp | remote |
| git, branch, merge | git |
| DMS, SHAPE, seq | analysis |
| PCR, gel, prep | lab |

## Workflow

1. Parse title and optional category
2. Infer category from keywords if not specified
3. Generate filename: `howto-title.md`
4. Save to `300-reference/howto/`
5. Return path
