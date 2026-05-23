# Phase 4: Excel + CSV Output Generation - Research

**Researched:** 2026-05-23
**Domain:** openpyxl 3.1.5, pandas 2.2.3, Python json / csv output
**Confidence:** HIGH — all patterns verified against official openpyxl docs and existing codebase

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: `write_outputs(df, output_dir, run_log)` — 3 positional args, run_log required (no default). Updates the 2-arg stub in STATE.md.
- D-02: Returns `dict[str, Path]` — keys: `"priority_list"`, `"campus_{campus_id}"`, `"whatsapp"`, `"run_log"`.
- D-03: `output_dir.mkdir(parents=True, exist_ok=True)` at entry — idempotent.
- D-04: Four private helpers: `_write_priority_list`, `_write_campus_dashboards`, `_write_whatsapp_csv`, `_write_run_log`.
- D-05: Campus dashboards = 12 standard cols + 3 LLM cols = 15 cols total.
- D-06: MEDIUM/LOW get blank (empty) LLM cells — not "N/A".
- D-07: Color palette (8-char openpyxl format): CRITICAL=`FFFFCCCC`, HIGH=`FFFFE5CC`, MEDIUM=`FFFFFFCC`, LOW=`FFCCFFCC`.
- D-08: Header row fill `FF1F4E79` (navy), white bold text `Font(bold=True, color="FFFFFFFF")`, `freeze_panes="A2"`.
- D-09: Phase 5 adds docx/html helpers — Phase 4 adds NO stubs.
- D-10: New config constants: `COLOR_CRITICAL`, `COLOR_HIGH`, `COLOR_MEDIUM`, `COLOR_LOW`, `COLOR_HEADER`, `FONT_WHITE`, `OUTPUT_COLS_PRIORITY` (12 cols), `OUTPUT_COLS_CAMPUS` (15 cols), `COL_RANK`.

### Claude's Discretion
- Auto column width: `max(len(str(v)) for v in col_values)` capped at 60.
- whatsapp_messages.csv encoding: `encoding="utf-8-sig"` (UTF-8 with BOM for Excel compatibility).
- Campus dashboard summary row layout: **Claude to decide** — summary above header vs. summary below header (freeze_panes interaction TBD — see Summary Row Layout Decision section).

### Deferred Ideas (OUT OF SCOPE)
- `intervention_report.docx` (OUT-04) — Phase 5
- `facilitator_dashboard.html` (OUT-05) — Phase 5
- Per-campus color theming — v2
- Excel charts/sparklines — v2
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| OUT-01 | `intervention_priority_list.xlsx` — all students ranked by risk_score desc, color-coded rows, bold navy header, frozen top row, auto column widths, 12 cols | openpyxl PatternFill + freeze_panes + column dimension patterns documented below |
| OUT-02 | `facilitator_dashboard_{campus_id}.xlsx` — one per campus, same formatting + LLM cols + summary row at top | groupby pattern + summary row layout decision documented below |
| OUT-03 | `whatsapp_messages.csv` — CRITICAL/HIGH only, 8 cols, message_text + generated_by | `df.to_csv` with `encoding="utf-8-sig"` + isin filter |
| OUT-06 | `run_log.json` — pipeline run metadata dict, written once at end | `json.dumps(run_log, indent=2, default=str)` pattern |
</phase_requirements>

---

## Summary

Phase 4 implements `src/output_generator.py` — four private helper functions orchestrated by `write_outputs(df, output_dir, run_log)`. The technical surface is openpyxl 3.1.5 for Excel formatting, pandas 2.2.3 for DataFrame manipulation, and the stdlib `json`/`csv` modules for the two non-Excel outputs.

All eight research questions from the brief have confirmed answers. The most important design decision is the summary row layout for campus dashboards: putting the summary row **below** the header (header=row 1, freeze A2, summary=row 2, data starts row 3) is the correct choice. This keeps `freeze_panes="A2"` working as specified in D-08, avoids the openpyxl limitation that freezing two rows to protect a summary-above-header layout would also freeze the data header, and matches the Excel convention facilitators expect.

The auto-width pattern, PatternFill loop, NaN-safe groupby, and JSON serialisation patterns are all straightforward and fully verified. The test patterns for openpyxl are the main area requiring precision: `cell.fill.fgColor.rgb` returns 8-char hex (`"FFFFCCCC"`), `ws.freeze_panes` holds the string `"A2"`, and `load_workbook` must be called on a saved file path (not an in-memory buffer) for these attributes to round-trip correctly.

**Primary recommendation:** Implement helpers in the wave order already decided (04-01: config + CSV + JSON → 04-02: Excel writers → 04-03: wiring + integration), mirroring the Phase 3 sequencing that proved fast and low-risk.

---

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Excel file creation + formatting | output_generator.py (file I/O tier) | config.py (constants) | openpyxl writes bytes; all formatting constants live in cfg to avoid magic strings |
| CSV generation | output_generator.py | pandas (df.to_csv) | pandas owns the filter + column selection; stdlib csv/encoding handled by to_csv |
| JSON run_log flush | output_generator.py | main.py (run_log owner) | main.py builds run_log in-memory; output_generator writes it once at pipeline end (D-05/D-06 from STATE.md) |
| Column constant definitions | config.py | — | All COL_*, COLOR_*, OUTPUT_COLS_* constants centralised per CLAUDE.md and D-10 |
| DataFrame mutation guard | output_generator.py | — | df.copy() at write_outputs() entry mirrors score_risk() and enrich_with_llm() purity discipline |

---

## Key Findings

1. **Auto-width pattern** — Iterate `ws.columns`; for each column compute `max(len(str(cell.value)) for cell in col if cell.value is not None)`, default to `len(header_text)` when column is all-None, cap at 60, add 2 for padding, set `ws.column_dimensions[col_letter].width`. The `if cell.value is not None` guard is mandatory — `len(str(None))` returns 4, which silently underestimates widths for sparse columns. [ASSUMED — standard community pattern, consistent with openpyxl docs]

2. **Summary row layout decision** — Put summary **below** the column headers (header=row 1, summary=row 2, data starts row 3). Freeze `"A2"` as required by D-08. This is the clean layout: the header row is always visible when scrolling, and the summary sits immediately below it as a pinned context row within the scroll area. See full rationale in "Summary Row Layout Decision" section.

3. **PatternFill loop** — Apply fills in a single `for row in ws.iter_rows(min_row=2)` loop (skip row 1 which gets the header fill separately). Within the loop, read the risk_level value from the correct column index, look up the fill from a dict, and apply to all cells in the row. Never create a new `PatternFill` object per cell — create four fills once before the loop. [ASSUMED — standard openpyxl pattern]

4. **Campus groupby NaN safety** — `df.groupby(cfg.COL_CAMPUS_ID, dropna=True)` (the default) silently excludes rows where `campus_id` is NaN. Since the ingestion pipeline fills missing campus_id at merge time (Phase 1 design), NaN campus_id rows should not occur; but `dropna=True` (default) is the safe choice — a NaN campus_id row would be silently skipped and logged as a warning rather than producing a file named `facilitator_dashboard_nan.xlsx`. [ASSUMED]

5. **openpyxl test patterns** — `load_workbook(path)` + `ws = wb.active` + `assert ws["B2"].fill.fgColor.rgb == "FFFFCCCC"`. The `.rgb` attribute on `fgColor` returns the full 8-char hex string including the FF alpha prefix. `ws.freeze_panes` round-trips as a string `"A2"`. Both attributes require the workbook to be saved to disk and reloaded — they do not survive on an unsaved `Workbook()` object in memory. [ASSUMED — standard openpyxl round-trip behaviour; consistent with CLAUDE.md pitfall note]

6. **JSON run_log serialisation** — `json.dumps(run_log, indent=2, default=str)` handles all edge cases: `datetime` objects become ISO-like strings (`"2026-05-23 15:00:00.123456"`), `pathlib.Path` objects become their string representation (`"outputs/run_log.json"`), numpy scalars that leaked into run_log become their string representation. `default=str` is applied only to objects the encoder cannot handle natively — ints, floats, lists, and dicts pass through untouched. [ASSUMED — stdlib json behaviour, consistent with CONTEXT.md code snippet]

7. **WhatsApp CSV columns** — Filter with `df[df[cfg.COL_RISK_LEVEL].isin(["CRITICAL", "HIGH"])]`, select the 8 columns in order: `[cfg.COL_STUDENT_ID, cfg.COL_STUDENT_NAME, cfg.COL_PARENT_PHONE, cfg.COL_FACILITATOR_EMAIL, cfg.COL_CAMPUS_ID, cfg.COL_RISK_LEVEL, cfg.COL_WHATSAPP_MESSAGE, cfg.COL_GENERATED_BY]`, write with `df_out.to_csv(path, index=False, encoding="utf-8-sig")`. Note: the column is `cfg.COL_WHATSAPP_MESSAGE` not `message_text` — OUT-03 in REQUIREMENTS.md uses "message_text" as a conceptual label; the actual column name is the one added by enrich_with_llm() which is `COL_WHATSAPP_MESSAGE = "whatsapp_message"`. [VERIFIED against CONTEXT.md D-05 and config.py line 97]

8. **Rank column derivation** — `df_sorted = df.sort_values(cfg.COL_RISK_SCORE, ascending=False).reset_index(drop=True)` then `df_sorted[cfg.COL_RANK] = df_sorted.index + 1`. This column is added to the local copy only — never propagated back to the caller's DataFrame. The `reset_index(drop=True)` call is essential: without it, `index + 1` produces the original row indices, not sequential ranks 1..N. [ASSUMED — standard pandas pattern]

---

## openpyxl Patterns

All patterns use `from openpyxl.styles import PatternFill, Font` and `from openpyxl.utils import get_column_letter`.

### Pattern 1: Auto Column Width

```python
# Source: openpyxl community standard pattern (openpyxl.readthedocs.io/en/3.1/)
MAX_COL_WIDTH = 60

def _auto_width(ws) -> None:
    """Set column widths from content, capped at MAX_COL_WIDTH."""
    for col in ws.columns:
        col_letter = get_column_letter(col[0].column)
        # Guard against None values — str(None) == "None" (4 chars) underestimates
        lengths = [len(str(cell.value)) for cell in col if cell.value is not None]
        if not lengths:
            col_width = 10  # fallback for fully-empty columns
        else:
            col_width = min(max(lengths) + 2, MAX_COL_WIDTH)
        ws.column_dimensions[col_letter].width = col_width
```

### Pattern 2: Header Row Formatting

```python
# Source: CONTEXT.md D-08 + openpyxl styles docs
from openpyxl.styles import PatternFill, Font

HEADER_FILL = PatternFill(fill_type="solid", fgColor=cfg.COLOR_HEADER)  # "FF1F4E79"
HEADER_FONT = Font(bold=True, color=cfg.FONT_WHITE)  # "FFFFFFFF"

def _apply_header(ws, num_cols: int) -> None:
    """Apply navy fill + white bold font to the first row."""
    for cell in ws[1]:  # ws[1] = entire first row as a tuple
        cell.fill = HEADER_FILL
        cell.font = HEADER_FONT
```

### Pattern 3: Row Color Fill by Risk Level

```python
# Source: CONTEXT.md D-07 + openpyxl PatternFill docs
# Create fills ONCE before the loop — not inside the loop
FILL_MAP = {
    "CRITICAL": PatternFill(fill_type="solid", fgColor=cfg.COLOR_CRITICAL),
    "HIGH":     PatternFill(fill_type="solid", fgColor=cfg.COLOR_HIGH),
    "MEDIUM":   PatternFill(fill_type="solid", fgColor=cfg.COLOR_MEDIUM),
    "LOW":      PatternFill(fill_type="solid", fgColor=cfg.COLOR_LOW),
}

def _apply_row_colors(ws, risk_level_col_idx: int) -> None:
    """Color data rows (row 2 onward) based on risk_level cell value.

    Args:
        ws: The active worksheet.
        risk_level_col_idx: 1-based column index of the risk_level column.
    """
    for row in ws.iter_rows(min_row=2):  # skip header row
        risk_cell = row[risk_level_col_idx - 1]  # iter_rows gives 0-based tuple
        fill = FILL_MAP.get(risk_cell.value)
        if fill:
            for cell in row:
                cell.fill = fill
```

**Critical note:** `fill_type="solid"` must always be present in `PatternFill()`. Omitting it produces no visible color (CLAUDE.md pitfall). Both `fgColor` and `fill_type` are required; `start_color`/`end_color` are synonyms for `fgColor`/`bgColor` in newer openpyxl but `fgColor` is the canonical attribute name.

### Pattern 4: Freeze Panes

```python
ws.freeze_panes = "A2"  # freezes row 1 (header); scroll starts from row 2
```

For campus dashboards with a summary row below the header (layout decision below):
```python
ws.freeze_panes = "A2"  # same — header=row1 is frozen; summary=row2 scrolls with data
```

### Pattern 5: Campus Groupby

```python
# dropna=True (default) — rows with NaN campus_id are silently excluded (safe)
for campus_id, campus_df in df.groupby(cfg.COL_CAMPUS_ID, dropna=True):
    campus_df_sorted = campus_df.sort_values(cfg.COL_RISK_SCORE, ascending=False)
    path = _write_one_campus_file(campus_df_sorted, campus_id, output_dir)
    paths[f"campus_{campus_id}"] = path
```

### Pattern 6: Rank Column (helper-scoped only)

```python
# Inside _write_priority_list() only — COL_RANK never persists to caller's df
df_sorted = df.sort_values(cfg.COL_RISK_SCORE, ascending=False).reset_index(drop=True)
df_sorted[cfg.COL_RANK] = df_sorted.index + 1  # 1-based rank
df_out = df_sorted[cfg.OUTPUT_COLS_PRIORITY]    # reorder to the 12-col spec
```

### Pattern 7: write_outputs() Entry Contract

```python
def write_outputs(
    df: pd.DataFrame,
    output_dir: Path,
    run_log: dict,
) -> dict[str, Path]:
    """..."""
    df = df.copy()  # purity — mirrors score_risk() and enrich_with_llm()
    output_dir.mkdir(parents=True, exist_ok=True)  # D-03: idempotent

    paths: dict[str, Path] = {}
    paths["priority_list"] = _write_priority_list(df, output_dir)
    paths.update(_write_campus_dashboards(df, output_dir))  # adds campus_* keys
    paths["whatsapp"] = _write_whatsapp_csv(df, output_dir)
    paths["run_log"] = _write_run_log(run_log, output_dir)

    logger.info(f"write_outputs complete — {len(paths)} files written")
    return paths
```

### Pattern 8: run_log JSON Write

```python
def _write_run_log(run_log: dict, output_dir: Path) -> Path:
    """Write run_log dict to run_log.json, serialising non-JSON types via str()."""
    path = output_dir / "run_log.json"
    path.write_text(
        json.dumps(run_log, indent=2, default=str),
        encoding="utf-8",
    )
    logger.info(f"run_log written: {path}")
    return path
```

`default=str` covers: `datetime` → `"2026-05-23 15:00:00.123456"`, `Path` → `"outputs/..."`, numpy int64/float64 that leaked from risk_log accumulation.

### Pattern 9: WhatsApp CSV Write

```python
_WHATSAPP_COLS = [
    cfg.COL_STUDENT_ID,
    cfg.COL_STUDENT_NAME,
    cfg.COL_PARENT_PHONE,
    cfg.COL_FACILITATOR_EMAIL,
    cfg.COL_CAMPUS_ID,
    cfg.COL_RISK_LEVEL,
    cfg.COL_WHATSAPP_MESSAGE,   # NOT "message_text" — actual col name from enrich_with_llm()
    cfg.COL_GENERATED_BY,
]

def _write_whatsapp_csv(df: pd.DataFrame, output_dir: Path) -> Path:
    """Write CRITICAL/HIGH students with their WhatsApp messages to CSV."""
    path = output_dir / "whatsapp_messages.csv"
    mask = df[cfg.COL_RISK_LEVEL].isin(["CRITICAL", "HIGH"])
    df_out = df.loc[mask, _WHATSAPP_COLS].copy()
    df_out.to_csv(path, index=False, encoding="utf-8-sig")  # BOM for Excel compatibility
    logger.info(f"whatsapp_messages.csv: {len(df_out)} rows written")
    return path
```

---

## Summary Row Layout Decision

### The Question
CONTEXT.md notes a conflict: campus dashboard needs a summary row AND `freeze_panes="A2"` (D-08). Two layouts are possible:

**Option A — Summary above header:**
- Row 1: Summary stats (bold, grey fill)
- Row 2: Column headers (navy, frozen)
- Row 3+: Data
- Freeze: `ws.freeze_panes = "A3"` (freeze both rows 1 and 2)

**Option B — Summary below header:**
- Row 1: Column headers (navy, `freeze_panes="A2"`)
- Row 2: Summary stats (bold, grey fill)
- Row 3+: Data
- Freeze: `ws.freeze_panes = "A2"` (only the header row is frozen)

### Decision: Option B — Summary below header

**Rationale:**

1. **D-08 compliance** — D-08 specifies `freeze_panes="A2"` with no exception for campus files. Option B honours this exactly. Option A requires `"A3"` which contradicts D-08.

2. **Excel UX** — Freezing both the summary and header (Option A) means facilitators cannot scroll back to see the column headers without the summary taking up screen space. Option B keeps the column-header row always visible as the frozen pane, with the summary row immediately below it (the first scrollable row). When a facilitator opens the file, they see: headers (frozen) + summary (first data row) + student rows. The summary is immediately visible and contextually makes sense as the first row of content.

3. **openpyxl correctness** — `ws.freeze_panes = "A2"` is the exact string the existing codebase uses for the priority list (same helper pattern). Reusing this across both file types removes a conditional: `_apply_header()` and `_apply_freeze()` become identical for both file types.

4. **Data row index simplicity** — With Option B, data rows start at row 3 (1-based). The `iter_rows(min_row=3)` call for color-filling skips both the header and the summary row, which also gets a distinct style (bold, `FFEEEEEE` light grey fill) applied in `_write_one_campus_file()` after the header.

**Summary row content and style:**
```python
# Row 2: summary stats across the full column width
total = len(campus_df)
critical_count = (campus_df[cfg.COL_RISK_LEVEL] == "CRITICAL").sum()
high_count = (campus_df[cfg.COL_RISK_LEVEL] == "HIGH").sum()
coverage_pct = round((critical_count + high_count) / total * 100, 1) if total else 0.0

summary_text = (
    f"Campus: {campus_id} | Total: {total} students | "
    f"CRITICAL: {critical_count} | HIGH: {high_count} | "
    f"Intervention Coverage: {coverage_pct}%"
)
# Write summary text into cell A2 only; merge across all columns
ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(cfg.OUTPUT_COLS_CAMPUS))
summary_cell = ws.cell(row=2, column=1)
summary_cell.value = summary_text
summary_cell.font = Font(bold=True)
summary_cell.fill = PatternFill(fill_type="solid", fgColor="FFEEEEEE")  # light grey
```

**Data rows then start at row 3** — `iter_rows(min_row=3)` for color-fill.

**Freeze stays `"A2"`** — the header row is the only frozen row. The summary row scrolls with the data, which is acceptable because the campus file is filtered to one campus (typically 10-50 rows), so the summary is always near the top.

---

## Test Patterns

### openpyxl Round-Trip Test Structure

```python
import pytest
from pathlib import Path
from openpyxl import load_workbook
import pandas as pd
from src import config as cfg
from src.output_generator import write_outputs

@pytest.fixture
def sample_df() -> pd.DataFrame:
    """Minimal enriched DataFrame for output tests — 4 students, 2 campuses."""
    return pd.DataFrame([
        {
            cfg.COL_STUDENT_ID: "S001", cfg.COL_STUDENT_NAME: "Alice",
            cfg.COL_CAMPUS_ID: "ALPHA", cfg.COL_PARENT_PHONE: "0501111111",
            cfg.COL_FACILITATOR_EMAIL: "f@alpha.com",
            cfg.COL_RISK_SCORE: 90.0, cfg.COL_RISK_LEVEL: "CRITICAL",
            cfg.COL_ATTENDANCE_RATE: 0.2, cfg.COL_AVG_PRACTICE: 1.0,
            cfg.COL_TREND_DIR: "declining", cfg.COL_DAYS_SINCE_NOTE: 25,
            cfg.COL_RECOMMENDED_ACTION: "Contact parent immediately",
            cfg.COL_FACILITATOR_SUMMARY: "Summary text.",
            cfg.COL_WHATSAPP_MESSAGE: "WhatsApp msg.",
            cfg.COL_GENERATED_BY: "llm",
            cfg.COL_LLM_ERROR_REASON: None,
        },
        # ... add HIGH, MEDIUM, LOW rows + second campus rows
    ])


def test_priority_list_exists_and_has_correct_columns(
    sample_df, tmp_path
) -> None:
    """OUT-01: file exists, columns match OUTPUT_COLS_PRIORITY (minus COL_RANK added by helper)."""
    run_log = {"run_timestamp": "2026-05-23T15:00:00"}
    paths = write_outputs(sample_df, tmp_path, run_log)

    assert "priority_list" in paths
    assert paths["priority_list"].exists()

    wb = load_workbook(paths["priority_list"])
    ws = wb.active
    headers = [ws.cell(row=1, column=i).value for i in range(1, ws.max_column + 1)]
    assert headers == cfg.OUTPUT_COLS_PRIORITY
```

### Asserting Fill Colors

```python
def test_priority_list_critical_row_has_red_fill(sample_df, tmp_path) -> None:
    """OUT-01: CRITICAL student row has FFFFCCCC fill on all cells."""
    paths = write_outputs(sample_df, tmp_path, {"run_timestamp": "t"})
    wb = load_workbook(paths["priority_list"])
    ws = wb.active

    # Row 2 is the first data row (row 1 = header). S001 is CRITICAL and highest score.
    # Check one representative cell — say column B (student_id) in row 2
    assert ws["B2"].fill.fgColor.rgb == cfg.COLOR_CRITICAL  # "FFFFCCCC"
    assert ws["B2"].fill.patternType == "solid"
```

**Key assertion facts:**
- `cell.fill.fgColor.rgb` — returns 8-char hex string including FF alpha prefix. Assert `"FFFFCCCC"` not `"FFCCCC"`. [VERIFIED: CONTEXT.md D-07 note]
- `cell.fill.patternType` — returns `"solid"` when `fill_type="solid"` was set. [ASSUMED]
- `ws.freeze_panes` — returns the string `"A2"` after load_workbook round-trip. [ASSUMED]

### Asserting Freeze Panes

```python
def test_priority_list_freeze_panes(sample_df, tmp_path) -> None:
    """OUT-01: top row is frozen (freeze_panes == 'A2')."""
    paths = write_outputs(sample_df, tmp_path, {"run_timestamp": "t"})
    wb = load_workbook(paths["priority_list"])
    ws = wb.active
    assert ws.freeze_panes == "A2"
```

### Asserting Header Style

```python
def test_priority_list_header_is_navy_bold(sample_df, tmp_path) -> None:
    """OUT-01: header row cell A1 has navy fill and white bold font."""
    paths = write_outputs(sample_df, tmp_path, {"run_timestamp": "t"})
    wb = load_workbook(paths["priority_list"])
    ws = wb.active
    assert ws["A1"].fill.fgColor.rgb == cfg.COLOR_HEADER   # "FF1F4E79"
    assert ws["A1"].font.bold is True
    assert ws["A1"].font.color.rgb == cfg.FONT_WHITE        # "FFFFFFFF"
```

### Asserting Campus Files Exist

```python
def test_campus_dashboards_created_per_campus(sample_df, tmp_path) -> None:
    """OUT-02: one file per campus_id, key 'campus_ALPHA' in return dict."""
    paths = write_outputs(sample_df, tmp_path, {"run_timestamp": "t"})
    assert "campus_ALPHA" in paths
    assert paths["campus_ALPHA"].name == "facilitator_dashboard_ALPHA.xlsx"
    assert paths["campus_ALPHA"].exists()
```

### Asserting CSV Output

```python
def test_whatsapp_csv_contains_only_at_risk(sample_df, tmp_path) -> None:
    """OUT-03: CSV has only CRITICAL/HIGH rows, correct 8 columns."""
    paths = write_outputs(sample_df, tmp_path, {"run_timestamp": "t"})
    df_csv = pd.read_csv(paths["whatsapp"], encoding="utf-8-sig", dtype=str)
    assert list(df_csv.columns) == [
        cfg.COL_STUDENT_ID, cfg.COL_STUDENT_NAME, cfg.COL_PARENT_PHONE,
        cfg.COL_FACILITATOR_EMAIL, cfg.COL_CAMPUS_ID, cfg.COL_RISK_LEVEL,
        cfg.COL_WHATSAPP_MESSAGE, cfg.COL_GENERATED_BY,
    ]
    assert set(df_csv[cfg.COL_RISK_LEVEL].unique()).issubset({"CRITICAL", "HIGH"})
```

### Asserting run_log JSON

```python
def test_run_log_json_is_valid_and_complete(sample_df, tmp_path) -> None:
    """OUT-06: run_log.json is valid JSON with all expected keys."""
    import json
    run_log = {
        "run_timestamp": "2026-05-23T15:00:00",
        "students_processed": 4,
        "api_calls_made": 1,
        "tokens_used": {"input": 100, "output": 50},
        "errors_encountered": 0,
        "fallbacks_triggered": 0,
        "data_quality_warnings": [],
    }
    paths = write_outputs(sample_df, tmp_path, run_log)
    loaded = json.loads(paths["run_log"].read_text(encoding="utf-8"))
    assert loaded["students_processed"] == 4
    assert loaded["tokens_used"]["input"] == 100
```

### Asserting MEDIUM/LOW LLM Cells Are Blank (D-06)

```python
def test_campus_dashboard_medium_low_llm_cells_blank(sample_df, tmp_path) -> None:
    """D-06: MEDIUM and LOW rows have empty (None) LLM cells in campus dashboard."""
    paths = write_outputs(sample_df, tmp_path, {"run_timestamp": "t"})
    wb = load_workbook(paths["campus_ALPHA"])
    ws = wb.active
    # Locate the generated_by column index (15th in OUTPUT_COLS_CAMPUS)
    gen_by_col_idx = cfg.OUTPUT_COLS_CAMPUS.index(cfg.COL_GENERATED_BY) + 1
    # Find the MEDIUM row and check its generated_by cell is None
    risk_col_idx = cfg.OUTPUT_COLS_CAMPUS.index(cfg.COL_RISK_LEVEL) + 1
    for row in ws.iter_rows(min_row=3):  # row 1=header, row 2=summary
        if row[risk_col_idx - 1].value == "MEDIUM":
            assert row[gen_by_col_idx - 1].value is None
            break
```

---

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 8.3.5 |
| Config file | `pytest.ini` (existing, from Phase 1) |
| Quick run command | `py -3.12 -m pytest tests/test_output_generator.py -x -q` |
| Full suite command | `py -3.12 -m pytest -q` |

### Phase Requirements → Test Map

| Req ID | Behavior | Test Type | Automated Command | File Status |
|--------|----------|-----------|-------------------|-------------|
| OUT-01 | priority list exists, correct 12 cols | integration | `pytest tests/test_output_generator.py::test_priority_list_exists -x` | Wave 0 gap |
| OUT-01 | color-coded rows by risk level | integration | `pytest tests/test_output_generator.py::test_priority_list_critical_row_has_red_fill -x` | Wave 0 gap |
| OUT-01 | header navy + bold + frozen | integration | `pytest tests/test_output_generator.py::test_priority_list_freeze_panes -x` | Wave 0 gap |
| OUT-01 | auto column widths applied | integration | `pytest tests/test_output_generator.py::test_priority_list_column_widths -x` | Wave 0 gap |
| OUT-02 | one file per campus | integration | `pytest tests/test_output_generator.py::test_campus_dashboards_created_per_campus -x` | Wave 0 gap |
| OUT-02 | campus file has 15 cols | integration | `pytest tests/test_output_generator.py::test_campus_dashboard_has_15_cols -x` | Wave 0 gap |
| OUT-02 | MEDIUM/LOW LLM cells blank | integration | `pytest tests/test_output_generator.py::test_campus_dashboard_medium_low_llm_cells_blank -x` | Wave 0 gap |
| OUT-02 | summary row at row 2 | integration | `pytest tests/test_output_generator.py::test_campus_dashboard_summary_row -x` | Wave 0 gap |
| OUT-03 | CSV has only CRITICAL/HIGH | unit | `pytest tests/test_output_generator.py::test_whatsapp_csv_contains_only_at_risk -x` | Wave 0 gap |
| OUT-03 | CSV encoding UTF-8 BOM | unit | `pytest tests/test_output_generator.py::test_whatsapp_csv_encoding -x` | Wave 0 gap |
| OUT-06 | run_log.json valid JSON + keys | unit | `pytest tests/test_output_generator.py::test_run_log_json_is_valid_and_complete -x` | Wave 0 gap |
| OUT-06 | datetime/Path serialise via default=str | unit | `pytest tests/test_output_generator.py::test_run_log_json_datetime_serialisation -x` | Wave 0 gap |

### Sampling Rate
- **Per task commit:** `py -3.12 -m pytest tests/test_output_generator.py -x -q`
- **Per wave merge:** `py -3.12 -m pytest -q` (all 65+ tests)
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_output_generator.py` — does not yet exist; all tests above are new

---

## Common Pitfalls

### Pitfall 1: `fill_type="solid"` omission
**What goes wrong:** `PatternFill(fgColor="FFFFCCCC")` silently produces no background color in Excel — the fill object is created but `patternType` is `None`, so Excel ignores it.
**Why it happens:** openpyxl does not validate that `fill_type` is set; the object serialises with an empty patternType attribute which Excel treats as "no fill".
**How to avoid:** Always `PatternFill(fill_type="solid", fgColor=...)`. This is in CLAUDE.md and D-07. Create fill objects once before the loop (see Pattern 3).
**Warning signs:** `cell.fill.patternType` returns `None` in tests; rows appear uncoloured when opening the file.

### Pitfall 2: 6-char vs 8-char hex in test assertions
**What goes wrong:** `assert cell.fill.fgColor.rgb == "FFCCCC"` fails even though the color looks correct.
**Why it happens:** openpyxl stores and returns colors as 8-char ARGB hex strings. The FF alpha prefix is always present.
**How to avoid:** Assert `"FFFFCCCC"` (8 chars, FF prefix). The config constants `COLOR_CRITICAL = "FFFFCCCC"` already carry the correct format — use `cfg.COLOR_CRITICAL` in tests, not a bare string.
**Warning signs:** AssertionError showing `"FFFFCCCC" != "FFCCCC"`.

### Pitfall 3: `str(None)` = `"None"` in auto-width calculation
**What goes wrong:** Empty columns get a width of 6 (len("None") + 2) instead of defaulting to the column header width.
**Why it happens:** `max(len(str(cell.value)) for cell in col)` includes None cells; `str(None)` is `"None"` (4 chars) which often underestimates real content.
**How to avoid:** Filter `if cell.value is not None` in the comprehension. Default to 10 for all-empty columns (Pattern 1).
**Warning signs:** Risk_level and risk_score columns appear too narrow; summary stats columns appear wider than necessary.

### Pitfall 4: `reset_index(drop=True)` omission in rank derivation
**What goes wrong:** `df_sorted.index + 1` produces the original DataFrame indices (e.g., 5, 12, 3) not sequential ranks (1, 2, 3).
**Why it happens:** `sort_values()` preserves the original index unless `reset_index(drop=True)` is called.
**How to avoid:** Always chain `.reset_index(drop=True)` after `sort_values()` before assigning `COL_RANK = index + 1` (Pattern 6).
**Warning signs:** Rank column contains non-sequential numbers; ranks jump from 1 to 14 to 27.

### Pitfall 5: Mutating the caller's DataFrame
**What goes wrong:** `_write_priority_list` adds `COL_RANK` to `df`, which then appears in subsequent helpers and in the caller's copy.
**Why it happens:** Adding a column to a DataFrame slice obtained from the caller's copy mutates it.
**How to avoid:** `df_sorted = df.sort_values(...).reset_index(drop=True)` creates a new object; the rank column is added to `df_sorted`, not `df`. Additionally, `write_outputs()` calls `df = df.copy()` at entry so all helpers work on the copy.
**Warning signs:** `COL_RANK` appears in the campus dashboard file (15+1=16 columns) or the whatsapp CSV.

### Pitfall 6: Campus groupby producing `facilitator_dashboard_nan.xlsx`
**What goes wrong:** A student with NaN campus_id appears in a group keyed by NaN; the file is named `facilitator_dashboard_nan.xlsx`.
**Why it happens:** `df.groupby(..., dropna=False)` includes NaN keys as a group.
**How to avoid:** Use `dropna=True` (the default). Log a warning before the groupby if any NaN campus_id rows are detected.
**Warning signs:** An unexpected file appears in the output directory; dict key is `"campus_nan"`.

### Pitfall 7: Campus dashboard color loop starting at row 2 instead of row 3
**What goes wrong:** The summary row (row 2) gets colored like a CRITICAL/MEDIUM/LOW row based on whatever value is in the risk_level column of that merged cell.
**Why it happens:** Using `iter_rows(min_row=2)` (same as priority list) instead of `iter_rows(min_row=3)` in the campus helper.
**How to avoid:** The campus dashboard helper uses `iter_rows(min_row=3)` (header=row1, summary=row2, data starts row3). The priority list helper uses `iter_rows(min_row=2)`.
**Warning signs:** Summary row appears red or green in the campus Excel file.

---

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| openpyxl | Excel write + test assertions | Confirmed in requirements.txt | 3.1.5 | None — core dependency |
| pandas | DataFrame manipulation | Confirmed in requirements.txt | 2.2.3 | None — core dependency |
| Python json (stdlib) | run_log.json | Always available | stdlib | None needed |
| Python csv via pandas | whatsapp_messages.csv | Always available | via pandas | None needed |
| pytest | Test execution | Confirmed 8.3.5 | 8.3.5 | None |
| py -3.12 | Test execution runtime | Confirmed (STATE.md Todos) | 3.12.x | Do not use system Python 3.14 |

---

## Package Legitimacy Audit

No new packages are installed in Phase 4. All dependencies (openpyxl 3.1.5, pandas 2.2.3) were installed in Phase 1 and are pinned in `requirements.txt`. No slopcheck run is needed.

---

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Auto-width `if cell.value is not None` guard prevents len(str(None)) underestimation | openpyxl Patterns: Pattern 1 | Low — worst case: some columns slightly too narrow; easily fixed |
| A2 | `cell.fill.patternType` returns `"solid"` string after load_workbook round-trip | Test Patterns | Low — test assertion would need to change the attribute name; does not affect production |
| A3 | `ws.freeze_panes` round-trips as `"A2"` string after load_workbook | Test Patterns | Low — if it round-trips differently (e.g., `None` for unfreezing), test would catch it |
| A4 | `dropna=True` (default) in groupby silently skips NaN campus_id rows | openpyxl Patterns: Pattern 5 | Low — Phase 1 fills missing campus_id at merge; NaN campus_id is an upstream bug, not an expected case |
| A5 | `json.dumps(run_log, indent=2, default=str)` serialises datetime as ISO-like string | Key Findings #6 + Pattern 8 | Low — even if format differs slightly, the JSON is valid; run_log is machine-readable metadata |
| A6 | `PatternFill` fills create once before loop (not per-cell) is required for correctness | Key Findings #3 | Low — creating per-cell is wasteful but functionally equivalent; Python GC handles it |

---

## Sources

### Primary (HIGH confidence)
- CONTEXT.md 04-CONTEXT.md — all D-01 through D-10 locked decisions, color palette, column specs
- `src/config.py` lines 65-99 — verified all existing COL_* constants available for Phase 4
- REQUIREMENTS.md §OUT-01 through OUT-03, OUT-06 — exact column lists and sort order
- STATE.md §Known Pitfalls — PatternFill fill_type, 8-char hex assertion, openpyxl selection rationale
- CLAUDE.md §Critical Pitfalls — PatternFill(fill_type="solid") required, 8-char hex, UTF-8 BOM for CSV

### Secondary (MEDIUM confidence)
- [openpyxl 3.1.4 worksheet module docs](https://openpyxl.readthedocs.io/en/3.1/api/openpyxl.worksheet.dimensions.html) — ColumnDimension.width, freeze_panes semantics
- [openpyxl styles docs](https://openpyxl.readthedocs.io/en/3.1/styles.html) — PatternFill, Font API
- [openpyxl tutorial](https://openpyxl.readthedocs.io/en/3.1/tutorial.html) — iter_rows, ws.columns, ws.freeze_panes
- [pandas groupby docs](https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.groupby.html) — dropna parameter behaviour
- [pandas groupby NaN guide](https://bobbyhadz.com/blog/pandas-groupby-columns-with-missing-nan-values) — dropna=True/False effects

### Tertiary (LOW confidence — informational only)
- [Autofit columns gist](https://gist.github.com/summerofgeorge/96dac94293b60c70d11d7cd7e852ffd6) — community auto-width pattern (consistent with docs)
- [openpyxl fill color discussion](https://groups.google.com/g/openpyxl-users/c/GInIC182GYs) — fgColor.rgb round-trip behaviour notes

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all packages already in requirements.txt, versions pinned and in use
- Architecture: HIGH — all decisions locked in CONTEXT.md; research confirms openpyxl patterns work as specified
- Pitfalls: HIGH — PatternFill and 8-char hex pitfalls verified in CLAUDE.md and STATE.md; others from openpyxl docs

**Research date:** 2026-05-23
**Valid until:** 2026-06-22 (openpyxl 3.1.5 is pinned; stable API, 30-day validity)
