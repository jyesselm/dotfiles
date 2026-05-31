---
description: Create a meeting note with attendees, agenda, and action items
---

Create a structured meeting note in Obsidian.

## Input: $ARGUMENTS

- Meeting topic/title (required)
- Optional: attendees
- Optional: project link

## Note Structure

```markdown
---
date: [TODAY]
week: [CURRENT_WEEK]
month: [YYYY-MM]
type: meeting
status: active
attendees: [list]
project: [if specified]
tags: [meeting]
updated: [TODAY]
---

# [Meeting Title] - [DATE]

## Attendees
- [ ] Person 1
- [ ] Person 2

## Agenda
1. Topic 1
2. Topic 2

## Discussion Notes

### [Topic 1]
-

### [Topic 2]
-

## Decisions Made
-

## Action Items

| Task | Owner | Due |
|------|-------|-----|
| | | |

## Follow-up
- [ ] Schedule next meeting
- [ ]

## Related
- [[project link]]
```

## Workflow

1. Parse meeting title and optional attendees
2. Generate filename: `YYYY-MM-DD-meeting-title.md`
3. Create note in `000-journals/` or specified location
4. Return path for easy access
