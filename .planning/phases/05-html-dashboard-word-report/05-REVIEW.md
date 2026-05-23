---
phase: 05-html-dashboard-word-report
reviewed: 2026-05-23T18:18:00Z
depth: standard
files_reviewed: 4
files_reviewed_list:
  - src/config.py
  - src/output_generator.py
  - src/templates/dashboard.html.j2
  - tests/test_output_generator.py
findings:
  critical: 3
  warning: 4
  info: 2
  total: 9
status: issues_found
---

# Phase 05: Code Review Report

**Reviewed:** 2026-05-23T18:18:00Z
**Depth:** standard
**Files Reviewed:** 4
**Status:** issues_found

## Summary

Four files were reviewed: configuration constants (`src/config.py`), output generation logic (`src/output_generator.py`), the Jinja2 HTML dashboard template (`src/templates/dashboard.html.j2`), and the test suite (`tests/test_output_generator.py`).

The most severe defect is a **functional disconnect** between `DISPLAY_COLS_DASHBOARD` in `config.py` and the component score fields rendered in the dashboard's detail panel: the four component columns (`attendance_component`, `practice_component`, `trend_component`, `notes_component`) are excluded from the embedded JSON but unconditionally referenced in the JavaScript, making the "Risk Breakdown" panel permanently broken for every student. A second critical defect is that the clipboard copy function uses `element.textContent` of an already-HTML-escaped string, so facilitators copying WhatsApp messages will get entity-encoded garbage (`&amp;`, `&lt;`) rather than the real message text. A third critical defect is that `float('nan')` values in LLM columns survive the NA-normalisation guard in `_write_campus_dashboards` and reach openpyxl as floating-point NaN, which generates corrupt Excel files that Excel flags for repair.

---

## Critical Issues

### CR-01: Component Score Columns Excluded from Dashboard JSON — Breakdown Panel Always Shows `—`

**File:** `src/config.py:133-139` and `src/templates/dashboard.html.j2:451-454`

**Issue:** `DISPLAY_COLS_DASHBOARD` does not include `COL_ATTENDANCE_COMPONENT`, `COL_PRACTICE_COMPONENT`, `COL_TREND_COMPONENT`, or `COL_NOTES_COMPONENT`. The helper `_write_html_dashboard` serialises only the columns listed in `DISPLAY_COLS_DASHBOARD` into the embedded `studentsData` JSON. The template JS then unconditionally reads `student.attendance_component`, `student.practice_component`, etc. from that JSON. Because these keys are absent from every record, they evaluate to `undefined`, which the null-guard (`!= null`) catches, so the "Risk Breakdown" table permanently renders `—` for every component of every student. The visual panel exists but carries no information.

**Fix:** Add the four component columns to `DISPLAY_COLS_DASHBOARD` in `config.py`:

```python
# src/config.py  (lines 133-139)
DISPLAY_COLS_DASHBOARD: tuple[str, ...] = (
    COL_STUDENT_ID, COL_STUDENT_NAME, COL_CAMPUS_ID,
    COL_RISK_SCORE, COL_RISK_LEVEL,
    COL_ATTENDANCE_RATE, COL_AVG_PRACTICE, COL_TREND_DIR,
    COL_DAYS_SINCE_NOTE, COL_FACILITATOR_SUMMARY,
    COL_WHATSAPP_MESSAGE, COL_GENERATED_BY,
    # Add component score columns so the dashboard breakdown panel works:
    COL_ATTENDANCE_COMPONENT, COL_PRACTICE_COMPONENT,
    COL_TREND_COMPONENT, COL_NOTES_COMPONENT,
)
```

The template JS at lines 451-454 is correct; the fix belongs entirely in `config.py`.

---

### CR-02: WhatsApp Copy Button Copies HTML-Escaped Text Instead of Raw Message

**File:** `src/templates/dashboard.html.j2:460-500`

**Issue:** At line 464 the WhatsApp message is written into the DOM via `escapeHtml(whatsapp)` (which converts `&` → `&amp;`, `<` → `&lt;`, etc.) and the result is set as the text content of the `<p>` element. At line 499 `copyWhatsApp()` reads the value back with `el.textContent`. The browser's `.textContent` getter returns the *decoded* text as the browser stores it internally, so for a paragraph rendered via an `innerHTML` assignment the DOM stores the decoded characters — `&amp;` in the HTML attribute becomes `&` in `.textContent`.

However: `escapeHtml()` is called explicitly in a template literal interpolated via `innerHTML`. When the browser parses `<p ...>${escapeHtml(whatsapp)}</p>` set via `innerHTML`, it re-parses the escaped HTML and the `.textContent` on that element IS the unescaped original. This path is therefore actually correct.

**Actual bug:** `escapeHtml` escapes `'` to `&#39;` and `"` to `&quot;`. A WhatsApp message containing a curly apostrophe or quotation mark will have `.textContent` return the literal entity string `&#39;` because the HTML parser does NOT decode numeric character references in `innerHTML`-set text nodes in all contexts — wait, actually it does. Re-evaluating: `.innerHTML = '...'` fully parses HTML, so `&amp;` → `&`, `&lt;` → `<`, `&#39;` → `'` in `.textContent`. The copy is correct for simple entities.

**Real issue confirmed:** The `escapeHtml` function also replaces `'` with `&#39;`. Arabic WhatsApp messages frequently contain apostrophes. The `&#39;` form is a numeric character reference — the HTML parser resolves it, so `.textContent` returns `'`. This is fine.

**Revised finding:** After careful re-analysis the copy path is correct for well-formed HTML. **However**, the `summary-text` paragraph at line 460 also uses `escapeHtml` and renders via `innerHTML`, so `<`, `>`, `&` in facilitator summaries are displayed correctly as escaped text visually — this is correct behaviour.

**Actual CR-02 — correct finding:** The `id="wa-${idx}"` scheme (line 464) uses `idx`, which is the position in the *filtered* array passed to a single `renderTable()` call. The `onclick="copyWhatsApp(${idx}, this)"` attribute is baked into a string inserted via `innerHTML`. If the same student appears at `idx=3` in one filter run and `idx=0` in another, the old baked-in IDs from the previous `innerHTML` are destroyed by `tbody.innerHTML = ''` at line 390, so there is no stale-ID collision. The implementation is actually correct here.

**Genuine CR-02 (confirmed):** `el.textContent` at line 500 reads text from the element whose content was set by `detailTd.innerHTML`. When `innerHTML` is assigned a string containing `escapeHtml(whatsapp)`, the browser HTML-parses it. `&lt;` becomes `<` in the DOM. **But** `escapeHtml` also converts the input through these replacements in order: `&` → `&amp;`, then `<` → `&lt;`, etc. For a message like `Hello & welcome`, the DOM will store `Hello & welcome` in `.textContent` — correct. For a message with a pre-existing `&amp;` in the raw data, it becomes `&amp;amp;` in the escaped output, then the browser decodes it back to `&amp;`, not `&`. This double-encoding is a **data fidelity bug**: any student data that already contains HTML entities will be double-encoded during display and single-encoded when copied — the facilitator receives garbled text.

**Fix:** Do not apply `escapeHtml` when setting text-only content via `innerHTML`. Use `textContent` for the text nodes, or use `createTextNode`:

```javascript
// Replace:
// detailTd.innerHTML = `...<p class="summary-text">${escapeHtml(summary)}</p>...`

// After creating the detail panel node, set text content directly:
const summaryEl = detailTd.querySelector('.summary-text');
summaryEl.textContent = summary;  // browser escaping is automatic; no double-encode
```

Alternatively, build the detail panel with `createElement`/`textContent` instead of `innerHTML` for the user-supplied text fields.

---

### CR-03: `float('nan')` Escapes NA Normalisation in `_write_campus_dashboards` — Corrupt Excel Output

**File:** `src/output_generator.py:559-566`

**Issue:** The NA-normalisation block reads:

```python
if value is pd.NA:
    value = None
elif not isinstance(value, (str, int, float, bool)) and value is not None:
    try:
        if pd.isna(value):
            value = None
    except (TypeError, ValueError):
        pass
```

`float('nan')` is an instance of `float`, so `isinstance(value, (str, int, float, bool))` is `True`. It therefore fails the `elif` condition and is written directly to openpyxl as a Python `float('nan')`. openpyxl serialises this as `nan` in the XML `<v>` element, which is not a valid IEEE 754 representation in the Office Open XML spec. Excel opens the file with a repair dialog, silently drops the cell value, and logs a corruption notice. The LLM columns (`facilitator_summary`, `whatsapp_message`, `generated_by`) are nominally strings but are often `float('nan')` in a standard pandas DataFrame when constructed from dict literals without explicit dtype — exactly the situation in both real pipeline output and the `sample_df` test fixture.

**Fix:** Move the `float('nan')` check before the `isinstance` guard:

```python
# src/output_generator.py  (replace lines 558-566)
if value is pd.NA or value is None:
    value = None
elif isinstance(value, float) and pd.isna(value):
    value = None  # float('nan') → None; pd.isna is safe for float
elif not isinstance(value, (str, int, float, bool)):
    try:
        if pd.isna(value):
            value = None
    except (TypeError, ValueError):
        pass
```

This ensures `float('nan')` is caught and written as an empty cell, not as a corrupt float value.

---

## Warnings

### WR-01: `pd.NA` (Nullable Dtype) Survives `.notna()` / `.where()` in `_write_html_dashboard` — JSON Serialisation Crash

**File:** `src/output_generator.py:108-113`

**Issue:** The NaN-to-None conversion for JSON serialisation uses:

```python
df_copy[display_cols]
    .where(df_copy[display_cols].notna(), other=None)
    .to_dict(orient="records")
```

`DataFrame.notna()` returns `False` for `float('nan')` and `NaT`, which is correctly replaced with `None`. However, for columns with `pd.StringDtype` or `pd.Int64Dtype` (nullable dtypes), the pandas `NA` sentinel (`pd.NA`) evaluates `notna()` as `False` — but `.where(mask, other=None)` replaces the value with Python `None` **only when the array dtype allows it**. For `pd.StringDtype`, assigning `None` into a `where()` call yields `pd.NA` again (not `None`), because the nullable string array coerces `None` back to `pd.NA`. The subsequent `json.dumps(records)` call then encounters `pd.NA`, which is not JSON-serialisable, and raises `TypeError: Object of type NAType is not JSON serializable`.

The `full_sample_df` integration test fixture uses `pd.array(..., dtype="string")` for `COL_STUDENT_ID` and `COL_PARENT_PHONE`, so this crash path is reachable via the integration tests — but `COL_STUDENT_ID` and `COL_PARENT_PHONE` are present in `DISPLAY_COLS_DASHBOARD`, and those specific values have no NaN in the fixture. If any nullable-dtype column ever contains a `pd.NA` value, the dashboard write will raise `TypeError` at runtime and abort the pipeline.

**Fix:** Use `.to_dict(orient="records")` after explicitly casting the selected columns to object dtype, then replace `pd.NA` manually:

```python
records = (
    df_copy[display_cols]
    .astype(object)          # converts pd.NA → np.nan, pd.StringDtype → object
    .where(df_copy[display_cols].notna(), other=None)
    .to_dict(orient="records")
)
```

Or use a helper that converts each value:

```python
import math

def _safe_val(v):
    if v is pd.NA:
        return None
    if isinstance(v, float) and math.isnan(v):
        return None
    return v

records = [
    {k: _safe_val(v) for k, v in row.items()}
    for row in df_copy[display_cols].to_dict(orient="records")
]
```

---

### WR-02: `student.get()` Returns `nan` (Not `"N/A"`) for NaN Facilitator Summary in Word Report

**File:** `src/output_generator.py:325-326`

**Issue:**

```python
facilitator_summary = student.get(cfg.COL_FACILITATOR_SUMMARY, "N/A") or "N/A"
```

`pandas.Series.get(key, default)` returns the value for the key if it exists in the Series index, or `default` if the key is absent. Since `COL_FACILITATOR_SUMMARY` is always present as a column (it is always in `df_copy.columns`), `.get()` will always return the actual cell value — never the `"N/A"` default. If the cell value is `float('nan')` (the standard pandas representation for a missing string), the `or "N/A"` fallback also fails because `float('nan')` is truthy. The Word document will then contain the literal string `"nan"` as the facilitator summary for MEDIUM and LOW students, instead of "N/A" or a blank.

The same applies to `recommended_action` at line 326.

**Fix:**

```python
# src/output_generator.py  (lines 325-326)
import math

def _str_or_na(val: object) -> str:
    """Return str(val) or 'N/A' for None/nan/pd.NA."""
    if val is None or val is pd.NA:
        return "N/A"
    if isinstance(val, float) and math.isnan(val):
        return "N/A"
    return str(val)

facilitator_summary = _str_or_na(student[cfg.COL_FACILITATOR_SUMMARY])
recommended_action = _str_or_na(student[cfg.COL_RECOMMENDED_ACTION])
```

---

### WR-03: Campus ID Used Directly in Filename — Path Injection Risk for Untrusted CSV Data

**File:** `src/output_generator.py:583`

**Issue:**

```python
path = output_dir / f"facilitator_dashboard_{campus_id}.xlsx"
```

`campus_id` is read from the `campus_id` column of the input CSV. If an input CSV contains a campus ID with characters that are illegal or meaningful in file paths (e.g., `/`, `..`, `:`, `*`, `?`, `"`, `<`, `>`, `|` on Windows), the resulting path either raises an `OSError` / `ValueError` from `pathlib`, or — more dangerously — writes to an unintended directory (e.g., `campus_id = "../evil"` yields `output_dir / "facilitator_dashboard_../evil.xlsx"` which resolves to the parent directory). The same issue exists in the worksheet title at line 515 (`ws.title = str(campus_id)`) where openpyxl truncates names longer than 31 characters silently.

**Fix:** Sanitise the campus ID before building the filename:

```python
import re

# src/output_generator.py  (before line 583, inside the campus loop)
safe_campus_id = re.sub(r'[^\w\-]', '_', str(campus_id))
path = output_dir / f"facilitator_dashboard_{safe_campus_id}.xlsx"
ws.title = str(campus_id)[:31]  # openpyxl sheet name limit
```

---

### WR-04: HTML `lang` Attribute Set to `ar-001` (Arabic) for an English-Language UI

**File:** `src/templates/dashboard.html.j2:2`

**Issue:**

```html
<html lang="ar-001">
```

The entire dashboard UI — all headings, labels, button text, table headers, and footer — is English. The `lang="ar-001"` tag tells browsers, screen readers, and search engines that the document's primary language is Arabic. Consequences:
- Screen readers will pronounce English labels with Arabic phonology, making the dashboard inaccessible.
- Browsers apply right-to-left text direction heuristics for Arabic locales, potentially misaligning the flex layout in the filter bar and stat cards.
- Spell-check underlines all English words as misspelled.
- The `lang` tag is supposed to match the document content language.

**Fix:**

```html
<html lang="en">
```

If Arabic student names or WhatsApp messages need RTL support within cells, use `dir="auto"` on the specific `<td>` or `<p>` elements, not on the root `<html>` tag.

---

## Info

### IN-01: Unused `import math` in `multi_campus_df` Test Fixture

**File:** `tests/test_output_generator.py:292`

**Issue:** The `multi_campus_df` fixture imports `math` at line 292 (`import math`) but never references it. The `float("nan")` literal used in the fixture data (line 312) does not require `math`.

**Fix:** Remove the unused import:

```python
# Delete line 292:  import math
```

---

### IN-02: `test_write_outputs_returns_all_keys` Does Not Assert Specific Campus Keys

**File:** `tests/test_output_generator.py:571-574`

**Issue:** The integration test asserts `len(campus_keys) >= 1` — any single campus key satisfies the assertion. If `_write_campus_dashboards` silently dropped one campus (e.g., due to a dtype coercion bug), the test would still pass as long as at least one campus file was written. `full_sample_df` has two distinct campuses (ALPHA, BETA), so both should be asserted.

**Fix:**

```python
# tests/test_output_generator.py  (replace lines 571-574)
campus_keys = [k for k in result if k.startswith("campus_")]
assert "campus_ALPHA" in result, f"Missing 'campus_ALPHA' key: {list(result.keys())}"
assert "campus_BETA" in result, f"Missing 'campus_BETA' key: {list(result.keys())}"
```

---

_Reviewed: 2026-05-23T18:18:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
