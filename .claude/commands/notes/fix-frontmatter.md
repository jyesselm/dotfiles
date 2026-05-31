---
description: Quick fix frontmatter on one or more notes
---

Quickly standardize and complete frontmatter on notes.

## Input: $ARGUMENTS

- Note path, title, or directory (required)
- Optional: `--dry-run` - show changes without applying
- Optional: `--force` - overwrite existing fields

## Standard Frontmatter Schema

```yaml
---
date: YYYY-MM-DD          # Required: creation date
week: YYYY-[W]WW          # Auto-calculated
month: YYYY-MM            # Auto-calculated
type: <type>              # Required: note type
status: <status>          # Required: draft/active/archive
tags: [list]              # Recommended
updated: YYYY-MM-DD       # Auto-set to today
---
```

## Type-Specific Fields

### ref/code
```yaml
language: python
code-tags: [cli, async]
packages: [pandas, numpy]
source: /path/to/file.py
```

### ref/paper
```yaml
authors: [Author1, Author2]
year: 2024
journal: Nature
doi: 10.1234/example
```

### research
```yaml
project: project-name
hypothesis:
status: active/completed
```

### meeting
```yaml
attendees: [Person1, Person2]
project: related-project
```

### protocol
```yaml
category: wet-lab/computational
version: 1.0
last-tested: YYYY-MM-DD
```

## Auto-Detection Rules

**Date extraction:**
1. From filename: `2024-01-15-note-title.md` → `2024-01-15`
2. From existing frontmatter
3. From file modification time
4. Default: today

**Type inference:**
| Pattern | Type |
|---------|------|
| `def `, `class `, `import ` | ref/code |
| `doi:`, `journal`, `abstract` | ref/paper |
| `## Step`, `## Procedure` | howto |
| `## Attendees`, `## Agenda` | meeting |
| `## Hypothesis`, `## Experiment` | research |

**Tag inference:**
- Scan H2 headers
- Extract from code block languages
- Identify tool/package names
- Domain keywords (RNA, DMS, etc.)

## Process

1. Read note(s)
2. Parse existing frontmatter
3. Detect missing/incorrect fields
4. Infer values from content
5. Show diff
6. Apply if confirmed

## Output Format

### Single Note
```
## Frontmatter Fix: [[note-title]]

Current:
---
date: 2024-01-15
---

Proposed:
---
date: 2024-01-15
week: 2024-W03
month: 2024-01
type: ref/code
status: active
language: python
tags: [analysis, dms]
packages: [pandas, numpy]
updated: 2024-01-20
---

Apply? [y/n]
```

### Directory Batch
```
## Frontmatter Fix: 300-reference/code/

Scanning 15 notes...

| Note | Missing Fields | Action |
|------|----------------|--------|
| note1.md | type, tags | Will add |
| note2.md | week, month | Will add |
| note3.md | (complete) | Skip |
| note4.md | type, status | Will add |

Fix 12 notes? [y/n/review each]
```

## Examples

```bash
# Fix single note
/fix-frontmatter 300-reference/code/dms-normalize.md

# Preview changes without applying
/fix-frontmatter my-note.md --dry-run

# Fix all notes in folder
/fix-frontmatter 300-reference/code/

# Force overwrite existing type
/fix-frontmatter my-note.md --force
```
