---
name: format-lecture
description: Format and enhance lecture notes for CHEM 114 with proper style, slide annotations, worked examples, and math verification. Use when updating or creating lecture notes.
---

# Format Lecture Skill

Use this skill to format lecture notes in the established CHEM 114 style. This skill will:
1. Update frontmatter to match the standard format
2. Add navigation links and structure
3. Annotate slides with key talking points and transitions
4. Add detailed worked examples with step-by-step solutions
5. Verify all math calculations using Python
6. Add lecture summary and common mistakes sections

---

## How to Use

Invoke with: `/format-lecture <lecture-file-path>`

Example: `/format-lecture lecture-09-colligative-properties.md`

---

## Standard Lecture Note Format

### 1. Frontmatter (Required)

```yaml
---
type: teaching
course: chem-114
semester: 2026-spring
lecture: [number]
title: "[Lecture Title]"
date: [YYYY-MM-DD]
status: active
teaching-tags: [array of relevant tags]
---
```

### 2. Navigation (Required)

```markdown
< [[previous-lecture]] | [[next-lecture]] >

schedule: [[2026-chem-114-schedule]]

# Lecture X: [Title]
```

### 3. Lecture Planning Section (Required)

```markdown
---

## Lecture Planning

> [!info] Coverage Goals
> **Must cover:**
> - Topic 1
> - Topic 2
>
> **Key equations:**
> - Equation 1
> - Equation 2
```

### 4. Announcements Section

```markdown
---

# Announcements

**draw in different colors**
- Reminder 1
- Reminder 2
```

### 5. Content Sections

Use clear part headers:
```markdown
---

# Part 1: [Topic Name]

## [Subtopic]
```

---

## Slide Annotation Format

After each image/slide, add a callout with:
- 1-2 key teaching points
- Transition to next topic
- Optional student engagement question

```markdown
![[slide-image.png]]

> [!note] Key Point to Emphasize
> **Main point:** [What to emphasize when showing this slide]
>
> **Transition:** "Now let's look at..."
```

Or use other callout types:
- `>[!tip]` - For helpful hints
- `>[!important]` - For critical concepts
- `>[!warning]` - For common mistakes
- `>[!question]` - For discussion questions

---

## Worked Example Format

Follow this structure for ALL examples:

```markdown
## Worked Example X: [Descriptive Title]

**Problem:** [Full problem statement]

**Given:**
- Variable 1 = value
- Variable 2 = value

**Find:** [What we're solving for]

### Solution

**Step 1:** [Description of step]
$$[equation]$$

**Step 2:** [Description of step]
$$[equation]$$

[Continue steps...]

$$\boxed{[Final Answer with units]}$$

> [!tip] Reality Check
> [Explain why answer makes sense or compare to known value]
```

---

## Math Verification

**ALWAYS verify calculations using Python before finalizing.**

Run a Python script to check all numerical answers:

```python
# Example verification
import math

# Problem setup
given_value = 1.5
result = given_value * 2
print(f"Result: {result}")
```

Include verification for:
- Unit conversions
- Multi-step calculations
- Final answers

---

## Required Sections Checklist

- [ ] Frontmatter with proper fields
- [ ] Navigation links (prev/next lecture)
- [ ] Schedule link
- [ ] Lecture Planning callout
- [ ] Announcements section
- [ ] Part headers with `---` dividers
- [ ] Slide annotations with callouts
- [ ] Worked examples with step-by-step solutions
- [ ] Practice problems section
- [ ] Common Mistakes to Avoid section
- [ ] Lecture Summary callout

---

## Lecture Summary Format

```markdown
---

# Lecture Summary

> [!summary] Today We Covered
> 1. **Topic 1:** Brief description
> 2. **Topic 2:** Brief description
> 3. **Topic 3:** Brief description

> [!important] Key Takeaways
> - Takeaway 1
> - Takeaway 2
> - Takeaway 3

**Next lecture:** [Preview of next topic]
```

---

## Common Mistakes Section Format

```markdown
## Common Mistakes to Avoid

> [!warning] Watch Out!
>
> 1. **[Mistake category]**
>    - Explanation of mistake
>    - How to avoid it
>
> 2. **[Mistake category]**
>    - Explanation of mistake
>    - How to avoid it
```

---

## Example Tags for teaching-tags

Chemistry topics:
- `henrys-law`, `gas-solubility`, `vapor-pressure`
- `molarity`, `molality`, `mole-fraction`, `mass-percent`
- `enthalpy-of-solution`, `lattice-energy`, `hydration-enthalpy`
- `colligative-properties`, `boiling-point-elevation`, `freezing-point-depression`
- `intermolecular-forces`, `hydrogen-bonding`, `dispersion-forces`
- `unit-cells`, `crystalline-solids`, `braggs-law`

Always include `chem-114` as the first tag.

---

## Workflow

1. **Read the existing lecture note** to understand current content
2. **Read 1-2 nearby lectures** to match style consistency
3. **Update frontmatter** to standard format
4. **Add navigation** and structure sections
5. **Annotate each slide** with teaching points
6. **Expand or add worked examples** with full step-by-step solutions
7. **Verify all math** using Python
8. **Add missing sections** (summary, common mistakes, practice problems)
9. **Review and finalize**

---

## Reference: Callout Types

| Callout | Use For |
|---------|---------|
| `>[!info]` | Coverage goals, neutral information |
| `>[!note]` | Teaching points, slide annotations |
| `>[!tip]` | Helpful hints, memory aids, reality checks |
| `>[!important]` | Critical concepts, key takeaways |
| `>[!warning]` | Common mistakes, things to avoid |
| `>[!example]` | Worked examples, solutions |
| `>[!question]` | Discussion questions for students |
| `>[!summary]` | Lecture summaries |
