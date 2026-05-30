# Design: Replace .docx Outputs with PDF

**Date:** 2026-05-30  
**Status:** Approved  
**Scope:** boon-academy-intervention pipeline

---

## Problem

The pipeline currently produces 9 `.docx` files (Word documents). PDF is the required output format for all document-type files.

---

## Scope

**In scope:** Replace all 9 `.docx` output files with `.pdf` equivalents.  
**Out of scope:** `.xlsx`, `.csv`, `.html`, `.json` outputs — these remain unchanged.  
**Approach:** Pure Python, no external applications (no Word, no LibreOffice).  
**Library:** `fpdf2==2.8.3`

---

## File Changes

| Old path | New path |
|---|---|
| `outputs/intervention_report.docx` | `outputs/intervention_report.pdf` |
| `docs/analysis.docx` | `docs/analysis.pdf` |
| `docs/architecture.docx` | `docs/architecture.pdf` |
| `docs/security.docx` | `docs/security.pdf` |
| `docs/engineering_decisions.docx` | `docs/engineering_decisions.pdf` |
| `docs/data_handling.docx` | `docs/data_handling.pdf` |
| `docs/scalability.docx` | `docs/scalability.pdf` |
| `docs/system_design.docx` | `docs/system_design.pdf` |
| `docs/alternatives.docx` | `docs/alternatives.pdf` |

`docs/analysis.md` is **not changed** — Markdown stays as-is.

---

## Architecture

Two source files change:

- **`src/output_generator.py`** — `_write_report()` rewritten with fpdf2. Filename changes to `intervention_report.pdf`.
- **`src/doc_generator.py`** — `_render_doc_from_content()` and all 8 private helpers rewritten with fpdf2. All filenames change from `.docx` to `.pdf`. The `Document` import removed.

**`main.py` is unchanged.** Public signatures of `write_outputs()` and `write_docs()` are unchanged — both still return `dict[str, Path]`.

---

## PDF Rendering Conventions

All documents share these rendering rules, enforced by a `_make_pdf()` shared factory:

| Element | Rendering |
|---|---|
| Page size | A4 |
| Margins | 20mm left/right, 15mm top/bottom |
| Auto page break | Enabled, 20mm bottom margin |
| Title (level 0) | DejaVu Bold, 20pt, after which a blank line is inserted |
| H1 heading | DejaVu Bold, 14pt |
| H2 heading | DejaVu Bold, 12pt |
| Paragraph | DejaVu (regular), 11pt, `multi_cell()` for line wrapping, 6pt spacing after |
| Bullet | DejaVu (regular), 11pt, 8mm left indent, `•` prefix |
| Table header row | DejaVu Bold, 10pt, light grey fill (`#EEEEEE`) |
| Table data rows | DejaVu (regular), 10pt, alternating white / very light grey (`#F9F9F9`) |
| Table borders | 0.3mm grey line |

Font: **DejaVu** (bundled with fpdf2) — no external font installation required.

---

## Shared Helper: `_make_pdf()`

Both `output_generator.py` and `doc_generator.py` define a module-local `_make_pdf()` that returns a pre-configured `FPDF` instance:

```python
def _make_pdf() -> FPDF:
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_margins(left=20, top=15, right=20)
    return pdf
```

Each document function calls `_make_pdf()`, builds content, then saves with `pdf.output(str(path))`.

---

## Shared Helper: `_render_doc_from_content_pdf()`

Replaces the existing `_render_doc_from_content()` in `doc_generator.py`. Same signature and contract — accepts a YAML content dict and writes a `.pdf` file:

```python
def _render_doc_from_content_pdf(content_dict: dict, docs_dir: Path, filename: str) -> Path:
```

Renders `title`, then iterates `sections` → `heading` + `body` items (`paragraph` / `bullet`).

---

## Dependency Changes

**`requirements.txt`:**
- Remove: `python-docx==1.1.2`
- Add: `fpdf2==2.8.3`

**`src/output_generator.py` imports:**
- Remove: `from docx import Document`
- Add: `from fpdf import FPDF`

**`src/doc_generator.py` imports:**
- Remove: `from docx import Document`
- Add: `from fpdf import FPDF`

---

## Tests

Tests that currently:
- Assert `.docx` path extensions → update to `.pdf`
- Import `python-docx` to inspect document content → remove docx inspection; assert file exists and `file.stat().st_size > 0`
- Check `doc.save()` calls → check `pdf.output()` calls via mocks if needed

End-to-end correctness is verified by the pipeline completing without error and producing non-empty PDF files.

---

## Error Handling

No new error handling needed. fpdf2 raises `FPDFException` on bad input — these propagate naturally through the existing pipeline error handler in `main.py`. The three-layer fallback in `llm_engine.py` is unaffected.

---

## Implementation Order

1. Install `fpdf2`, update `requirements.txt`
2. Rewrite `src/doc_generator.py` — shared helper + 8 doc helpers
3. Rewrite `src/output_generator.py` — `_write_report()`
4. Update tests
5. Run pipeline end-to-end, verify 9 PDFs produced
