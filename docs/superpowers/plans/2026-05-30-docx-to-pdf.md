# docx-to-PDF Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace all 9 `.docx` pipeline outputs with `.pdf` equivalents using pure-Python `fpdf2`, with no changes to public API signatures or `main.py`.

**Architecture:** `src/output_generator.py` and `src/doc_generator.py` each get a module-local `_make_pdf()` factory and `_safe_text()` helper; all `Document()` / `doc.save()` calls are replaced with `FPDF()` / `pdf.output()` calls. `_render_doc_from_content()` in `doc_generator.py` is replaced by `_render_doc_from_content_pdf()`. Return dict keys and public function signatures are unchanged.

**Tech Stack:** Python 3.11+, fpdf2==2.8.3 (replaces python-docx==1.1.2), pytest, existing pandas/openpyxl stack untouched.

---

## File Map

| File | Action | What changes |
|---|---|---|
| `requirements.txt` | Modify | Remove `python-docx==1.1.2`; add `fpdf2==2.8.3` |
| `src/output_generator.py` | Modify | Remove `from docx import Document`; add `from fpdf import FPDF, FontFace`; add `_make_pdf()`, `_safe_text()`; rewrite `_write_report()` → produces `intervention_report.pdf` |
| `src/doc_generator.py` | Modify | Remove `from docx import Document`; add `from fpdf import FPDF, FontFace`; add `_make_pdf()`, `_safe_text()`; replace `_render_doc_from_content()` with `_render_doc_from_content_pdf()`; rewrite all 8 doc helpers to produce `.pdf`; rename `_write_analysis_docx` → `_write_analysis_pdf`; update `write_docs()` orchestrator |
| `tests/test_output_generator.py` | Modify | Remove `from docx import Document` inline imports; update `_write_report` tests: filename `.docx` → `.pdf`, replace docx-inspection assertions with PDF magic-bytes + size checks |
| `tests/test_doc_generator.py` | Create | New test file: verify `write_docs()` produces 9 paths, all exist, all are `.pdf`, all are non-empty valid PDFs |

---

## Task 1: Update dependencies

**Files:**
- Modify: `requirements.txt`

- [ ] **Step 1: Edit requirements.txt**

Open `requirements.txt` and make this exact change:

```
# Remove this line:
python-docx==1.1.2

# Add this line in its place:
fpdf2==2.8.3
```

Final `requirements.txt` should be:
```
pandas==2.2.3
openpyxl==3.1.5
fpdf2==2.8.3
anthropic==0.103.1
python-dotenv==1.2.2
tenacity==9.1.4
jinja2==3.1.6
PyYAML==6.0.3
respx==0.23.1
```

- [ ] **Step 2: Install fpdf2**

```bash
pip install fpdf2==2.8.3
```

Expected output: `Successfully installed fpdf2-2.8.3`

- [ ] **Step 3: Verify fpdf2 import works**

```bash
python -c "from fpdf import FPDF, FontFace; pdf = FPDF(); pdf.add_page(); pdf.set_font('Helvetica', 'B', 14); pdf.multi_cell(0, 8, 'test'); print('fpdf2 OK')"
```

Expected output: `fpdf2 OK`

- [ ] **Step 4: Commit**

```bash
git add requirements.txt
git commit -m "chore(deps): replace python-docx with fpdf2==2.8.3"
```

---

## Task 2: Update `_write_report` tests to expect PDF

**Files:**
- Modify: `tests/test_output_generator.py`

- [ ] **Step 1: Replace the five `_write_report` tests**

In `tests/test_output_generator.py`, find and replace all five functions starting from `def test_report_returns_path` through `def test_report_data_quality_no_warnings` (lines ~780–845) with these:

```python
# ---------------------------------------------------------------------------
# _write_report tests (OUT-04) — PDF output
# ---------------------------------------------------------------------------


@pytest.fixture
def report_path(sample_df: pd.DataFrame, sample_run_log: dict, tmp_path: Path) -> Path:
    """Write PDF intervention report to tmp_path and return the path for assertions."""
    return _write_report(sample_df, sample_run_log, tmp_path)


def test_report_returns_path(report_path: Path) -> None:
    """_write_report returns a Path pointing to intervention_report.pdf."""
    assert isinstance(report_path, Path), f"Expected Path, got {type(report_path)}"
    assert report_path.exists(), f"Returned path does not exist: {report_path}"
    assert report_path.name == "intervention_report.pdf"


def test_report_is_valid_pdf(report_path: Path) -> None:
    """intervention_report.pdf starts with the PDF magic bytes %PDF-."""
    magic = report_path.read_bytes()[:5]
    assert magic == b"%PDF-", f"Expected PDF magic bytes b'%PDF-', got {magic!r}"


def test_report_nonempty_pdf(report_path: Path) -> None:
    """intervention_report.pdf is larger than 1 KB — contains real content."""
    size = report_path.stat().st_size
    assert size > 1024, f"Expected PDF > 1024 bytes, got {size} bytes"


def test_report_data_quality_no_warnings_pdf(
    sample_df: pd.DataFrame, tmp_path: Path
) -> None:
    """_write_report with empty data_quality_warnings still produces a valid PDF."""
    run_log_no_warnings = {
        "run_timestamp": "2026-01-01T00:00:00+00:00",
        "students_processed": 4,
        "api_calls_made": 1,
        "tokens_used": {"input": 50, "output": 25},
        "errors_encountered": [],
        "fallbacks_triggered": 0,
        "data_quality_warnings": [],
    }
    path = _write_report(sample_df, run_log_no_warnings, tmp_path)
    assert path.exists(), f"PDF not created: {path}"
    assert path.read_bytes()[:5] == b"%PDF-", "Expected valid PDF output"
```

- [ ] **Step 2: Run the report tests to verify they FAIL (implementation not yet written)**

```bash
pytest tests/test_output_generator.py -k "report" -v
```

Expected: FAIL on `test_report_returns_path` because `_write_report` still returns `.docx`.

- [ ] **Step 3: Commit the updated tests**

```bash
git add tests/test_output_generator.py
git commit -m "test(output): update _write_report tests to expect PDF output"
```

---

## Task 3: Rewrite `_write_report()` in `output_generator.py`

**Files:**
- Modify: `src/output_generator.py`

- [ ] **Step 1: Replace the `from docx import Document` import**

At the top of `src/output_generator.py`, find:
```python
from docx import Document
```
Replace with:
```python
from fpdf import FPDF, FontFace
```

- [ ] **Step 2: Add `_make_pdf()` and `_safe_text()` helpers after the `logger` line**

After line `logger = logging.getLogger(__name__)`, add:

```python

def _make_pdf() -> FPDF:
    """Return a pre-configured FPDF instance: A4, 20mm margins, auto page break."""
    pdf = FPDF()
    pdf.set_margins(left=20, top=15, right=20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 11)
    return pdf


def _safe_text(text: str) -> str:
    """Replace non-latin1 Unicode chars with ASCII equivalents for Helvetica rendering."""
    replacements = {
        "—": " - ", "–": " - ",
        "’": "'", "‘": "'",
        "“": '"', "”": '"',
        "•": "-", "→": "->",
    }
    for char, sub in replacements.items():
        text = text.replace(char, sub)
    return text.encode("latin-1", errors="replace").decode("latin-1")

```

- [ ] **Step 3: Replace the entire `_write_report()` function**

Find the function starting at `def _write_report(df: pd.DataFrame, run_log: dict, output_dir: Path) -> Path:` and ending at `return path` (before `def _write_priority_list`). Replace it entirely with:

```python
def _write_report(df: pd.DataFrame, run_log: dict, output_dir: Path) -> Path:
    """Write intervention_report.pdf — programmatic fpdf2 builder (OUT-04).

    Produces a 7-section A4 PDF document mirroring the previous .docx output.
    Uses Helvetica (built-in) with _safe_text() for latin-1 safety.

    Args:
        df: Fully enriched one-row-per-student DataFrame from enrich_with_llm().
        run_log: Pipeline run metadata dict.
        output_dir: Directory to write intervention_report.pdf into.

    Returns:
        Path to the written intervention_report.pdf file.
    """
    df_copy = df.copy()
    pdf = _make_pdf()
    hs = FontFace(emphasis="BOLD", fill_color=(220, 220, 220))  # heading style for tables

    # -----------------------------------------------------------------------
    # Section 1 — Cover page
    # -----------------------------------------------------------------------
    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(0, 10, _safe_text("Boon Academy - Student Intervention Report"))
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, f"Run date: {run_log.get('run_timestamp', 'N/A')}")
    campus_count = df_copy[cfg.COL_CAMPUS_ID].nunique()
    pdf.multi_cell(0, 6, f"Campuses: {campus_count}")
    pdf.multi_cell(0, 6, f"Students processed: {run_log.get('students_processed', len(df_copy))}")
    pdf.ln(4)

    # -----------------------------------------------------------------------
    # Section 2 — Executive Summary
    # -----------------------------------------------------------------------
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "Executive Summary")
    pdf.ln(2)

    total = len(df_copy)
    risk_counts = df_copy[cfg.COL_RISK_LEVEL].value_counts()
    critical_count = int(risk_counts.get("CRITICAL", 0))
    high_count = int(risk_counts.get("HIGH", 0))
    medium_count = int(risk_counts.get("MEDIUM", 0))
    low_count = int(risk_counts.get("LOW", 0))
    critical_pct = (critical_count / total * 100) if total > 0 else 0.0

    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0, 6,
        f"Of {total} students, {critical_count} ({critical_pct:.0f}%) are at CRITICAL "
        "risk requiring immediate intervention. The pipeline has generated prioritised "
        "facilitator action items and drafted WhatsApp parent messages for all CRITICAL "
        "and HIGH risk students.",
    )
    pdf.ln(3)

    pdf.set_font("Helvetica", "", 10)
    with pdf.table(headings_style=hs, num_heading_rows=1) as table:
        row = table.row()
        for h in ("Risk Level", "Count", "% of Total"):
            row.cell(h)
        for level, count in [
            ("CRITICAL", critical_count),
            ("HIGH", high_count),
            ("MEDIUM", medium_count),
            ("LOW", low_count),
        ]:
            pct = (count / total * 100) if total > 0 else 0.0
            row = table.row()
            row.cell(level)
            row.cell(str(count))
            row.cell(f"{pct:.1f}%")
    pdf.ln(4)

    # -----------------------------------------------------------------------
    # Section 3 — Top 10 Most At-Risk Students
    # -----------------------------------------------------------------------
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "Top 10 Most At-Risk Students")
    pdf.ln(2)

    top10 = df_copy.nlargest(10, cfg.COL_RISK_SCORE)
    pdf.set_font("Helvetica", "", 10)
    with pdf.table(headings_style=hs, num_heading_rows=1) as table:
        row = table.row()
        for h in ("Rank", "Student Name", "Campus", "Risk Score", "Risk Level"):
            row.cell(h)
        for rank_idx, (_, student) in enumerate(top10.iterrows(), start=1):
            row = table.row()
            row.cell(str(rank_idx))
            row.cell(_safe_text(str(student[cfg.COL_STUDENT_NAME])))
            row.cell(_safe_text(str(student[cfg.COL_CAMPUS_ID])))
            row.cell(f"{student[cfg.COL_RISK_SCORE]:.1f}")
            row.cell(str(student[cfg.COL_RISK_LEVEL]))
    pdf.ln(4)

    # -----------------------------------------------------------------------
    # Section 4 — Campus Summary
    # -----------------------------------------------------------------------
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "Campus Summary")
    pdf.ln(2)

    campus_groups = df_copy.groupby(cfg.COL_CAMPUS_ID, dropna=True)
    pdf.set_font("Helvetica", "", 10)
    with pdf.table(headings_style=hs, num_heading_rows=1) as table:
        row = table.row()
        for h in ("Campus", "Total Students", "Critical", "High", "Intervention Coverage %"):
            row.cell(h)
        for campus_id, campus_df in campus_groups:
            c_total = len(campus_df)
            c_critical = int((campus_df[cfg.COL_RISK_LEVEL] == "CRITICAL").sum())
            c_high = int((campus_df[cfg.COL_RISK_LEVEL] == "HIGH").sum())
            c_coverage = (
                round((c_critical + c_high) / c_total * 100, 1) if c_total > 0 else 0.0
            )
            row = table.row()
            row.cell(_safe_text(str(campus_id)))
            row.cell(str(c_total))
            row.cell(str(c_critical))
            row.cell(str(c_high))
            row.cell(f"{c_coverage}%")
    pdf.ln(4)

    # -----------------------------------------------------------------------
    # Section 5 — Student Deep-Dives
    # -----------------------------------------------------------------------
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "Student Deep-Dives")
    pdf.ln(2)

    component_cols = [
        cfg.COL_ATTENDANCE_RATE,
        cfg.COL_AVG_PRACTICE,
        cfg.COL_TREND_DIR,
        cfg.COL_DAYS_SINCE_NOTE,
    ]
    component_labels = [
        "Attendance Rate",
        "Avg Practice Questions",
        "Trend Direction",
        "Days Since Last Note",
    ]

    for tier in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        tier_df = df_copy[df_copy[cfg.COL_RISK_LEVEL] == tier]
        if tier_df.empty:
            continue
        student = tier_df.nlargest(1, cfg.COL_RISK_SCORE).iloc[0]
        pdf.set_font("Helvetica", "B", 12)
        pdf.multi_cell(0, 7, _safe_text(f"{tier} - {student[cfg.COL_STUDENT_NAME]}"))
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(
            0, 6,
            _safe_text(
                f"Campus: {student[cfg.COL_CAMPUS_ID]} | "
                f"Risk Score: {student[cfg.COL_RISK_SCORE]:.1f} | "
                f"Level: {student[cfg.COL_RISK_LEVEL]}"
            ),
        )
        pdf.set_font("Helvetica", "", 10)
        with pdf.table(headings_style=hs, num_heading_rows=1) as table:
            row = table.row()
            row.cell("Component")
            row.cell("Score")
            for col, label in zip(component_cols, component_labels):
                value = student[col] if col in df_copy.columns else "N/A"
                row = table.row()
                row.cell(label)
                row.cell(_safe_text(str(value)))
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(
            0, 6, f"Facilitator Summary: {_safe_text(_str_or_na(student[cfg.COL_FACILITATOR_SUMMARY]))}"
        )
        pdf.multi_cell(
            0, 6, f"Recommended Action: {_safe_text(_str_or_na(student[cfg.COL_RECOMMENDED_ACTION]))}"
        )
        pdf.ln(3)

    # -----------------------------------------------------------------------
    # Section 6 — Automated Data Cleanup Summary
    # -----------------------------------------------------------------------
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "Automated Data Cleanup Summary")
    pdf.ln(2)

    warnings = run_log.get("data_quality_warnings", [])
    missing_count = sum(1 for w in warnings if w.get("type") == "missing_numeric")
    mismatch_count = sum(1 for w in warnings if w.get("type") == "type_mismatch")
    duplicate_count = sum(1 for w in warnings if w.get("type") == "duplicate_id")

    pdf.set_font("Helvetica", "", 11)
    if not warnings:
        pdf.multi_cell(
            0, 6, "No data quality issues detected. All student records were complete and valid."
        )
    else:
        pdf.multi_cell(
            0, 6,
            "The pipeline automatically detected and resolved the following data quality issues "
            "before scoring. No students were excluded - all records were corrected and included "
            "in the risk analysis.",
        )
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 10)
        with pdf.table(headings_style=hs, num_heading_rows=1) as table:
            row = table.row()
            for h in ("Issue Type", "Count", "Action Taken"):
                row.cell(h)
            for issue_type, count, action in [
                ("Missing numeric values", str(missing_count), "Filled with 0"),
                ("Non-numeric values", str(mismatch_count), "Coerced to 0"),
                ("Duplicate student IDs", str(duplicate_count), "Kept last record"),
            ]:
                row = table.row()
                row.cell(issue_type)
                row.cell(count)
                row.cell(action)
    pdf.ln(4)

    # -----------------------------------------------------------------------
    # Section 7 — Methodology Appendix
    # -----------------------------------------------------------------------
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "Methodology Appendix")
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(0, 7, "Risk Score Formula")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, "Risk score (0-100) is computed as a weighted sum of four components:")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    with pdf.table(headings_style=hs, num_heading_rows=1) as table:
        row = table.row()
        row.cell("Component")
        row.cell("Weight")
        for component, weight in [
            ("Attendance Rate", f"{cfg.WEIGHT_ATTENDANCE:.0%}"),
            ("Avg Practice Questions", f"{cfg.WEIGHT_PRACTICE:.0%}"),
            ("Trend Direction", f"{cfg.WEIGHT_TREND:.0%}"),
            ("Days Since Last Note", f"{cfg.WEIGHT_NOTES:.0%}"),
        ]:
            row = table.row()
            row.cell(component)
            row.cell(weight)
    pdf.ln(3)
    pdf.set_font("Helvetica", "B", 12)
    pdf.multi_cell(0, 7, "Risk Level Thresholds")
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, f"CRITICAL: score >= {cfg.RISK_THRESHOLD_CRITICAL}")
    pdf.multi_cell(
        0, 6, f"HIGH: {cfg.RISK_THRESHOLD_HIGH} <= score < {cfg.RISK_THRESHOLD_CRITICAL}"
    )
    pdf.multi_cell(
        0, 6, f"MEDIUM: {cfg.RISK_THRESHOLD_MEDIUM} <= score < {cfg.RISK_THRESHOLD_HIGH}"
    )
    pdf.multi_cell(0, 6, f"LOW: score < {cfg.RISK_THRESHOLD_MEDIUM}")

    path = output_dir / "intervention_report.pdf"
    pdf.output(str(path))
    logger.info("Wrote PDF report: %s (%d students)", path, len(df_copy))
    return path
```

- [ ] **Step 4: Run the report tests to verify they PASS**

```bash
pytest tests/test_output_generator.py -k "report" -v
```

Expected: all 4 report tests PASS.

- [ ] **Step 5: Run the full test suite to check for regressions**

```bash
pytest tests/test_output_generator.py -v
```

Expected: all tests pass. The `write_outputs` integration tests still pass because they only check `path.exists()`, not file format.

- [ ] **Step 6: Commit**

```bash
git add src/output_generator.py
git commit -m "feat(output): rewrite _write_report() to produce PDF via fpdf2"
```

---

## Task 4: Create `tests/test_doc_generator.py` with failing tests

**Files:**
- Create: `tests/test_doc_generator.py`

- [ ] **Step 1: Create the test file**

```python
"""Tests for src/doc_generator.py — write_docs() PDF output.

Verifies that write_docs() produces the expected PDF files:
- analysis.pdf, architecture.pdf, security.pdf, engineering_decisions.pdf,
  data_handling.pdf, scalability.pdf, system_design.pdf, alternatives.pdf
All files must exist, be non-empty, and start with the PDF magic bytes.
analysis.md is a Markdown file — it is NOT tested here.
"""
import os
from pathlib import Path

import pandas as pd
import pytest

os.environ.setdefault("ANTHROPIC_API_KEY", "dummy-key-for-tests")

from src import config as cfg
from src.doc_generator import write_docs


@pytest.fixture()
def minimal_df() -> pd.DataFrame:
    """Minimal 2-row DataFrame satisfying write_docs() column requirements."""
    return pd.DataFrame({
        cfg.COL_STUDENT_ID: ["S001", "S002"],
        cfg.COL_STUDENT_NAME: ["Alice", "Bob"],
        cfg.COL_CAMPUS_ID: ["C01", "C01"],
        cfg.COL_PARENT_PHONE: ["0501111111", "0502222222"],
        cfg.COL_FACILITATOR_EMAIL: ["f@c01.sa", "f@c01.sa"],
        cfg.COL_RISK_SCORE: [88.0, 45.0],
        cfg.COL_RISK_LEVEL: ["CRITICAL", "MEDIUM"],
        cfg.COL_ATTENDANCE_RATE: [0.2, 0.7],
        cfg.COL_AVG_PRACTICE: [1.0, 5.0],
        cfg.COL_TREND_DIR: ["declining", "stable"],
        cfg.COL_DAYS_SINCE_NOTE: [20, 4],
        cfg.COL_RECOMMENDED_ACTION: ["Contact parent", "Monitor"],
        cfg.COL_FACILITATOR_SUMMARY: ["Alice at risk", None],
        cfg.COL_WHATSAPP_MESSAGE: ["Msg for Alice", None],
        cfg.COL_GENERATED_BY: ["llm", None],
        cfg.COL_LLM_ERROR_REASON: [None, None],
        cfg.COL_ATTENDANCE_COMPONENT: [31.5, 7.0],
        cfg.COL_PRACTICE_COMPONENT: [27.0, 12.0],
        cfg.COL_TREND_COMPONENT: [20.0, 10.0],
        cfg.COL_NOTES_COMPONENT: [9.5, 3.0],
    })


@pytest.fixture()
def minimal_run_log() -> dict:
    """Minimal run_log dict for doc generation."""
    return {
        "run_timestamp": "2026-05-30T10:00:00+00:00",
        "students_processed": 2,
        "api_calls_made": 1,
        "tokens_used": {"input": 100, "output": 50},
        "errors_encountered": [],
        "fallbacks_triggered": 0,
        "data_quality_warnings": [],
    }


@pytest.fixture()
def doc_paths(minimal_df: pd.DataFrame, minimal_run_log: dict, tmp_path: Path) -> dict[str, Path]:
    """Run write_docs() into tmp_path and return the result dict."""
    return write_docs(minimal_df, minimal_run_log, tmp_path)


_EXPECTED_PDF_KEYS = [
    "analysis_pdf",
    "architecture",
    "security",
    "engineering_decisions",
    "data_handling",
    "scalability",
    "system_design",
    "alternatives",
]

_EXPECTED_ALL_KEYS = ["analysis_md"] + _EXPECTED_PDF_KEYS


def test_write_docs_returns_all_keys(doc_paths: dict[str, Path]) -> None:
    """write_docs() returns a dict containing all 9 expected keys."""
    for key in _EXPECTED_ALL_KEYS:
        assert key in doc_paths, f"Missing key {key!r} in write_docs() result: {list(doc_paths.keys())}"


def test_write_docs_all_files_exist(doc_paths: dict[str, Path]) -> None:
    """Every Path value returned by write_docs() points to a file that exists on disk."""
    for key, path in doc_paths.items():
        assert isinstance(path, Path), f"Expected Path for key {key!r}, got {type(path)}"
        assert path.exists(), f"File missing for key {key!r}: {path}"


def test_write_docs_pdf_files_have_pdf_magic(doc_paths: dict[str, Path]) -> None:
    """Every PDF output file starts with b'%PDF-' (valid PDF magic bytes)."""
    for key in _EXPECTED_PDF_KEYS:
        path = doc_paths[key]
        magic = path.read_bytes()[:5]
        assert magic == b"%PDF-", (
            f"Key {key!r} at {path.name}: expected PDF magic b'%PDF-', got {magic!r}"
        )


def test_write_docs_pdf_files_nonempty(doc_paths: dict[str, Path]) -> None:
    """Every PDF output file is larger than 1 KB — contains real content."""
    for key in _EXPECTED_PDF_KEYS:
        path = doc_paths[key]
        size = path.stat().st_size
        assert size > 1024, (
            f"Key {key!r} at {path.name}: expected > 1024 bytes, got {size} bytes"
        )


def test_write_docs_analysis_md_is_markdown(doc_paths: dict[str, Path]) -> None:
    """analysis.md ends in .md and contains the expected section headers."""
    path = doc_paths["analysis_md"]
    assert path.suffix == ".md", f"Expected .md extension, got {path.suffix}"
    content = path.read_text(encoding="utf-8")
    for section in ("## Diagnosis", "## What You Found", "## What You Built"):
        assert section in content, f"Expected section {section!r} in analysis.md"


def test_write_docs_pdf_filenames(doc_paths: dict[str, Path]) -> None:
    """Each PDF key maps to a file with the expected .pdf extension and filename."""
    expected_names = {
        "analysis_pdf": "analysis.pdf",
        "architecture": "architecture.pdf",
        "security": "security.pdf",
        "engineering_decisions": "engineering_decisions.pdf",
        "data_handling": "data_handling.pdf",
        "scalability": "scalability.pdf",
        "system_design": "system_design.pdf",
        "alternatives": "alternatives.pdf",
    }
    for key, expected_name in expected_names.items():
        actual_name = doc_paths[key].name
        assert actual_name == expected_name, (
            f"Key {key!r}: expected filename {expected_name!r}, got {actual_name!r}"
        )


def test_write_docs_creates_docs_dir(
    minimal_df: pd.DataFrame, minimal_run_log: dict, tmp_path: Path
) -> None:
    """write_docs() creates a non-existent docs_dir without error."""
    nested = tmp_path / "deep" / "docs"
    assert not nested.exists()
    result = write_docs(minimal_df, minimal_run_log, nested)
    assert nested.exists()
    assert len(result) == 9
```

- [ ] **Step 2: Run the new tests to verify they FAIL (implementation not yet done)**

```bash
pytest tests/test_doc_generator.py -v
```

Expected: multiple FAILs — `write_docs()` still returns `.docx` keys/paths.

- [ ] **Step 3: Commit the test file**

```bash
git add tests/test_doc_generator.py
git commit -m "test(docs): add test_doc_generator.py expecting PDF output"
```

---

## Task 5: Rewrite `src/doc_generator.py` — helpers and static doc functions

**Files:**
- Modify: `src/doc_generator.py`

- [ ] **Step 1: Replace the `from docx import Document` import**

Find:
```python
from docx import Document
```
Replace with:
```python
from fpdf import FPDF, FontFace
```

- [ ] **Step 2: Add `_make_pdf()` and `_safe_text()` after the `logger` line**

After `logger = logging.getLogger(__name__)`, add:

```python

def _make_pdf() -> FPDF:
    """Return a pre-configured FPDF instance: A4, 20mm margins, auto page break."""
    pdf = FPDF()
    pdf.set_margins(left=20, top=15, right=20)
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()
    pdf.set_font("Helvetica", "", 11)
    return pdf


def _safe_text(text: str) -> str:
    """Replace non-latin1 Unicode chars with ASCII equivalents for Helvetica rendering."""
    replacements = {
        "—": " - ", "–": " - ",
        "’": "'", "‘": "'",
        "“": '"', "”": '"',
        "•": "-", "→": "->",
    }
    for char, sub in replacements.items():
        text = text.replace(char, sub)
    return text.encode("latin-1", errors="replace").decode("latin-1")

```

- [ ] **Step 3: Replace `_render_doc_from_content()` with `_render_doc_from_content_pdf()`**

Find the entire `_render_doc_from_content()` function and replace it with:

```python
def _render_doc_from_content_pdf(content_dict: dict, docs_dir: Path, filename: str) -> Path:
    """Render a YAML content dict into a .pdf file using fpdf2.

    Each content_dict must have 'title' (str) and 'sections' (list).
    Each section has 'heading' (str) and 'body' (list of {type, text} dicts).
    Supported body types: 'paragraph' and 'bullet'.

    Args:
        content_dict: Parsed YAML dict with 'title' and 'sections' keys.
        docs_dir: Directory to write the .pdf file into.
        filename: Output filename (e.g. 'architecture.pdf').

    Returns:
        Path to the written .pdf file.
    """
    pdf = _make_pdf()
    hs = FontFace(emphasis="BOLD", fill_color=(220, 220, 220))

    title = content_dict.get(
        "title", filename.replace(".pdf", "").replace("_", " ").title()
    )
    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(0, 10, _safe_text(title))
    pdf.ln(4)

    for section in content_dict.get("sections", []):
        heading = section.get("heading", "")
        if heading:
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(0, 8, _safe_text(heading))
            pdf.ln(2)
        for item in section.get("body", []):
            item_type = item.get("type", "paragraph")
            text = item.get("text", "")
            if item_type == "bullet":
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, "- " + _safe_text(text))
                pdf.ln(1)
            else:
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, _safe_text(text))
                pdf.ln(3)

    path = docs_dir / filename
    pdf.output(str(path))
    return path
```

- [ ] **Step 4: Update the 6 static doc helpers that delegate to `_render_doc_from_content`**

Replace each of `_write_architecture`, `_write_security`, `_write_engineering_decisions`, `_write_data_handling`, `_write_system_design`, `_write_alternatives` with the PDF version. For each, the only changes are:
1. Call `_render_doc_from_content_pdf(...)` instead of `_render_doc_from_content(...)`
2. Change filename argument from `.docx` to `.pdf`
3. Update logger message from `.docx` to `.pdf`

After the edit, each function looks like this pattern (shown for `_write_architecture`):

```python
def _write_architecture(docs_dir: Path, content: dict) -> Path:
    """Write docs/architecture.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "architecture.pdf")
    logger.info("Wrote architecture.pdf: %s", path)
    return path


def _write_security(docs_dir: Path, content: dict) -> Path:
    """Write docs/security.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "security.pdf")
    logger.info("Wrote security.pdf: %s", path)
    return path


def _write_engineering_decisions(docs_dir: Path, content: dict) -> Path:
    """Write docs/engineering_decisions.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "engineering_decisions.pdf")
    logger.info("Wrote engineering_decisions.pdf: %s", path)
    return path


def _write_data_handling(docs_dir: Path, content: dict) -> Path:
    """Write docs/data_handling.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "data_handling.pdf")
    logger.info("Wrote data_handling.pdf: %s", path)
    return path


def _write_system_design(docs_dir: Path, content: dict) -> Path:
    """Write docs/system_design.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "system_design.pdf")
    logger.info("Wrote system_design.pdf: %s", path)
    return path


def _write_alternatives(docs_dir: Path, content: dict) -> Path:
    """Write docs/alternatives.pdf from docs_content.yaml."""
    path = _render_doc_from_content_pdf(content, docs_dir, "alternatives.pdf")
    logger.info("Wrote alternatives.pdf: %s", path)
    return path
```

- [ ] **Step 5: Run the doc generator tests**

```bash
pytest tests/test_doc_generator.py -v
```

Expected: the 6 static-doc tests start passing. `analysis_pdf` and `scalability` tests still FAIL (not yet rewritten).

- [ ] **Step 6: Commit**

```bash
git add src/doc_generator.py
git commit -m "feat(docs): replace docx shared helper and 6 static doc helpers with fpdf2 PDF"
```

---

## Task 6: Rewrite `_write_scalability()` and `_write_analysis_*` in `doc_generator.py`

**Files:**
- Modify: `src/doc_generator.py`

- [ ] **Step 1: Replace `_write_scalability()` with the PDF version**

Find the entire `_write_scalability()` function and replace it with:

```python
def _write_scalability(docs_dir: Path, content: dict) -> Path:
    """Write docs/scalability.pdf with YAML sections plus programmatic cost tables."""
    pdf = _make_pdf()
    hs = FontFace(emphasis="BOLD", fill_color=(220, 220, 220))

    title = content.get("title", "Scalability Analysis")
    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(0, 10, _safe_text(title))
    pdf.ln(4)

    for section in content.get("sections", []):
        heading = section.get("heading", "")
        if heading:
            pdf.set_font("Helvetica", "B", 14)
            pdf.multi_cell(0, 8, _safe_text(heading))
            pdf.ln(2)
        for item in section.get("body", []):
            item_type = item.get("type", "paragraph")
            text = item.get("text", "")
            if item_type == "bullet":
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, "- " + _safe_text(text))
                pdf.ln(1)
            else:
                pdf.set_font("Helvetica", "", 11)
                pdf.multi_cell(0, 6, _safe_text(text))
                pdf.ln(3)

    # Scale comparison table
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "Scale Comparison")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0, 6,
        "The table below projects at-risk student count and token usage as campus count "
        "grows. Calculation basis: 106 tokens/student (31,771 tokens / 300 students "
        "from demo run); 40% CRITICAL/HIGH rate assumed.",
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    with pdf.table(headings_style=hs, num_heading_rows=1) as table:
        row = table.row()
        for h in ("Scale", "At-Risk Students/Run", "Est. Tokens/Run"):
            row.cell(h)
        row = table.row()
        row.cell("20 campuses (current)")
        row.cell("~120")
        row.cell("~12,720")
        row = table.row()
        row.cell("100 campuses")
        row.cell("~600")
        row.cell("~63,600")
    pdf.ln(4)

    # Monthly cost table
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, "Monthly Cost Estimate")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(
        0, 6,
        "Estimated monthly cost at claude-sonnet-4-5 pricing (~$6/million tokens blended). "
        "Both scenarios are well within the $200/month budget target - 17x headroom at 100 campuses.",
    )
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 10)
    with pdf.table(headings_style=hs, num_heading_rows=1) as table:
        row = table.row()
        for h in ("Runs/Month", "Tokens/Run", "Est. Monthly Cost"):
            row.cell(h)
        row = table.row()
        row.cell("30")
        row.cell("~12,720")
        row.cell("<$1/month")
        row = table.row()
        row.cell("30")
        row.cell("~63,600")
        row.cell("~$5-10/month")

    path = docs_dir / "scalability.pdf"
    pdf.output(str(path))
    logger.info("Wrote scalability.pdf: %s", path)
    return path
```

- [ ] **Step 2: Replace `_write_analysis_docx()` with `_write_analysis_pdf()`**

Find the entire `_write_analysis_docx()` function and replace it with:

```python
def _write_analysis_pdf(run_log: dict, docs_dir: Path) -> Path:
    """Write docs/analysis.pdf - Word version of the 5-section analysis.

    Args:
        run_log: Pipeline run metadata dict with live numbers.
        docs_dir: Directory to write analysis.pdf into.

    Returns:
        Path to docs/analysis.pdf.
    """
    tokens_used = run_log.get("tokens_used", {})
    tokens_in = tokens_used.get("input", 0)
    tokens_out = tokens_used.get("output", 0)
    tokens_total = tokens_in + tokens_out
    students_processed = run_log.get("students_processed", 0)
    api_calls = run_log.get("api_calls_made", 0)
    fallbacks = run_log.get("fallbacks_triggered", 0)
    run_timestamp = run_log.get("run_timestamp", "N/A")

    pdf = _make_pdf()

    pdf.set_font("Helvetica", "B", 20)
    pdf.multi_cell(0, 10, "Analysis: boon-academy-intervention")
    pdf.ln(2)
    pdf.set_font("Helvetica", "", 11)
    pdf.multi_cell(0, 6, f"Generated: {run_timestamp}")
    pdf.ln(4)

    sections = [
        (
            "Diagnosis",
            "Boon Academy runs 20 campuses serving roughly 300 students. Facilitator "
            "intervention rate is currently ~30% against an 80%+ target. The gap exists "
            "because facilitators lack a fast, prioritised view of which students to contact "
            "and what to say. This pipeline closes that gap by scoring every student daily, "
            "ranking them by risk, and generating draft WhatsApp messages that facilitators "
            "send in one click.",
        ),
        (
            "What You Found",
            f"Student intake: {students_processed} students processed in this run. "
            "Risk distribution is available in the intervention_priority_list.xlsx output "
            "(colour-coded by CRITICAL / HIGH / MEDIUM / LOW). All data quality issues "
            "(missing metrics, type-mismatch strings, blank notes) were auto-resolved by "
            "the ingestion layer - no manual cleanup required.",
        ),
        (
            "What You Built",
            f"A five-stage pipeline: ingest -> score -> LLM enrich -> outputs -> docs. "
            f"LLM usage this run: {api_calls} API calls, {tokens_total} tokens total "
            f"({tokens_in} input + {tokens_out} output). Fallbacks triggered: {fallbacks}. "
            "Output files: intervention_priority_list.xlsx, campus_dashboard_<id>.xlsx, "
            "whatsapp_messages.csv, dashboard.html, intervention_report.pdf, "
            "docs/ (nine technical docs).",
        ),
        (
            "What You Cut",
            "No ML model - deterministic weighted scoring is auditable with no training data needed. "
            "No real-time server - on-demand script run fits current workflow. "
            "No OAuth or SSO - outputs are file-based, not a web app. "
            "No Docker or Kubernetes - single-machine Python script. "
            "No direct WhatsApp API sending - facilitators copy-paste from CSV as the safe v1 path.",
        ),
        (
            "What Next",
            "1. Hook up real student data - replace synthetic CSVs with live exports.\n"
            "2. Validate risk weights with the academic director.\n"
            "3. Confirm Arabic dialect per campus (Modern Standard vs. Gulf).\n"
            "4. Test outputs on LibreOffice - facilitator PCs may not have Excel.\n"
            "5. Consider a scheduled daily trigger (cron or Windows Task Scheduler).",
        ),
    ]

    for heading, body in sections:
        pdf.set_font("Helvetica", "B", 14)
        pdf.multi_cell(0, 8, heading)
        pdf.ln(2)
        pdf.set_font("Helvetica", "", 11)
        pdf.multi_cell(0, 6, _safe_text(body))
        pdf.ln(4)

    path = docs_dir / "analysis.pdf"
    pdf.output(str(path))
    logger.info("Wrote analysis.pdf: %s", path)
    return path
```

- [ ] **Step 3: Update `write_docs()` orchestrator**

In `write_docs()`, find:
```python
    paths["analysis_docx"] = _write_analysis_docx(run_log, docs_dir)
```
Replace with:
```python
    paths["analysis_pdf"] = _write_analysis_pdf(run_log, docs_dir)
```

- [ ] **Step 4: Run all doc generator tests**

```bash
pytest tests/test_doc_generator.py -v
```

Expected: all 8 tests PASS.

- [ ] **Step 5: Run the full test suite**

```bash
pytest tests/ -v --ignore=tests/test_llm_engine.py
```

Expected: all tests pass (excluding llm_engine which requires API key).

- [ ] **Step 6: Commit**

```bash
git add src/doc_generator.py
git commit -m "feat(docs): rewrite scalability and analysis doc helpers to produce PDF via fpdf2"
```

---

## Task 7: End-to-end pipeline run and verification

**Files:** None (verification only)

- [ ] **Step 1: Run the pipeline**

```bash
python main.py
```

Expected output (stderr): pipeline completes without error, log lines show "Wrote PDF report", "Wrote analysis.pdf", etc.

- [ ] **Step 2: Verify the 9 PDF files exist**

```bash
python -c "
from pathlib import Path
pdf_files = list(Path('outputs').glob('*.pdf')) + list(Path('docs').glob('*.pdf'))
print('PDF files found:')
for f in sorted(pdf_files):
    size = f.stat().st_size
    magic = f.read_bytes()[:5]
    valid = 'OK' if magic == b'%PDF-' else 'INVALID'
    print(f'  {f} — {size} bytes — {valid}')
print(f'Total: {len(pdf_files)} PDFs')
"
```

Expected: 9 PDF files listed (1 in outputs/, 8 in docs/), all marked OK.

- [ ] **Step 3: Verify no .docx files remain in outputs/ or docs/**

```bash
python -c "
from pathlib import Path
docx = list(Path('outputs').glob('*.docx')) + list(Path('docs').glob('*.docx'))
if docx:
    print('ERROR: .docx files still present:', docx)
else:
    print('OK: no .docx files in outputs/ or docs/')
"
```

Expected: `OK: no .docx files in outputs/ or docs/`

- [ ] **Step 4: Run the full test suite one final time**

```bash
pytest tests/ -v --ignore=tests/test_llm_engine.py
```

Expected: all tests pass.

- [ ] **Step 5: Commit the updated outputs and final state**

```bash
git add outputs/ docs/
git commit -m "feat: pipeline now produces PDF documents; .docx outputs fully replaced"
```

---

## Self-Review

**Spec coverage check:**
- [x] 9 `.docx` → `.pdf` — all 9 covered across Tasks 3, 5, 6
- [x] Pure Python, no Word/LibreOffice — fpdf2 only, Task 1
- [x] Only `.docx` files changed — `.xlsx`, `.csv`, `.html`, `.json` untouched
- [x] `main.py` unchanged — verified, no changes proposed
- [x] Public signatures unchanged — `write_outputs()` and `write_docs()` return same `dict[str, Path]` shape
- [x] `analysis.md` unchanged — `_write_analysis_md()` not touched in any task
- [x] `requirements.txt` updated — Task 1
- [x] Tests updated — Tasks 2 and 4

**Placeholder scan:** No TBDs, no "implement later", all steps have explicit code.

**Type consistency:**
- `_make_pdf()` returns `FPDF` in both modules — consistent
- `_safe_text(text: str) -> str` — consistent
- `_render_doc_from_content_pdf()` has same call sites as old `_render_doc_from_content()` — consistent
- `_write_analysis_pdf` called in `write_docs()` with `(run_log, docs_dir)` — matches definition
- Return key `analysis_pdf` in `write_docs()` — matches test assertion in `test_doc_generator.py`
- All 8 static doc helpers return `.pdf` paths — consistent with test `expected_names` dict
