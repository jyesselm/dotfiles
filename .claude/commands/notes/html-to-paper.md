---
description: Convert a saved HTML paper webpage into an Obsidian paper note
---

Convert a saved HTML file from a journal website into a structured Obsidian paper note.

## Input: $ARGUMENTS

- Path to an HTML file (required) - a saved webpage from a journal publisher

## Important: Publisher-Specific Skills

Different publishers use different HTML structures. Use the appropriate skill:

| Publisher | Skill | How to Identify |
|-----------|-------|-----------------|
| **Oxford Academic** (NAR, etc.) | `/nar-html-to-paper` | URL contains `academic.oup.com` or title ends with `| Oxford Academic` |
| Nature | TBD | URL contains `nature.com` |
| Science/AAAS | TBD | URL contains `science.org` |
| Cell Press | TBD | URL contains `cell.com` |
| Elsevier/ScienceDirect | TBD | URL contains `sciencedirect.com` |
| Wiley | TBD | URL contains `wiley.com` |
| PNAS | TBD | URL contains `pnas.org` |
| PLoS | TBD | URL contains `plos.org` |
| bioRxiv/medRxiv | TBD | URL contains `biorxiv.org` or `medrxiv.org` |
| ACS Publications | TBD | URL contains `pubs.acs.org` |

## Auto-Detection

When this skill is invoked, first detect the publisher:

1. Check the filename for publisher hints (e.g., `| Oxford Academic`)
2. Search HTML for `og:site_name` or `citation_publisher` meta tags
3. Look for characteristic URL patterns in `og:url` or `canonical` link

Then delegate to the appropriate publisher-specific skill.

## Example

```bash
# This will auto-detect Oxford Academic and use nar-html-to-paper
/html-to-paper "/Users/name/Downloads/Paper Title | NAR | Oxford Academic.html"
```

## Adding New Publishers

To support a new publisher:

1. Save an example HTML file from that publisher
2. Examine the HTML structure:
   - How is metadata stored? (meta tags, JSON-LD, etc.)
   - How are sections structured? (classes, IDs, semantic HTML)
   - How are citations formatted?
3. Create a new skill: `/notes/PUBLISHER-html-to-paper.md`
4. Add to the table above

## Common Meta Tag Patterns

Most publishers use some variant of these:

```html
<!-- Dublin Core / Citation tags -->
<meta name="citation_title" content="...">
<meta name="citation_author" content="...">
<meta name="citation_doi" content="...">
<meta name="citation_journal_title" content="...">
<meta name="citation_publication_date" content="...">

<!-- Open Graph -->
<meta property="og:title" content="...">
<meta property="og:description" content="...">
<meta property="og:url" content="...">

<!-- JSON-LD (structured data) -->
<script type="application/ld+json">
{
  "@type": "ScholarlyArticle",
  "headline": "...",
  "author": [...],
  ...
}
</script>
```

## Output Format

All publisher skills should output notes with consistent structure:

```yaml
---
title: [Paper title]
date: [Today]
week: [Current week]
month: [Current month]
type: ref/paper
status: active
authors: [wikilinked author list]
year: [Publication year]
journal: [Journal name]
doi: [DOI]
source: [URL]
science-tags: [inferred tags]
updated: [Today]
---
```
