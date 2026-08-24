---
name: docx
description: Comprehensive Word document (.docx) creation, editing, and analysis with support for tracked changes, comments, formatting preservation, and text extraction.
---

# DOCX Skill

Use this skill when working with Word documents (.docx files) for creating new documents, modifying or editing content, working with tracked changes, adding comments, or any other document tasks.

A .docx file is essentially a ZIP archive containing XML files and other resources. You have different tools and workflows available for different tasks.

## Workflows

### Reading/Analyzing Documents

**For text extraction:** Convert the document to markdown using pandoc:
```bash
pandoc input.docx -o output.md
```

Pandoc provides excellent support for preserving document structure and can show tracked changes with:
```bash
pandoc input.docx -o output.md --track-changes=all
```

**For raw XML access** (comments, complex formatting, metadata, embedded media):
```bash
# Unpack the docx
unzip document.docx -d document_unpacked/

# Main content is in:
# document_unpacked/word/document.xml
```

---

### Creating New Documents

Use the `docx` npm package (JavaScript/TypeScript) to create documents programmatically.

**Install:**
```bash
npm install docx
```

**Basic example:**
```javascript
const { Document, Paragraph, TextRun, Packer } = require('docx');
const fs = require('fs');

const doc = new Document({
  sections: [{
    properties: {},
    children: [
      new Paragraph({
        children: [
          new TextRun("Hello World"),
          new TextRun({
            text: " - Bold text",
            bold: true
          })
        ]
      })
    ]
  }]
});

Packer.toBuffer(doc).then((buffer) => {
  fs.writeFileSync("output.docx", buffer);
});
```

**Key components:**
- `Document` - The main document container
- `Paragraph` - A paragraph of text
- `TextRun` - A run of text with consistent formatting
- `Table`, `TableRow`, `TableCell` - For tables
- `ImageRun` - For images
- `Header`, `Footer` - Document headers/footers

---

### Editing Existing Documents

For editing existing documents, use Python with the `python-docx` library or direct XML manipulation.

**Using python-docx:**
```bash
pip install python-docx
```

```python
from docx import Document

doc = Document('input.docx')

# Access paragraphs
for para in doc.paragraphs:
    print(para.text)

# Modify text
doc.paragraphs[0].text = "New text"

doc.save('output.docx')
```

**For complex edits (tracked changes, comments):** Use direct OOXML manipulation:

```bash
# Unpack
unzip document.docx -d doc_unpacked/

# Edit word/document.xml with Python/script

# Repack
cd doc_unpacked && zip -r ../modified.docx . && cd ..
```

---

### Tracked Changes (Redlining)

For professional documents requiring tracked changes:

1. **Convert to markdown first** to identify all needed changes:
   ```bash
   pandoc input.docx -o review.md --track-changes=all
   ```

2. **Organize changes into batches** (3-10 changes per batch) by section, type, or complexity

3. **Implement using XML edits:**
   - Insertions use `<w:ins>` tags
   - Deletions use `<w:del>` tags
   - Only mark text that actually changed (preserve unchanged text)

4. **Verify after completion:**
   ```bash
   pandoc modified.docx -o verify.md --track-changes=all
   ```

**Critical principle:** Make minimal, precise edits. Break replacements into segments:
- Unchanged text (reuse original `<w:r>` elements)
- Deletion (`<w:del>`)
- Insertion (`<w:ins>`)
- Unchanged text

---

### Visual Analysis

Convert documents to images for visual inspection:

```bash
# DOCX -> PDF -> Images
libreoffice --headless --convert-to pdf document.docx
pdftoppm -jpeg -r 150 document.pdf page
```

---

## Required Tools

| Tool | Purpose | Install |
|------|---------|---------|
| pandoc | Document conversion | `brew install pandoc` |
| docx (npm) | Create new documents | `npm install docx` |
| python-docx | Edit documents (Python) | `pip install python-docx` |
| LibreOffice | PDF conversion | `brew install --cask libreoffice` |
| Poppler | PDF to image | `brew install poppler` |
| defusedxml | Safe XML parsing | `pip install defusedxml` |

---

## Tips

- Always **unpack documents before editing** complex elements
- **Grep for current text** in `word/document.xml` before writing scripts (line numbers change after each edit)
- For tracked changes, maintain **professional appearance** by only marking actual changes
- Use **pandoc for verification** after making changes
- Back up original documents before modification
