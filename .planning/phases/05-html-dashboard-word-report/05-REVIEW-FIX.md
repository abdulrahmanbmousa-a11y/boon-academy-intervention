---
phase: 05-html-dashboard-word-report
fixed_at: 2026-05-24T00:40:00+03:00
review_path: .planning/phases/05-html-dashboard-word-report/05-REVIEW.md
iteration: 1
findings_in_scope: 7
fixed: 7
skipped: 0
status: all_fixed
---

# Phase 05: Code Review Fix Report

**Fixed at:** 2026-05-24T00:40:00+03:00
**Source review:** .planning/phases/05-html-dashboard-word-report/05-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 7 (CR-01, CR-02, CR-03, WR-01, WR-02, WR-03, WR-04)
- Fixed: 7
- Skipped: 0

## Fixed Issues

### CR-01: Component Score Columns Excluded from Dashboard JSON

**Files modified:** `src/config.py`, `tests/test_output_generator.py`
**Commits:** `0702231`, `4885fde`
**Applied fix:** Added `COL_ATTENDANCE_COMPONENT`, `COL_PRACTICE_COMPONENT`, `COL_TREND_COMPONENT`,
and `COL_NOTES_COMPONENT` to `DISPLAY_COLS_DASHBOARD` in `config.py` (tuple now has 16 entries,
comment updated from "12 columns" to "16 columns"). Also added the four component columns to all
three test fixtures that build DataFrames passed to `_write_html_dashboard` (`sample_df`,
`full_sample_df`, and the inline `injection_df` in `test_html_dashboard_escape_script_tag`).

---

### CR-02: WhatsApp Copy Button / Summary Double-Encoding

**Files modified:** `src/templates/dashboard.html.j2`
**Commit:** `f0b8db4`
**Applied fix:** Replaced `${escapeHtml(summary)}` and `${escapeHtml(whatsapp)}` inside the
`detailTd.innerHTML` template literal with empty `<p>` placeholders. After `innerHTML` is set,
the two user-supplied text fields are assigned via `detailTd.querySelector('.summary-text').textContent`
and `detailTd.querySelector('.whatsapp-text').textContent`. The browser handles escaping
automatically through `textContent`, eliminating any risk of double-encoding pre-existing
entities in LLM output.

---

### CR-03: float('nan') Escapes NA Normalisation in _write_campus_dashboards

**Files modified:** `src/output_generator.py`
**Commit:** `67a3523`
**Applied fix:** In the NA-normalisation block inside `_write_campus_dashboards`, added an
explicit `elif isinstance(value, float) and pd.isna(value): value = None` check *before* the
existing `elif not isinstance(value, (str, int, float, bool))` guard. `float('nan')` is an
instance of `float` so it previously fell through to openpyxl as a raw NaN; now it is caught
and written as an empty cell. Also added `import math` and `import re` to the module-level
imports (needed by WR-02 and WR-03 respectively).

---

### WR-01: pd.NA Survives .where() — JSON Serialisation Crash

**Files modified:** `src/output_generator.py`
**Commit:** `67a3523`
**Applied fix:** In `_write_html_dashboard`, introduced an intermediate `display_df` variable
that casts the selected columns to object dtype before the `.where()` call:
`display_df = df_copy[display_cols].astype(object)`. The `.where(display_df.notna(), other=None)`
then operates on a plain object array where `pd.NA` has been converted to `np.nan`, which
`.where()` reliably replaces with Python `None` without the nullable array coercing it back.

---

### WR-02: student.get() Returns nan for Missing Facilitator Summary

**Files modified:** `src/output_generator.py`
**Commit:** `67a3523`
**Applied fix:** Added a private `_str_or_na(val: object) -> str` helper (placed between
`_write_html_dashboard` and `_write_report`) that returns `"N/A"` for `None`, `pd.NA`, and
`float('nan')`, and `str(val)` otherwise. Replaced the two `.get(...) or "N/A"` calls in
`_write_report` with `_str_or_na(student[cfg.COL_FACILITATOR_SUMMARY])` and
`_str_or_na(student[cfg.COL_RECOMMENDED_ACTION])`, using direct index access since the column
is always present.

---

### WR-03: Campus ID Used Raw in Filename — Path Traversal Risk

**Files modified:** `src/output_generator.py`
**Commit:** `67a3523`
**Applied fix:** Two changes in `_write_campus_dashboards`:
1. `ws.title = str(campus_id)[:31]` — caps the worksheet name to openpyxl's 31-character limit.
2. Before building the file path, `safe_campus_id = re.sub(r'[^\w\-]', '_', str(campus_id))`
   strips any characters that are illegal or path-meaningful (slashes, dots, colons, etc.),
   then uses `safe_campus_id` in the filename. The dict key `campus_{campus_id}` retains the
   original unsanitised value so callers receive the canonical key.

---

### WR-04: HTML lang Attribute Set to ar-001 for English UI

**Files modified:** `src/templates/dashboard.html.j2`
**Commit:** `b7f2b4e`
**Applied fix:** Changed `<html lang="ar-001">` to `<html lang="en">` on line 2 of the
template. The dashboard UI is entirely English; the `lang` attribute now correctly signals
this to browsers, screen readers, and search engines. Arabic content within cells (student
names, WhatsApp messages) will render correctly via the browser's Unicode bidirectional
algorithm; `dir="auto"` can be added to specific `<td>` or `<p>` elements if explicit RTL
support is needed in future.

---

## Skipped Issues

None — all 7 in-scope findings were successfully fixed.

---

_Fixed: 2026-05-24T00:40:00+03:00_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
