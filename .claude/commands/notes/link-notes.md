---
description: Add links between related Obsidian notes
---

Find and add links between related notes in the vault.

## Input: $ARGUMENTS

- Note path or title to add links to
- Optional: `--auto` to automatically find and add links
- Optional: `--suggest` to only suggest without modifying

## Modes

### Auto-Link
```
/link-notes 300-reference/code/dms-normalization.md --auto
```
Scans vault for related notes and adds to "Related" section.

### Suggest Only
```
/link-notes dms-normalization --suggest
```
Shows potential links without modifying the note.

### Manual Add
```
/link-notes dms-normalization --add "[[shape-analysis]]" "[[reactivity-qc]]"
```
Adds specific links to the note.

## Link Discovery

Finds related notes by:
1. **Shared tags** - Notes with overlapping tags
2. **Title similarity** - Notes with similar titles
3. **Content overlap** - Notes mentioning similar terms
4. **Backlinks** - Notes already linking to this one

## Process

1. Read the target note
2. Extract keywords, tags, and topics
3. Search vault for related notes using `mcp__obsidian__search_notes`
4. Rank by relevance
5. Add links or show suggestions

## Output Format

### Suggest Mode
```
## Link Suggestions for [[note-title]]

### Strong Matches (shared tags + content)
- [[related-note-1]] - shares tags: python, analysis
- [[related-note-2]] - mentions: DMS, normalization

### Possible Matches (content similarity)
- [[related-note-3]] - similar topic
- [[related-note-4]] - references same paper

### Backlinks (already link here)
- [[note-that-links-here]]

Add these? [y/n/select]
```

### Auto Mode
```
Added 3 links to [[note-title]]:
- [[related-note-1]]
- [[related-note-2]]
- [[note-that-links-here]] (backlink)
```

## Workflow

1. Parse target note path
2. Read note content and frontmatter
3. Search for related notes
4. Either suggest or auto-add to "Related" or "See Also" section
5. Report changes
