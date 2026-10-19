### Progressive disclosure patterns

SKILL.md serves as an overview that points Claude to detailed materials as needed, like a table of contents in an onboarding guide. For an explanation of how progressive disclosure works, see [How Skills work](https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview#how-skills-work) in the overview.

**Practical guidance:**

* Keep SKILL.md body under 500 lines for optimal performance
* Split content into separate files when approaching this limit
* Use the following patterns to organize instructions, code, and resources effectively

#### Visual overview: From simple to complex

A basic Skill starts with just a SKILL.md file containing metadata and instructions:

<Frame>
  ![Simple SKILL.md file showing YAML frontmatter and markdown body](https://platform.claude.com/docs/images/agent-skills-simple-file.svg)
</Frame>

As your Skill grows, you can bundle additional content that Claude loads only when needed:

<Frame>
  ![Bundling additional reference files like reference.md and forms.md.](https://platform.claude.com/docs/images/agent-skills-bundling-content.svg)
</Frame>

The complete Skill directory structure might look like this:

* `pdf/`

  * `SKILL.md`: Main instructions (loaded when triggered)

  * `FORMS.md`: Form-filling guide (loaded as needed)

  * `reference.md`: API reference (loaded as needed)

  * `examples.md`: Usage examples (loaded as needed)

  * `scripts/`

    * `analyze_form.py`: Utility script (executed, not loaded)
    * `fill_form.py`: Form filling script
    * `validate.py`: Validation script

#### Pattern 1: High-level guide with references

````markdown
---
name: pdf-processing
description: Extracts text and tables from PDF files, fills forms, and merges documents. Use when working with PDF files or when the user mentions PDFs, forms, or document extraction.
---

# PDF Processing

## Quick start

Extract text with pdfplumber:
```python
import pdfplumber
with pdfplumber.open("file.pdf") as pdf:
    text = pdf.pages[0].extract_text()
```

## Advanced features

**Form filling**: See [FORMS.md](FORMS.md) for complete guide
**API reference**: See [REFERENCE.md](REFERENCE.md) for all methods
**Examples**: See [EXAMPLES.md](EXAMPLES.md) for common patterns
````

Claude loads FORMS.md, REFERENCE.md, or EXAMPLES.md only when needed.

#### Pattern 2: Domain-specific organization

For Skills with multiple domains, organize content by domain to avoid loading irrelevant context. When a user asks about sales metrics, Claude only needs to read sales-related schemas, not finance or marketing data. This keeps token usage low and context focused.

* `bigquery-skill/`

  * `SKILL.md` (overview and navigation)

  * `reference/`

    * `finance.md` (revenue, billing metrics)
    * `sales.md` (opportunities, pipeline)
    * `product.md` (API usage, features)
    * `marketing.md` (campaigns, attribution)

````markdown SKILL.md
# BigQuery Data Analysis

## Available datasets

**Finance**: Revenue, ARR, billing → See [reference/finance.md](reference/finance.md)
**Sales**: Opportunities, pipeline, accounts → See [reference/sales.md](reference/sales.md)
**Product**: API usage, features, adoption → See [reference/product.md](reference/product.md)
**Marketing**: Campaigns, attribution, email → See [reference/marketing.md](reference/marketing.md)

## Quick search

Find specific metrics using grep:

```bash
grep -i "revenue" reference/finance.md
grep -i "pipeline" reference/sales.md
grep -i "api usage" reference/product.md
```
````

#### Pattern 3: Conditional details

Show basic content, link to advanced content:

```markdown
# DOCX Processing

## Creating documents

Use docx-js for new documents. See [DOCX-JS.md](DOCX-JS.md).

## Editing documents

For simple edits, modify the XML directly.

**For tracked changes**: See [REDLINING.md](REDLINING.md)
**For OOXML details**: See [OOXML.md](OOXML.md)
```

Claude reads REDLINING.md or OOXML.md only when the user needs those features.
