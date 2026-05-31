---
description: Convert a saved NAR/Oxford Academic HTML paper into an Obsidian paper note
---

Convert a saved HTML file from **Nucleic Acids Research** or other **Oxford Academic** journals into a structured Obsidian paper note. This skill is specific to the Oxford Academic HTML structure.

## Input: $ARGUMENTS

- Path to an HTML file saved from Oxford Academic (NAR, NAR Genomics, etc.)

## Publisher-Specific Notes

**This skill is for Oxford Academic / NAR only.** Different publishers use different HTML structures:

| Publisher | Skill to Use | Notes |
|-----------|--------------|-------|
| Oxford Academic (NAR, etc.) | This skill | Uses `citation_*` meta tags, `class=chapter-para` paragraphs |
| Nature | TBD | Different structure |
| Science | TBD | Different structure |
| Cell Press | TBD | Different structure |
| Elsevier | TBD | Different structure |
| PNAS | TBD | Similar to Oxford |

## Oxford Academic HTML Structure

### Metadata Location

Oxford Academic stores metadata in `<meta>` tags with `citation_*` names:

```html
<meta name=citation_title content="Paper title">
<meta name=citation_author content="Last, First">
<meta name=citation_doi content="10.1093/nar/xxxxx">
<meta name=citation_journal_title content="Nucleic Acids Research">
<meta name=citation_publication_date content="2023/11/10">
```

Also check:
- `og:url` for source URL
- `og:description` for abstract preview

### Content Structure

Oxford Academic uses this pattern for article sections:

```html
<h2 class="abstract-title">Abstract</h2>
<section class="...">
  <p class=chapter-para>Abstract text...</p>
</section>

>Introduction</h2>
<p class=chapter-para>Introduction paragraph 1...</p>
<p class=chapter-para>Introduction paragraph 2...</p>
...
<h2>Results</h2>
```

**Key identifiers:**
- Section headings: `<h2>` tags containing section names
- Paragraphs: `<p class=chapter-para>` (note: unquoted attribute!)
- Citations: `<span class=xrefLink>` followed by `<a class="...xref-bibr...">number</a>`

## Extraction Process

### 1. Parse Metadata

```python
import re
from html import unescape

# Extract from citation_* meta tags
title = re.search(r'citation_title["\s]+content="([^"]+)"', content)
authors = re.findall(r'citation_author["\s]+content="([^"]+)"', content)
doi = re.search(r'citation_doi["\s]+content="([^"]+)"', content)
journal = re.search(r'citation_journal_title["\s]+content="([^"]+)"', content)
pub_date = re.search(r'citation_publication_date["\s]+content="([^"]+)"', content)
```

### 2. Extract Sections

For each section (Introduction, Results, Discussion, Methods):

```python
def extract_nar_section(content, heading):
    # Find heading position
    pattern = rf'>\s*{re.escape(heading)}\s*</h2>'
    match = re.search(pattern, content, re.IGNORECASE)
    if not match:
        return None

    start = match.end()

    # Find next h2 (end of section)
    next_section = re.search(r'<h2[^>]*>', content[start:])
    end = start + next_section.start() if next_section else len(content)

    section_html = content[start:end]
    return clean_html_to_markdown(section_html)
```

### 3. Clean HTML to Markdown

```python
def clean_html_to_markdown(text):
    # Remove scripts/styles
    text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL)

    # Convert citations [^1] format
    text = re.sub(r'<span class=xrefLink[^>]*></span><a[^>]*>(\d+)</a>', r'[^\1]', text)

    # Convert emphasis
    text = re.sub(r'<em>(.*?)</em>', r'*\1*', text)
    text = re.sub(r'<i>(.*?)</i>', r'*\1*', text)
    text = re.sub(r'<strong>(.*?)</strong>', r'**\1**', text)

    # Superscripts to unicode
    sup_map = {'0':'⁰','1':'¹','2':'²','3':'³','4':'⁴','5':'⁵','6':'⁶','7':'⁷','8':'⁸','9':'⁹','+':'⁺','-':'⁻'}
    # ... apply conversion

    # Paragraphs
    text = re.sub(r'<p\s+class=chapter-para>', '\n\n', text)
    text = re.sub(r'<p[^>]*>', '\n\n', text)

    # Remove remaining tags
    text = re.sub(r'<[^>]+>', '', text)

    # Clean entities
    text = unescape(text)

    return text.strip()
```

### 3.5 Handle Equations (MathML)

NAR papers contain equations as MathML `<math>` blocks. When text is extracted, these become linearized and concatenated to paragraph endings.

**Pattern:** Text ends with equation reference, followed by linearized MathML text and `(N)`:
```
...using Equation ([^2]) using *meltR.F*.ln(KD)=\xa0ΔS′R−\xa0ΔH′RT(2)
```

**Detection and formatting:**
```python
import re

def format_equations(text):
    """Separate equations from paragraph text and format them."""

    # Pattern: equation reference followed by inline equation ending with (N)
    # The \xa0 is non-breaking space commonly found in NAR equations
    pattern = r'(\]\)[.\s]*|\.)\s*([A-Za-z]+[=<>≤≥][\s\xa0]*[^\n]+)\((\d+)\)\s*$'

    def replacement(match):
        before = match.group(1)  # ] or .
        eq_text = match.group(2).strip()
        eq_num = match.group(3)
        # Format equation on its own line as code block
        return f'{before}\n\n`{eq_text}`  *(Equation {eq_num})*'

    # Apply to each line that might have an equation
    lines = text.split('\n')
    result = []
    for line in lines:
        if re.search(r'\(\d+\)\s*$', line):  # Line ends with (N)
            line = re.sub(pattern, replacement, line, flags=re.MULTILINE)
        result.append(line)

    return '\n'.join(result)
```

**Common equation patterns to detect:**
- Thermodynamic: `ΔG°₃₇ = ...`, `ln(K_D) = ...`
- Statistical: `Weight = ...`, `Accuracy = ...`
- Kinetic: `F = F_max + ...`

**Note:** Equations often contain `\xa0` (non-breaking space) characters from MathML conversion. Include these in pattern matching.

### 4. Generate Frontmatter

```yaml
---
title: [Paper title - clean]
date: YYYY-MM-DD           # Today
week: YYYY-Www
month: YYYY-MM
type: ref/paper
status: active
authors:
  - "[[First Author]]"
  - "[[Second Author]]"
year: YYYY                 # Publication year
journal: Nucleic Acids Research
doi: 10.1093/nar/xxxxx
source: https://doi.org/10.1093/nar/xxxxx
science-tags:
  - [inferred tags]
updated: YYYY-MM-DD
---
```

### 5. Infer Science Tags

| Content Pattern | Tag |
|-----------------|-----|
| thermodynamic, stability, ΔG | methods/thermodynamics |
| nearest neighbor, NNP | methods/nearest-neighbor |
| DMS, SHAPE, chemical probing | methods/chemical-probing |
| in vivo, cellular, cells | biology/in-vivo |
| RNA structure, secondary structure | rna/structure |
| Mg²⁺, magnesium | biochemistry/metal-ions |
| E. coli, Escherichia | organisms/e-coli |
| transcriptome, mRNA | rna/mrna |
| FRET, fluorescence | methods/fluorescence |
| crystallography, X-ray | methods/crystallography |
| NMR | methods/nmr |
| cryo-EM | methods/cryo-em |

### 6. Extract Figures

NAR embeds figures as base64 data URIs in saved HTML files:

```html
<div class="fig-section" data-id="F1">
  <img src="data:image/jpeg;base64,/9j/4AAQ...">
  <div class="caption">
    <p class="chapter-para">Figure 1. Caption text...</p>
  </div>
</div>
```

**Extraction process:**

```python
import base64
import os

# Create attachments directory
img_dir = "300-reference/science/papers/attachments/YYYY-author-short"
os.makedirs(img_dir, exist_ok=True)

# Find figure sections
fig_pattern = r'<div[^>]*class="[^"]*fig-section[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>'
for i, match in enumerate(re.finditer(fig_pattern, content, re.DOTALL)):
    section = match.group(0)

    # Extract base64 image
    img_match = re.search(r'src="data:image/(\w+);base64,([^"]+)"', section)
    if img_match:
        img_type = img_match.group(1)  # jpeg, png, etc.
        img_data = img_match.group(2)

        # Save image file
        with open(f"{img_dir}/figure-{i+1}.{img_type}", 'wb') as f:
            f.write(base64.b64decode(img_data))

    # Extract caption
    cap_match = re.search(r'<div class="?caption[^>]*>.*?<p[^>]*>(.*?)</p>', section, re.DOTALL)
    caption = clean_text(cap_match.group(1)) if cap_match else ""
```

### 7. Extract Tables

NAR uses `<div class="table-wrap">` with **unclosed HTML tags** (valid HTML5):

```html
<div class="table-wrap">
  <span class="label">Table 1.</span>
  <div class="caption"><p class="chapter-para">Caption...</p></div>
  <table>
    <thead><tr><th>Col1<th>Col2<th>Col3  <!-- No closing </th> tags! -->
    <tbody><tr><td>A<td>B<td>C           <!-- No closing </td> or </tr>! -->
  </table>
</div>
```

**Extraction process:**

```python
# Find tables by "Table N." label
table_pattern = r'<div class="table-wrap[^"]*"[^>]*>.*?Table (\d+)\.</span>.*?</table>'
seen_labels = set()

for match in re.finditer(table_pattern, content, re.DOTALL):
    table_num = match.group(1)
    if f"Table {table_num}" in seen_labels:
        continue  # Skip duplicate (NAR shows tables twice)
    seen_labels.add(f"Table {table_num}")

    section = match.group(0)

    # Extract headers - split by <th> since no closing tags
    headers = []
    thead_match = re.search(r'<thead>(.*?)<tbody>', section, re.DOTALL)
    if thead_match:
        for part in thead_match.group(1).split('<th>')[1:]:
            full_text = part.split('<span aria-hidden')[0]  # Stop before hidden spans
            headers.append(clean_text(full_text))

    # Extract rows - split by <tr> and <td>
    rows = []
    tbody_idx = section.find('<tbody>')
    if tbody_idx > 0:
        tbody = section[tbody_idx:section.find('</table>')]
        for tr in tbody.split('<tr>')[1:]:
            cells = [clean_text(td.split('<')[0]) for td in tr.split('<td>')[1:]]
            if cells:
                rows.append(cells)

    # Convert to markdown table
    md_lines = ['| ' + ' | '.join(headers) + ' |']
    md_lines.append('|' + ':---|' * len(headers))
    for row in rows:
        md_lines.append('| ' + ' | '.join(row[:len(headers)]) + ' |')
```

### 8. Structure the Note

```markdown
# [Paper Title]

## Summary
> [2-3 sentence AI-generated summary]

## Key Findings
1. **[Finding 1]**: [Brief explanation]
2. **[Finding 2]**: [Brief explanation]
3. **[Finding 3]**: [Brief explanation]

## Abstract
[Full abstract]

## Introduction
[Full introduction with citations as [^1] footnotes]

## Results
[Full results]

## Discussion
[Full discussion]

## Materials and Methods
[Full methods]

## Data Availability
[Data/code links]

## Funding
[Funding info]

## Figures

### Figure 1
![Figure 1](attachments/YYYY-author-short/figure-1.jpeg)
**Caption**: [Figure caption text]

### Figure 2
...

## Tables

### Table 1
**[Table caption]**
| Header1 | Header2 | Header3 |
|:---|:---|:---|
| Data | Data | Data |

## Relevance to My Work
*[User fills in]*

## Follow-up
- [ ] [Tasks]

## Related Notes
- [[]]
```

### 9. Save the Note

1. Generate filename: `YYYY-firstauthor-short-title.md`
2. Copy content to `300-reference/science/papers/`
3. Add frontmatter via `mcp__obsidian__update_frontmatter`

## Example Usage

```bash
/nar-html-to-paper "/Users/jyesselman2/Downloads/Paper Title | NAR | Oxford Academic.html"
```

## Output

```
## Paper Note Created: NAR

**File**: 300-reference/science/papers/2023-sieg-in-vivo-nearest-neighbor-parameters.md

### Metadata
- Title: In vivo-like nearest neighbor parameters...
- Authors: 5 (Sieg, Jolley, Huot, Babitzke, Bevilacqua)
- Journal: Nucleic Acids Research
- Year: 2023
- DOI: 10.1093/nar/gkad807

### Sections Extracted
- [x] Abstract (1,303 chars)
- [x] Introduction (10,046 chars)
- [x] Results (47,623 chars)
- [x] Discussion (13,401 chars)
- [x] Methods (19,152 chars)
- [x] Data Availability
- [x] Funding

### Figures Extracted
- [x] Figure 1 (76 KB) - FDBI thermodynamic characterization
- [x] Figure 2 (86 KB) - NN model adjustments
- [x] Figure 3 (92 KB) - Structure prediction benchmarks
- [x] Figure 4 (72 KB) - Chemical probing validation
Saved to: attachments/2023-sieg-nar/

### Tables Extracted
- [x] Table 1: Thermodynamic analysis (25 rows × 10 cols)
- [x] Table 2: Nearest neighbor parameters (14 rows × 10 cols)
- [x] Table 3: Structure prediction results (24 rows × 5 cols)

### Tags Inferred
methods/thermodynamics, methods/nearest-neighbor, methods/chemical-probing,
biology/in-vivo, rna/structure, biochemistry/metal-ions, organisms/e-coli

Total: ~106 KB (including figures section)
```

## Troubleshooting

**No metadata found**: Check that the HTML is from Oxford Academic. Other publishers use different meta tag formats.

**Sections empty**: The HTML structure may have changed. Look for `<p class=chapter-para>` patterns.

**Large file issues**: If the note is >100KB, the MCP write may fail. Use bash to copy the file directly to the vault, then update frontmatter with MCP.

**Figures not extracted**:
- Figures are embedded as base64 data URIs when you "Save As" the HTML from browser
- If images show as external URLs, the HTML was saved without images - re-save with "Save As Complete Webpage"
- Look for `<div class="fig-section">` patterns

**Tables incomplete**:
- NAR uses unclosed HTML tags (`<th>`, `<td>`, `<tr>` without closing tags)
- Use string splitting instead of regex for tag matching
- Tables appear twice in NAR HTML (normal + mobile view) - deduplicate by label

**Duplicate content**:
- NAR HTML includes sidebar content with other paper titles
- Make sure to extract only content between section headings
- Stop extraction at `<div class="widget-SocialShareOptions"` or similar

**Equations concatenated to paragraphs**:
- MathML equations get linearized when HTML text is extracted
- Pattern: paragraph ends with `...Equation ([^N]).EQUATION_TEXT(N)`
- Contains `\xa0` (non-breaking space) characters - include in regex patterns
- Solution: Use `format_equations()` function to detect and separate
- Manual fix: Search for lines ending with `(N)` where N is a number
