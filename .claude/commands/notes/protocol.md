---
description: Create or update a lab protocol document
---

Create a detailed lab protocol in Obsidian. Use the obsidian MCP tools.

## Input: $ARGUMENTS

- Protocol name/topic
- Optional: reference to existing protocol to update

## Protocol Structure

```markdown
---
date: [TODAY]
week: [CURRENT_WEEK]
month: [YYYY-MM]
type: protocol
status: draft
category: [wet-lab/computational/analysis]
author: Joe Yesselman
version: 1.0
last-tested:
tags: []
updated: [TODAY]
---

# [Protocol Name]

## Purpose
[Brief description of what this protocol accomplishes]

## Materials

### Reagents
| Reagent | Concentration | Volume | Vendor | Cat # |
|---------|--------------|--------|--------|-------|
| | | | | |

### Equipment
- [ ] Item 1
- [ ] Item 2

### Computational Requirements
- Software:
- Data inputs:

## Before You Start
- [ ] Preparation step 1
- [ ] Preparation step 2

## Procedure

### Day 1: [Description]

1. **Step 1** (estimated time: X min)
   - Detail
   - Detail

   > **Note:** Important consideration

2. **Step 2** (estimated time: X min)
   - Detail

### Day 2: [Description]
...

## Expected Results
[What should you see if it worked?]

## Troubleshooting

| Problem | Possible Cause | Solution |
|---------|---------------|----------|
| | | |

## Quality Control
- [ ] QC check 1
- [ ] QC check 2

## Data Analysis
[How to analyze the results]

## References
- [[related protocol]]
- Paper citation

## Revision History
| Version | Date | Changes | Author |
|---------|------|---------|--------|
| 1.0 | [TODAY] | Initial version | JY |
```

## Workflow

1. Parse protocol name from arguments
2. Determine category (wet-lab/computational/analysis)
3. Generate filename: `protocol-name.md`
4. Save to appropriate location
5. If updating, read existing and preserve revision history
