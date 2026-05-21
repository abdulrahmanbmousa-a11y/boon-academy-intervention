# Stack Research: boon-academy-intervention

**Project:** AI-powered student intervention pipeline (Python CLI + Claude API)
**Researched:** 2026-05-21
**Source:** PyPI `pip index versions` (authoritative, live) + knowledge base for API behavior details

---

## Recommended Stack (with pinned versions)

```
# requirements.txt — production
pandas==2.2.3
openpyxl==3.1.5
python-docx==1.1.2
anthropic==0.103.1
python-dotenv==1.2.2
tenacity==9.1.4
jinja2==3.1.6

# requirements-dev.txt — testing only
pytest==8.3.5
pytest-mock==3.15.1
pytest-cov==7.1.0
respx==0.23.1
freezegun==1.5.5
coverage==7.14.0
```

**Why not latest pandas 3.x:** pandas 3.0 introduced Copy-on-Write as the mandatory default,
removing the `inplace` silent-copy footgun but also breaking any code that relied on chained
assignment. For a batch pipeline written from scratch, pandas 2.2.3 is the safer LTS-equivalent
pin: it has CoW as opt-in (not forced), is fully Python 3.11-compatible, and will receive
security patches through 2025. Migrate to 3.x only when you need the memory footprint
improvements and are ready to audit every `df[col] = ...` pattern.

---

## CSV Ingestion (pandas)

**Use:** `pandas==2.2.3`

### read_csv best practices for this pipeline

```python
import pandas as pd

DTYPE_MAPS = {
    "student_metrics": {
        "student_id":       "string",   # nullable string, not object
        "campus_id":        "string",
        "attendance_rate":  "Float64",  # capital F = nullable float
        "assignment_score": "Float64",
        "quiz_score":       "Float64",
        "login_count":      "Int64",    # capital I = nullable int
    },
    "facilitator_notes": {
        "student_id":   "string",
        "facilitator_id": "string",
        "note_text":    "string",
    },
    "student_metadata": {
        "student_id":  "string",
        "campus_id":   "string",
        "parent_phone": "string",  # NEVER let pandas auto-infer phone numbers as int
        "grade_level": "Int64",
    },
}

def load_csv(path: str, table: str, nrows: int | None = None) -> pd.DataFrame:
    return pd.read_csv(
        path,
        dtype=DTYPE_MAPS[table],
        keep_default_na=True,       # treat empty cells as NaN
        na_values=["", "N/A", "n/a", "NULL", "null", "-"],
        nrows=nrows,                # pass during dev/testing, None in prod
        engine="c",                 # default; faster than python engine
    )
```

### Missing value handling

- Use pandas nullable types (`Int64`, `Float64`, `string`) instead of NumPy types
  (`int64`, `float64`, `object`). Nullable types preserve NaN without silently
  converting to float or raising on integer columns.
- After load, validate missing-value counts before scoring:
  ```python
  missing = df.isnull().sum()
  if missing.any():
      logger.warning("Missing values detected: %s", missing[missing > 0].to_dict())
  ```
- For the risk-scoring formula, fill numeric NaN with 0 (absent = no activity), but
  **log the imputation** so facilitators know the score is based on incomplete data.

### Breaking change to watch (pandas 3.x)

pandas 3.0 makes Copy-on-Write mandatory. Any `df[col][row] = value` chained assignment
silently does nothing instead of raising. If you ever upgrade, audit every mutation.

### nrows usage

Pass `nrows=200` in unit tests to avoid reading full CSVs. In production, omit entirely —
the pipeline processes the full 14-day window.

---

## Excel Generation (openpyxl)

**Use:** `openpyxl==3.1.5`
**Do not use:** `xlsxwriter` for this project (see "What NOT to Use")

### Why openpyxl

openpyxl supports **read + write** on the same file. xlsxwriter is write-only (cannot
open an existing workbook). Since the pipeline produces `intervention_priority_list.xlsx`
and `facilitator_dashboard_{campus_id}.xlsx` from scratch, either could work — but openpyxl
is the correct choice because:

1. pandas `.to_excel()` with `engine="openpyxl"` and `ExcelWriter` in append mode
   requires openpyxl (xlsxwriter has no append mode).
2. The `openpyxl.styles` API is explicit and composable; xlsxwriter's format objects
   must be registered before writing and cannot be re-applied after cell creation.
3. openpyxl handles conditional formatting natively with `ConditionalFormattingList`.

### Color-coded cells with frozen rows and bold headers

```python
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter

RISK_FILLS = {
    "CRITICAL": PatternFill("solid", fgColor="FF0000"),   # red
    "HIGH":     PatternFill("solid", fgColor="FFA500"),   # orange
    "MEDIUM":   PatternFill("solid", fgColor="FFFF00"),   # yellow
    "LOW":      PatternFill("solid", fgColor="00FF00"),   # green
}

def style_worksheet(ws, df, risk_col: str = "risk_level"):
    # Bold header row
    for cell in ws[1]:
        cell.font = Font(bold=True)
        cell.alignment = Alignment(horizontal="center")

    # Freeze first row
    ws.freeze_panes = "A2"

    # Auto column width (openpyxl has no built-in; iterate and measure)
    for col_idx, col in enumerate(ws.columns, 1):
        max_len = max(
            len(str(cell.value)) if cell.value is not None else 0
            for cell in col
        )
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 50)

    # Color-code risk column
    risk_col_idx = df.columns.get_loc(risk_col) + 1  # 1-indexed
    for row_idx, risk_val in enumerate(df[risk_col], start=2):
        fill = RISK_FILLS.get(str(risk_val).upper())
        if fill:
            ws.cell(row=row_idx, column=risk_col_idx).fill = fill
```

### Known openpyxl limitation

Auto column width is not built in — openpyxl provides `column_dimensions` but you must
calculate the max character width yourself (shown above). The calculation is approximate
for non-monospace fonts; add 4 chars of padding as shown.

---

## Word Doc Generation (python-docx)

**Use:** `python-docx==1.1.2`

**Not** `1.2.0` — version 1.2.0 introduced a refactored `OxmlElement` namespace that
breaks some third-party snippets and has open issues with table border rendering as of
May 2026. Pin to 1.1.2 until 1.2.x stabilizes.

### Known limitations

1. **No native mail-merge or template variables.** You build the document imperatively
   via Python. Use a helper function that accepts a dict and writes sections.

2. **No automatic table-of-contents generation.** TOC entries must be inserted as raw
   XML using `OxmlElement` — fragile across Word versions. Omit TOC from the 8 docx
   documentation files unless explicitly required.

3. **Image sizing is points-based, not pixel-based.** Use `docx.shared.Inches` or
   `docx.shared.Cm` — never raw pixel values.

4. **Paragraph spacing does not inherit from the previous paragraph.** Set
   `paragraph.paragraph_format.space_after = Pt(0)` explicitly on each paragraph if
   you want tight spacing.

5. **Table cell shading requires XML manipulation.** `python-docx` has no high-level
   `cell.fill` — use `set_cell_shading()` via `OxmlElement`:
   ```python
   from docx.oxml.ns import qn
   from docx.oxml import OxmlElement

   def shade_cell(cell, fill_hex: str):
       tc = cell._tc
       tcPr = tc.get_or_add_tcPr()
       shd = OxmlElement("w:shd")
       shd.set(qn("w:fill"), fill_hex)
       shd.set(qn("w:val"), "clear")
       tcPr.append(shd)
   ```

### Recommended pattern for 8 documentation files

Generate each doc from a plain Python dict/dataclass. Keep document content out of
`main.py` — write a `docs_generator.py` module that accepts structured data and produces
each `.docx`. This keeps generation testable without file I/O in most tests.

---

## Anthropic SDK

**Use:** `anthropic==0.103.1`
**Model:** `claude-sonnet-4-5` (as specified in project constraints)

### Built-in retry behavior

The Anthropic Python SDK includes built-in automatic retry with exponential backoff.
Configure at client construction:

```python
import anthropic

client = anthropic.Anthropic(
    api_key=os.environ["ANTHROPIC_API_KEY"],
    max_retries=3,          # default is 2; set to 3 for batch pipelines
    timeout=60.0,           # seconds; default is 600 — too long for a batch job
)
```

The SDK retries on: connection errors, 408 (timeout), 429 (rate limit), 500, 502, 503, 529.
It uses exponential backoff with jitter automatically. You do NOT need tenacity for the
API call itself unless you want custom retry logic (e.g., per-campus retry with logging).

**Use tenacity on top** only if you need: retry budgets per campus, custom on-retry callbacks
that log to `run_log.json`, or circuit-breaker behavior. Otherwise the SDK's built-in
retry is sufficient.

### Token counting (usage tracking for $200/month budget)

Every `messages.create()` response includes a `usage` attribute:

```python
response = client.messages.create(
    model="claude-sonnet-4-5",
    max_tokens=1024,
    messages=[{"role": "user", "content": prompt}],
)

input_tokens  = response.usage.input_tokens
output_tokens = response.usage.output_tokens
total_tokens  = input_tokens + output_tokens
```

For pre-call token estimation (before spending), use the count_tokens endpoint:

```python
token_count = client.messages.count_tokens(
    model="claude-sonnet-4-5",
    messages=[{"role": "user", "content": prompt}],
)
estimated_input = token_count.input_tokens
```

**Track cumulative tokens in `run_log.json`** across all campus batches. Emit a warning
if projected cost (input * $3/MTok + output * $15/MTok for Sonnet 3.5) approaches the
$200/month budget.

### Batching pattern for CRITICAL/HIGH students per campus

```python
def build_campus_prompt(campus_id: str, students: list[dict]) -> str:
    student_summaries = "\n".join(
        f"- {s['name']} (ID: {s['student_id']}): "
        f"risk={s['risk_level']}, attendance={s['attendance_rate']:.0%}, "
        f"notes={s['latest_note']}"
        for s in students
    )
    return (
        f"Campus: {campus_id}\n"
        f"Students requiring intervention ({len(students)} total):\n"
        f"{student_summaries}\n\n"
        "For each student: (1) write a 2-sentence facilitator action summary "
        "and (2) write a WhatsApp parent message in Arabic under 160 characters."
    )
```

Send one API call per campus (not per student). This reduces API calls by ~10x and
keeps tokens-per-call manageable. Parse the structured response per student.

### Rate limit handling

claude-sonnet-4-5 has a requests-per-minute (RPM) limit. For a batch pipeline processing
~10 campuses, you are unlikely to hit it. If you do, the SDK's built-in retry with
backoff handles 429s automatically.

---

## Testing Stack

**Core:**
- `pytest==8.3.5` — test runner
- `pytest-mock==3.15.1` — `mocker` fixture wrapping `unittest.mock`
- `pytest-cov==7.1.0` + `coverage==7.14.0` — coverage reporting
- `respx==0.23.1` — mock httpx transports (the Anthropic SDK uses httpx internally)
- `freezegun==1.5.5` — freeze timestamps in `run_log.json` assertions

**Why respx over pytest-httpx:**

The Anthropic SDK (0.50+) uses `httpx` as its HTTP transport. `respx` intercepts at the
`httpx.AsyncClient` / `httpx.Client` transport level and works cleanly with both sync
and async SDK usage. `pytest-httpx` is also valid, but `respx` has a cleaner API for
this use case and does not require the test to know whether the SDK uses sync or async
internally.

**Why not `responses`:** `responses` mocks the `requests` library. The Anthropic SDK
does not use `requests` — it uses `httpx`. Using `responses` here will not intercept
SDK calls.

### Testing the Anthropic SDK without real credentials

```python
# tests/test_claude_generator.py
import respx
import httpx
import pytest
import json

FAKE_RESPONSE = {
    "id": "msg_test",
    "type": "message",
    "role": "assistant",
    "content": [{"type": "text", "text": "Facilitator action: Follow up immediately."}],
    "model": "claude-sonnet-4-5",
    "stop_reason": "end_turn",
    "usage": {"input_tokens": 150, "output_tokens": 50},
}

@respx.mock
def test_generate_intervention_summary(mocker):
    respx.post("https://api.anthropic.com/v1/messages").mock(
        return_value=httpx.Response(200, json=FAKE_RESPONSE)
    )
    from src.claude_generator import generate_campus_summary
    result = generate_campus_summary(campus_id="C01", students=[...])
    assert "Follow up immediately" in result.text
```

### Testing CSV ingestion without real files

Use `io.StringIO` to inject CSV content directly — no temp files:

```python
import io
import pandas as pd
from src.ingestion import load_csv_from_buffer

def test_missing_attendance_rate_filled_with_zero():
    csv_content = "student_id,attendance_rate\nS001,\nS002,0.85"
    df = pd.read_csv(io.StringIO(csv_content), dtype={"student_id": "string", "attendance_rate": "Float64"})
    df["attendance_rate"] = df["attendance_rate"].fillna(0.0)
    assert df.loc[df["student_id"] == "S001", "attendance_rate"].iloc[0] == 0.0
```

---

## Environment Management

**Use:** `python-dotenv==1.2.2`

```python
# main.py — load at entry point, before any other imports that use env vars
from dotenv import load_dotenv
load_dotenv()  # reads .env in cwd; does NOT override already-set env vars

import os
API_KEY = os.environ["ANTHROPIC_API_KEY"]  # raises KeyError if missing — GOOD
```

**Critical pattern:** Use `os.environ["KEY"]` (raises) not `os.getenv("KEY")` (returns None)
for required secrets. Fail fast at startup rather than at the first API call 20 minutes into
a batch run.

### .env file layout

```
# .env  — never commit this file
ANTHROPIC_API_KEY=sk-ant-...
OUTPUT_DIR=./output
LOG_LEVEL=INFO
```

### .env.example file (commit this)

```
ANTHROPIC_API_KEY=
OUTPUT_DIR=./output
LOG_LEVEL=INFO
```

### CI/CD note

In CI (GitHub Actions etc.), set env vars directly in the runner environment. Do NOT
commit `.env` or inject it via `load_dotenv` in CI — set `ANTHROPIC_API_KEY` as a
repository secret.

---

## HTML Self-Contained Dashboard

**Use:** `jinja2==3.1.6`

The `facilitator_dashboard.html` must be a single standalone file with no external
dependencies. The correct pattern is:

1. Compute all data in Python (DataFrames, summary stats, per-campus breakdowns)
2. Serialize to JSON with `json.dumps(data, ensure_ascii=False)`
3. Render via a Jinja2 template that embeds the JSON as a JavaScript variable and
   uses vanilla JS or an inlined chart library

```python
from jinja2 import Environment, FileSystemLoader
import json

def render_dashboard(data: dict, output_path: str) -> None:
    env = Environment(loader=FileSystemLoader("templates"))
    template = env.get_template("dashboard.html.j2")
    html = template.render(
        dashboard_data_json=json.dumps(data, ensure_ascii=False, default=str),
        generated_at=datetime.utcnow().isoformat(),
    )
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(html)
```

```html
<!-- templates/dashboard.html.j2 -->
<!DOCTYPE html>
<html lang="ar" dir="rtl">
<head>
  <meta charset="UTF-8">
  <title>Facilitator Dashboard</title>
  <style>
    /* Inline all CSS here — no external stylesheets */
  </style>
</head>
<body>
  <script>
    const DASHBOARD_DATA = {{ dashboard_data_json | safe }};
    // All rendering logic here — no CDN, no external JS
  </script>
</body>
</html>
```

**Why not a heavier templating approach (Flask, FastAPI):** The spec says "no server."
Jinja2 renders at generation time to a static `.html` file. The file opens in any browser
with no server process.

**Why not string formatting / f-strings for HTML:** Jinja2 auto-escapes HTML in the
template body (preventing XSS from student name data), handles `| safe` explicitly
for trusted JSON blobs, and keeps logic out of Python strings.

---

## What NOT to Use (and why)

| Library | Avoid Because |
|---------|--------------|
| `xlsxwriter` | Write-only — cannot open/append to existing workbooks. Would force a full rewrite if append behavior is needed. openpyxl does everything xlsxwriter does for this pipeline plus read/append. |
| `pandas >= 3.0` | Copy-on-Write is mandatory default, not opt-in. New project starting from scratch should use 2.2.3 (stable) and schedule a deliberate 3.x migration. |
| `responses` (mock lib) | Mocks `requests`, not `httpx`. The Anthropic SDK uses `httpx` internally. `responses` will silently fail to intercept SDK calls. Use `respx` instead. |
| `openpyxl < 3.1` | 3.0.x had a `NamedStyle` registration bug that causes duplicate-style errors when writing multiple worksheets in a loop. Pin to 3.1.5. |
| `python-docx >= 1.2.0` | Version 1.2.0 refactored `OxmlElement` namespace (May 2025), breaking several table-border and shading patterns. 1.1.2 is stable. Re-evaluate when 1.2.x issues close. |
| `tenacity` for API retries | Redundant with the Anthropic SDK's built-in retry/backoff. Add only if you need custom retry callbacks or per-campus circuit breaking. |
| `httpretty` | Deprecated approach; does not work with `httpx` (socket-level mocking, not transport-level). |
| `dotenv` (the other one) | There are two `dotenv` packages on PyPI. The correct one is `python-dotenv`. The other (`dotenv`) is unmaintained. |
| `chardet` or `cchardet` | Do not auto-detect CSV encoding. Require UTF-8 as the only accepted encoding; fail with a clear error message if the file is not UTF-8. |

---

## Confidence Levels

| Area | Version Source | Confidence | Notes |
|------|---------------|------------|-------|
| All pinned versions | `pip index versions` (live PyPI query, 2026-05-21) | HIGH | Directly queried from PyPI |
| pandas 2.2.3 vs 3.x rationale | Knowledge base (CoW behavior is well-documented) | HIGH | CoW-as-default is the headline pandas 3.0 change |
| openpyxl vs xlsxwriter decision | Knowledge base (write-only limitation is in xlsxwriter docs) | HIGH | xlsxwriter docs explicitly state write-only |
| python-docx 1.1.2 vs 1.2.0 warning | Knowledge base | MEDIUM | 1.2.0 is recent; flag for manual verification before pinning |
| Anthropic SDK built-in retries | Knowledge base (SDK README documents `max_retries` param) | HIGH | SDK has exposed `max_retries` since ~0.20 |
| Anthropic SDK `count_tokens` | Knowledge base (added in SDK ~0.28) | HIGH | Available in 0.103.1 |
| `responses` vs `respx` for httpx mocking | Knowledge base | HIGH | Well-known incompatibility; httpx community consensus |
| Jinja2 for self-contained HTML | Knowledge base | HIGH | Standard pattern; no alternatives needed |
