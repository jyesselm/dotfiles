---
description: Organize a daily note and distribute content to proper standalone notes
---

Process a daily note and extract content into well-formatted standalone notes.

## Input: $ARGUMENTS

- Date or path to daily note (default: today)
- Optional: `--dry-run` - show suggestions without creating notes
- Optional: `--interactive` - process each item one by one

## Process Overview

1. **Read** the daily note
2. **Analyze** content sections
3. **Categorize** each item
4. **Suggest** appropriate note types and locations
5. **Create** standalone notes
6. **Update** daily note with links to new notes

## Content Detection

Scans daily note for extractable content:

| Pattern | Suggested Note Type | Destination |
|---------|---------------------|-------------|
| Code blocks with explanation | `/code-snippet` | 300-reference/snippet/ |
| Meeting notes, attendees | `/meeting-note` | 000-journals/ |
| "Idea:", "What if", hypothesis | `/idea-note` | 200-projects/240_ideas/ |
| Step-by-step instructions | `/howto-note` | 300-reference/howto/ |
| Paper/article discussion | `/paper-notes` | 300-reference/science/ |
| Research findings, data | `/research-note` | 200-projects/210_active/ |
| TODO clusters on a topic | Project note | 200-projects/ |
| Problem + solution | `/howto-note` | 300-reference/howto/ |

## Analysis Output

```
## Daily Note Analysis: 2024-01-15

### Content Summary
- Total sections: 8
- Extractable items: 5
- Already linked: 2

### Suggested Extractions

#### 1. Code Snippet (lines 23-45)
**Content:** DMS normalization function
**Suggested title:** dms-boxplot-normalization
**Destination:** 300-reference/snippet/
**Tags:** python, dms, normalization
```python
def normalize_dms(values):
    # preview of code...
```
**Action:** [Create] [Skip] [Edit title]

---

#### 2. Research Note (lines 67-89)
**Content:** Observations about batch effects in DMS data
**Suggested title:** dms-batch-effect-observations
**Destination:** 200-projects/210_active/
**Tags:** dms, analysis, batch-effects
> "Noticed significant batch effects when comparing..."
**Action:** [Create] [Skip] [Edit title]

---

#### 3. Idea (lines 102-108)
**Content:** Use ML for reactivity prediction
**Suggested title:** ml-reactivity-prediction-idea
**Destination:** 200-projects/240_ideas/
> "What if we trained a model on DMS profiles to..."
**Action:** [Create] [Skip] [Edit title]

---

#### 4. Meeting Note (lines 120-156)
**Content:** Lab meeting discussion
**Suggested title:** 2024-01-15-lab-meeting
**Destination:** 000-journals/
**Attendees:** [detected: Alice, Bob, Carol]
**Action:** [Create] [Skip] [Edit title]

---

#### 5. How-To (lines 178-201)
**Content:** SSH tunnel setup for cluster
**Suggested title:** howto-ssh-tunnel-cluster
**Destination:** 300-reference/howto/
**Tags:** ssh, remote, cluster
**Action:** [Create] [Skip] [Edit title]

---

### Summary
- 5 notes ready to create
- Estimated cleanup: 60% of daily note content

Proceed? [all/select/skip]
```

## After Extraction

### Daily Note Updates

Replace extracted content with links:

**Before:**
```markdown
## Afternoon

Figured out the DMS normalization issue. Here's the code:
```python
def normalize_dms(values):
    q1, q3 = np.percentile(values, [25, 75])
    ...
```
This uses boxplot normalization which is better for...
```

**After:**
```markdown
## Afternoon

Figured out the DMS normalization issue.
→ Created [[dms-boxplot-normalization]]
```

### Extraction Report

```
## Extraction Complete

Created 5 notes:
1. [[dms-boxplot-normalization]] - 300-reference/snippet/
2. [[dms-batch-effect-observations]] - 200-projects/210_active/
3. [[ml-reactivity-prediction-idea]] - 200-projects/240_ideas/
4. [[2024-01-15-lab-meeting]] - 000-journals/
5. [[howto-ssh-tunnel-cluster]] - 300-reference/howto/

Daily note updated with links.

Original content preserved in:
→ 000-journals/daily/2024-01-15.md.bak (just in case)
```

## Interactive Mode

Process one item at a time:

```
Item 1/5: Code Snippet

Content preview:
```python
def normalize_dms(values):
    ...
```

Suggested: 300-reference/snippet/dms-boxplot-normalization.md

Options:
[c] Create with suggestions
[e] Edit title/location
[m] Merge with existing note
[s] Skip
[q] Quit (keep remaining in daily)

Choice:
```

## Merge Option

If similar note exists:

```
Found similar note: [[dms-normalization-methods]]

Options:
[a] Append to existing note
[n] Create new note anyway
[s] Skip
```

## Examples

```bash
# Process today's daily note
/daily-note

# Process specific date
/daily-note 2024-01-10

# Preview without creating
/daily-note --dry-run

# Step through each item
/daily-note --interactive

# Process yesterday
/daily-note yesterday
```
