# Architecture Research: noon-academy-intervention

**Domain:** Python batch data pipeline with LLM enrichment and multi-format output
**Researched:** 2026-05-21
**Overall confidence:** HIGH (well-established Python/pandas/openpyxl/Anthropic SDK patterns)

---

## Pipeline Architecture

### Single-Pass Linear Pipeline

```
CSV files (3)
     │
     ▼
[ingestion.py]  ─── raw merge ──► unified DataFrame (students_raw)
     │
     ▼
[risk_engine.py] ─── score + tier ──► enriched DataFrame (students_scored)
     │
     ▼
[llm_engine.py]  ─── batch API calls by campus ──► DataFrame + llm_responses column
     │
     ▼
[output_generator.py] ─── fan-out ──► Excel / Word / HTML / CSV / JSON
     │
     ▼
[doc_generator.py]    ─────────────► 8 x .docx documentation files
```

The pipeline is a **linear transformer chain**. Each stage receives a DataFrame and
returns a richer DataFrame (or the same DataFrame with new columns appended). No stage
writes to disk except the final output stage. This makes unit testing trivial: mock
the DataFrame in, assert columns out.

### Execution Entry Point

```python
# main.py — orchestrates the chain, owns no business logic
def main():
    cfg   = load_config()                     # config.py / .env
    df    = ingest(cfg.data_paths)            # ingestion.py
    df    = score_risk(df)                    # risk_engine.py
    df    = enrich_with_llm(df, cfg.api_key)  # llm_engine.py
    write_outputs(df, cfg.output_dir)         # output_generator.py
    write_docs(cfg)                           # doc_generator.py
    write_run_log(df, cfg)                    # logger.py
```

`main.py` owns orchestration only. No business logic lives there.

---

## Module Interfaces (Input / Output Contracts)

### ingestion.py

```python
def ingest(data_paths: dict[str, Path]) -> pd.DataFrame:
    """
    Input:
        data_paths = {
            "students":     Path("data/students.csv"),
            "attendance":   Path("data/attendance.csv"),
            "assessments":  Path("data/assessments.csv"),
        }

    Output: DataFrame with columns:
        student_id (str, PK), full_name (str), campus_id (str),
        campus_name (str), grade_level (str), phone_whatsapp (str),
        attendance_rate (float 0-1), avg_score (float 0-100),
        assignments_missing (int), last_active_days_ago (int),
        [any other raw fields needed downstream]

    Contract:
        - Returns exactly one row per student_id.
        - No NaN in student_id, campus_id, full_name.
        - Raises ValueError on missing required columns.
        - Raises FileNotFoundError if any path missing.
    """
```

**Design rule:** Ingestion handles ALL normalization (column rename, dtype cast, dedup).
Downstream modules must never call `.fillna()` or rename columns.

### risk_engine.py

```python
def score_risk(df: pd.DataFrame) -> pd.DataFrame:
    """
    Input:  DataFrame from ingest()
    Output: same DataFrame + new columns:
        risk_score (float 0-100),
        risk_tier  (str: "CRITICAL" | "HIGH" | "MEDIUM" | "LOW"),
        score_components (dict, stored as JSON string for export)

    Contract:
        - Pure function: no I/O, no randomness.
        - Deterministic: same input always → same output.
        - risk_score uses weighted formula (weights in config.py).
        - Raises nothing; every student gets a score.
    """
```

**Design rule:** Keep weights in `config.py`, not hardcoded. Enables A/B testing of
formula without touching engine code.

### llm_engine.py

```python
def enrich_with_llm(
    df: pd.DataFrame,
    api_key: str,
    tiers: list[str] = ["CRITICAL", "HIGH"],
    batch_size: int = 10,
) -> pd.DataFrame:
    """
    Input:  scored DataFrame from score_risk()
    Output: same DataFrame + new columns:
        llm_intervention (str | None),
        llm_rationale   (str | None),
        llm_source      (str: "claude-3-5-haiku" | "rule_template" | "skipped"),
        llm_error       (str | None)

    Contract:
        - Only calls API for rows where risk_tier in tiers.
        - Non-targeted rows get llm_source="skipped", others None.
        - On API failure after retries: llm_source="rule_template".
        - Never raises; errors recorded in llm_error column.
    """
```

**Design rule:** LLM engine is a side-effect module but still returns a DataFrame.
Failures are data, not exceptions. Downstream output code checks `llm_source` column.

### output_generator.py

```python
def write_outputs(df: pd.DataFrame, output_dir: Path) -> dict[str, Path]:
    """
    Input:  fully enriched DataFrame
    Output: dict of {"artifact_name": Path} for each file written

    Contract:
        - Idempotent: running twice overwrites (no partial state).
        - output_dir created if missing.
        - Returns paths so run_log can record them.
    """
```

Sub-functions (private to module):
- `_write_priority_excel(df, path)` — master list, all campuses
- `_write_campus_excel(campus_df, path)` — one per campus
- `_write_whatsapp_csv(df, path)` — CRITICAL+HIGH only
- `_write_word_report(df, path)` — aggregate statistics
- `_write_html_dashboard(df, path)` — self-contained HTML
- `_write_json_log(df, meta, path)` — run metadata

---

## Data Representation (DataFrame Schema)

### Canonical Column Set

All columns present after each pipeline stage:

| Column | Type | Stage Added | Notes |
|--------|------|-------------|-------|
| `student_id` | str | ingestion | Primary key, no NaN |
| `full_name` | str | ingestion | |
| `campus_id` | str | ingestion | Slug, e.g. "riyadh-01" |
| `campus_name` | str | ingestion | Display name |
| `grade_level` | str | ingestion | e.g. "G10" |
| `phone_whatsapp` | str | ingestion | Normalized E.164 |
| `attendance_rate` | float | ingestion | 0.0–1.0 |
| `avg_score` | float | ingestion | 0.0–100.0 |
| `assignments_missing` | int | ingestion | |
| `last_active_days_ago` | int | ingestion | |
| `risk_score` | float | risk_engine | 0.0–100.0 |
| `risk_tier` | str | risk_engine | CRITICAL/HIGH/MEDIUM/LOW |
| `score_components` | str | risk_engine | JSON string |
| `llm_intervention` | str | llm_engine | None if skipped |
| `llm_rationale` | str | llm_engine | None if skipped |
| `llm_source` | str | llm_engine | claude/rule_template/skipped |
| `llm_error` | str | llm_engine | None if no error |

### Schema Validation Pattern

Use a lightweight schema check at each stage boundary:

```python
REQUIRED_AFTER_INGEST = {
    "student_id", "full_name", "campus_id", "campus_name",
    "attendance_rate", "avg_score", "assignments_missing",
    "last_active_days_ago", "phone_whatsapp",
}

def _validate(df: pd.DataFrame, required: set[str], stage: str) -> None:
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"[{stage}] Missing columns: {missing}")
    if df["student_id"].isna().any():
        raise ValueError(f"[{stage}] NaN student_id rows found")
```

Call `_validate()` at the top of each module's main function before processing.
This catches upstream contract violations immediately at the source, not mysteriously
downstream.

### DataFrame Performance Notes

- At 5,000 students, a fully enriched DataFrame is ~5,000 rows x 17 columns.
  This fits in memory well under 50 MB. No chunking required.
- Use `pd.Categorical` for `risk_tier` and `campus_id` columns — reduces memory
  ~4x for string columns and speeds `.groupby("campus_id")` operations.
- Sort by `(campus_id, risk_score DESC)` once after `score_risk()` and keep that
  order for all output. Avoids repeated sort calls in output functions.

---

## LLM Batching Pattern

### Core Design: Campus-Cohort Batching

Group students by campus, then send each campus in batches of N students per API call.
This is preferable to per-student calls because:
- Reduces API round-trips (1,000 students / 10 per call = 100 calls vs 1,000)
- Allows Claude to see sibling students in the same campus for contextual recommendations
- Single retry unit is one campus batch, not one student

### Batch Construction

```python
def _build_campus_batches(
    df: pd.DataFrame,
    tiers: list[str],
    batch_size: int = 10,
) -> list[dict]:
    """
    Returns list of batch dicts:
    {
        "campus_id": str,
        "campus_name": str,
        "students": [
            {
                "student_id": str,
                "full_name": str,
                "risk_tier": str,
                "risk_score": float,
                "attendance_rate": float,
                "avg_score": float,
                "assignments_missing": int,
                "last_active_days_ago": int,
            },
            ...  # up to batch_size entries
        ]
    }
    """
    targeted = df[df["risk_tier"].isin(tiers)].copy()
    batches = []
    for campus_id, campus_df in targeted.groupby("campus_id"):
        campus_name = campus_df["campus_name"].iloc[0]
        students = campus_df[STUDENT_FIELDS].to_dict("records")
        # Chunk into batch_size groups
        for i in range(0, len(students), batch_size):
            batches.append({
                "campus_id":   campus_id,
                "campus_name": campus_name,
                "students":    students[i : i + batch_size],
            })
    return batches
```

### Prompt Structure for Multi-Student Structured Output

**System prompt (constant, not per-call):**
```
You are an academic intervention advisor for a K-12 school network.
You analyze student risk data and produce concise, actionable intervention
recommendations for teachers and counselors.

Always respond with valid JSON only. No preamble, no explanation outside the JSON.
```

**User prompt template (per batch):**
```python
BATCH_PROMPT = """\
Campus: {campus_name}

Analyze the following {n} at-risk students and provide intervention recommendations.

Students:
{students_json}

Respond with this exact JSON structure:
{{
  "interventions": [
    {{
      "student_id": "<string, exactly as provided>",
      "intervention": "<2-3 sentence specific action for teacher/counselor>",
      "rationale": "<1 sentence explaining the primary risk driver>"
    }}
  ]
}}

Rules:
- Output one entry per student_id, in the same order.
- Keep interventions practical and campus-specific.
- Do not invent data not present in the input.
"""
```

Render with:
```python
import json

prompt = BATCH_PROMPT.format(
    campus_name=batch["campus_name"],
    n=len(batch["students"]),
    students_json=json.dumps(batch["students"], indent=2, ensure_ascii=False),
)
```

### Parsing and Merging Structured Output

```python
def _parse_llm_response(response_text: str, batch: dict) -> dict[str, dict]:
    """
    Returns: {student_id: {"intervention": str, "rationale": str}}
    Falls back to empty dict on parse failure.
    """
    try:
        # Strip markdown code fences if model wraps output in ```json
        text = response_text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0]
        parsed = json.loads(text)
        return {
            item["student_id"]: {
                "intervention": item["intervention"],
                "rationale":    item["rationale"],
            }
            for item in parsed["interventions"]
        }
    except (json.JSONDecodeError, KeyError, TypeError):
        return {}  # Triggers rule_template fallback for entire batch
```

After parsing, merge back to DataFrame:

```python
# results_map: {student_id: {"intervention": str, "rationale": str, "source": str}}
df["llm_intervention"] = df["student_id"].map(
    lambda sid: results_map.get(sid, {}).get("intervention")
)
df["llm_rationale"] = df["student_id"].map(
    lambda sid: results_map.get(sid, {}).get("rationale")
)
df["llm_source"] = df["student_id"].map(
    lambda sid: results_map.get(sid, {}).get("source", "skipped")
)
```

### Model Selection

Use `claude-3-5-haiku-20241022` for batch enrichment (not Sonnet/Opus):
- ~10x cheaper than Sonnet for structured extraction tasks
- Latency acceptable for batch processing (not real-time)
- Sufficient quality for structured JSON output from well-formed data

Switch to `claude-3-5-sonnet-20241022` only if haiku output quality is unacceptable
after testing on real student data.

---

## Retry + Fallback Architecture

### Three-Layer Error Handling

```
Layer 1: HTTP retry (transient errors: 429, 500, 502, 503, 529)
Layer 2: Parse retry (valid HTTP 200 but malformed JSON — re-prompt once)
Layer 3: Rule-based template fallback (all retries exhausted)
```

### Layer 1: Exponential Backoff Implementation

```python
import time
import random
import anthropic

RETRYABLE_STATUS = {429, 500, 502, 503, 529}

def _call_with_retry(
    client: anthropic.Anthropic,
    system: str,
    prompt: str,
    model: str = "claude-3-5-haiku-20241022",
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 60.0,
) -> str | None:
    """Returns response text, or None on total failure."""
    for attempt in range(max_retries + 1):
        try:
            response = client.messages.create(
                model=model,
                max_tokens=1024,
                system=system,
                messages=[{"role": "user", "content": prompt}],
            )
            return response.content[0].text

        except anthropic.RateLimitError:
            if attempt == max_retries:
                return None
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
            time.sleep(delay)

        except anthropic.APIStatusError as e:
            if e.status_code not in RETRYABLE_STATUS or attempt == max_retries:
                return None
            delay = min(base_delay * (2 ** attempt) + random.uniform(0, 1), max_delay)
            time.sleep(delay)

        except anthropic.APIConnectionError:
            if attempt == max_retries:
                return None
            time.sleep(base_delay * (2 ** attempt))

    return None
```

Note: The Anthropic Python SDK (>= 0.20) includes built-in automatic retries via
`max_retries` constructor param. Use SDK-level retry for simple cases:
```python
client = anthropic.Anthropic(api_key=key, max_retries=2)
```
Add the manual wrapper above when you need per-attempt logging or custom delay curves.

### Layer 2: Parse Retry

If `_call_with_retry()` returns a non-None string but `_parse_llm_response()` returns
empty dict (JSON parse failure), re-prompt once with:

```python
REPARSE_SUFFIX = (
    "\n\nIMPORTANT: Your previous response was not valid JSON. "
    "Respond with raw JSON only, no markdown, no explanation."
)
```

Append to original prompt and retry once. If second parse also fails, move to Layer 3.

### Layer 3: Rule-Based Template Fallback

Applied per student when their batch fails all retries:

```python
INTERVENTION_TEMPLATES = {
    "CRITICAL": (
        "Immediate counselor contact required. Student shows critical indicators "
        "in {top_risk_factor}. Schedule same-week meeting with student and guardian. "
        "Review academic support plan."
    ),
    "HIGH": (
        "Priority outreach this week. Student at high risk due to {top_risk_factor}. "
        "Assign peer mentor and weekly check-in with subject teacher."
    ),
}

def _rule_based_intervention(row: pd.Series) -> tuple[str, str]:
    """Returns (intervention, rationale) tuple."""
    top_factor = _identify_top_risk_factor(row)
    template   = INTERVENTION_TEMPLATES.get(
        row["risk_tier"], INTERVENTION_TEMPLATES["HIGH"]
    )
    return (
        template.format(top_risk_factor=top_factor),
        f"Rule-based: primary driver is {top_factor} (score={row['risk_score']:.1f})"
    )

def _identify_top_risk_factor(row: pd.Series) -> str:
    factors = {
        "attendance":    1.0 - row["attendance_rate"],
        "assessment":    (100 - row["avg_score"]) / 100,
        "missing work":  min(row["assignments_missing"] / 10, 1.0),
        "inactivity":    min(row["last_active_days_ago"] / 30, 1.0),
    }
    return max(factors, key=factors.get)
```

### Wiring All Three Layers in enrich_with_llm()

```python
for batch in batches:
    raw    = _call_with_retry(client, SYSTEM_PROMPT, _build_prompt(batch))
    parsed = _parse_llm_response(raw, batch) if raw else {}

    # Layer 2: single re-prompt on parse failure
    if not parsed and raw:
        raw2   = _call_with_retry(
            client, SYSTEM_PROMPT, _build_prompt(batch) + REPARSE_SUFFIX
        )
        parsed = _parse_llm_response(raw2, batch) if raw2 else {}

    for student in batch["students"]:
        sid = student["student_id"]
        if sid in parsed:
            results_map[sid] = {
                **parsed[sid],
                "source": model_name,
                "error":  None,
            }
        else:
            # Layer 3: rule-based fallback
            row = df[df["student_id"] == sid].iloc[0]
            interv, rationale = _rule_based_intervention(row)
            results_map[sid] = {
                "intervention": interv,
                "rationale":    rationale,
                "source":       "rule_template",
                "error":        "api_failure" if raw is None else "parse_failure",
            }
```

---

## Excel Output Patterns

### Correct openpyxl Pattern for Styled Workbooks

```python
from openpyxl import Workbook
from openpyxl.styles import PatternFill, Font, Alignment
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows

TIER_COLORS = {
    "CRITICAL": "FFCCCC",  # light red
    "HIGH":     "FFE5CC",  # light orange
    "MEDIUM":   "FFFACC",  # light yellow
    "LOW":      "CCFFCC",  # light green
}

HEADER_FILL  = PatternFill("solid", fgColor="1F4E79")  # dark blue
HEADER_FONT  = Font(bold=True, color="FFFFFF", size=11)
HEADER_ALIGN = Alignment(horizontal="center", vertical="center", wrap_text=True)


def _write_priority_excel(df: pd.DataFrame, path: Path) -> None:
    wb = Workbook()
    ws = wb.active
    ws.title = "Priority List"

    display_cols = [
        "student_id", "full_name", "campus_name", "grade_level",
        "risk_tier", "risk_score", "attendance_rate", "avg_score",
        "assignments_missing", "llm_intervention",
    ]
    headers = [col.replace("_", " ").title() for col in display_cols]

    # Header row
    for col_idx, header in enumerate(headers, start=1):
        cell           = ws.cell(row=1, column=col_idx, value=header)
        cell.fill      = HEADER_FILL
        cell.font      = HEADER_FONT
        cell.alignment = HEADER_ALIGN

    # Data rows with risk-tier color banding
    for row_idx, row_data in enumerate(
        dataframe_to_rows(df[display_cols], index=False, header=False),
        start=2
    ):
        tier  = df.iloc[row_idx - 2]["risk_tier"]
        fill  = PatternFill("solid", fgColor=TIER_COLORS.get(tier, "FFFFFF"))
        for col_idx, value in enumerate(row_data, start=1):
            cell           = ws.cell(row=row_idx, column=col_idx, value=value)
            cell.fill      = fill
            cell.alignment = Alignment(vertical="top", wrap_text=True)

    # Freeze top row
    ws.freeze_panes = "A2"

    # Auto column width (capped to avoid absurdly wide intervention column)
    for col_idx, col_cells in enumerate(ws.columns, start=1):
        max_len = max(
            (len(str(cell.value)) for cell in col_cells if cell.value),
            default=10
        )
        ws.column_dimensions[get_column_letter(col_idx)].width = min(max_len + 4, 50)

    # Header row height
    ws.row_dimensions[1].height = 30

    # Auto filter on entire data range
    ws.auto_filter.ref = ws.dimensions

    wb.save(path)
```

**Key rules:**
- `PatternFill("solid", fgColor=...)` — must pass `fill_type` as the first
  positional argument. Using `PatternFill(fgColor=...)` without fill_type silently
  produces no color in many openpyxl versions.
- `dataframe_to_rows(df, index=False, header=False)` — set both to False when
  manually controlling the header row.
- `wb.save()` must be called last — openpyxl only writes on save.
- For per-campus sheets in one workbook: `ws = wb.create_sheet(title=campus_name)`.
- Campus names with `/` or `>` characters will error on sheet naming — sanitize:
  `campus_name[:31].replace("/", "-").replace(":", "")` (Excel sheet name limit: 31 chars).

---

## Self-Contained HTML Pattern

### Embedding JSON in a Single file:// HTML

The pattern: store all data as a JavaScript const in a `<script>` tag. The file
has zero external dependencies — no CDN, no fetch() calls, no separate .json file.

```python
import json
from pathlib import Path
from datetime import datetime

HTML_TEMPLATE = """\
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>Noon Academy — Intervention Dashboard</title>
  <style>
    body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
           margin: 0; padding: 20px; background: #f5f5f5; }}
    .header {{ background: #1F4E79; color: white; padding: 20px;
               border-radius: 8px; margin-bottom: 20px; }}
    .stats  {{ display: grid; grid-template-columns: repeat(4,1fr);
               gap: 16px; margin-bottom: 24px; }}
    .card   {{ background: white; padding: 16px; border-radius: 8px;
               box-shadow: 0 1px 3px rgba(0,0,0,.1); text-align: center; }}
    .num    {{ font-size: 2rem; font-weight: bold; }}
    .c {{ color: #dc3545; }} .h {{ color: #fd7e14; }}
    .m {{ color: #ffc107; }} .l {{ color: #28a745; }}
    table   {{ width:100%; border-collapse:collapse; background:white;
               border-radius:8px; overflow:hidden;
               box-shadow:0 1px 3px rgba(0,0,0,.1); }}
    thead tr {{ background:#1F4E79; color:white; }}
    th,td   {{ padding:10px 14px; text-align:left; border-bottom:1px solid #eee; }}
    .CRITICAL {{ background:#fff5f5; }} .HIGH {{ background:#fff8f0; }}
    .MEDIUM   {{ background:#fffef0; }} .LOW  {{ background:#f0fff4; }}
    input   {{ margin-bottom:16px; padding:8px 12px; width:300px;
               font-size:14px; border:1px solid #ddd; border-radius:4px; }}
  </style>
</head>
<body>
  <div class="header">
    <h1>Student Intervention Dashboard</h1>
    <p>Run: {run_date} &nbsp;|&nbsp; Students: {total} &nbsp;|&nbsp; Campuses: {campus_count}</p>
  </div>
  <div class="stats">
    <div class="card"><div class="num c" id="nc">0</div><div>Critical</div></div>
    <div class="card"><div class="num h" id="nh">0</div><div>High</div></div>
    <div class="card"><div class="num m" id="nm">0</div><div>Medium</div></div>
    <div class="card"><div class="num l" id="nl">0</div><div>Low</div></div>
  </div>
  <input id="q" type="text" placeholder="Search name, campus, ID…" onkeyup="render()">
  <table>
    <thead>
      <tr><th>ID</th><th>Name</th><th>Campus</th><th>Tier</th>
          <th>Score</th><th>Attendance</th><th>Avg Score</th><th>Intervention</th></tr>
    </thead>
    <tbody id="tb"></tbody>
  </table>
  <script>
    // ALL DATA EMBEDDED — file:// safe, no fetch() required
    const DATA = {students_json};

    // Stat counters
    ['CRITICAL','HIGH','MEDIUM','LOW'].forEach((t,i) => {{
      document.getElementById(['nc','nh','nm','nl'][i]).textContent =
        DATA.filter(s => s.risk_tier === t).length;
    }});

    function render() {{
      const q = document.getElementById('q').value.toLowerCase();
      const rows = q
        ? DATA.filter(s =>
            s.full_name.toLowerCase().includes(q) ||
            s.campus_name.toLowerCase().includes(q) ||
            s.student_id.toLowerCase().includes(q))
        : DATA;
      document.getElementById('tb').innerHTML = rows.map(s => `
        <tr class="${{s.risk_tier}}">
          <td>${{s.student_id}}</td><td>${{s.full_name}}</td>
          <td>${{s.campus_name}}</td><td><b>${{s.risk_tier}}</b></td>
          <td>${{s.risk_score.toFixed(1)}}</td>
          <td>${{(s.attendance_rate*100).toFixed(0)}}%</td>
          <td>${{s.avg_score.toFixed(1)}}</td>
          <td>${{s.llm_intervention || '—'}}</td>
        </tr>`).join('');
    }}
    render();
  </script>
</body>
</html>
"""

def _write_html_dashboard(df: pd.DataFrame, path: Path) -> None:
    cols = [
        "student_id", "full_name", "campus_name", "risk_tier",
        "risk_score", "attendance_rate", "avg_score", "llm_intervention",
    ]
    records      = df[cols].fillna("").to_dict("records")
    students_json = json.dumps(records, ensure_ascii=False, default=str)

    html = HTML_TEMPLATE.format(
        run_date=datetime.now().strftime("%Y-%m-%d %H:%M"),
        total=len(df),
        campus_count=df["campus_id"].nunique(),
        students_json=students_json,
    )
    path.write_text(html, encoding="utf-8")
```

**Key rules for file:// compatibility:**
- No `fetch()`, `XMLHttpRequest`, or ES `import` — all blocked by browser CORS
  when opening via file:// protocol.
- No external CSS/JS (Google Fonts CDN, Chart.js CDN, etc.) — blocked offline.
- All data as a `const` assignment inside `<script>`, not a sibling `.json` file.
- `json.dumps(..., default=str)` handles datetime/Decimal/numpy types silently.
- `ensure_ascii=False` is required for Arabic student names.
- Double-brace all CSS/JS `{` `}` in Python `str.format()` strings: `{{` `}}`.
- At 5,000 students, the embedded JSON is ~2-3 MB — acceptable for a dashboard file.
- Use `fillna("")` before `to_dict("records")` so None becomes empty string in JS,
  not `null` (which would require null-checks throughout the template).

---

## Build Order (Dependency Graph)

```
Step 1: config.py           ── no deps ─────────────────────────────► foundation
Step 2: ingestion.py        ── needs: config.py ─────────────────────► data
Step 3: risk_engine.py      ── needs: ingestion output schema ────────► scoring
Step 4: llm_engine.py       ── needs: risk_engine output schema ───────► enrichment
         ├── _build_campus_batches()
         ├── _call_with_retry()
         ├── _parse_llm_response()
         └── _rule_based_intervention()
Step 5: output_generator.py ── needs: llm_engine output schema ───────► outputs
         ├── _write_priority_excel()
         ├── _write_campus_excel()
         ├── _write_whatsapp_csv()
         ├── _write_word_report()
         ├── _write_html_dashboard()
         └── _write_json_log()
Step 6: doc_generator.py    ── needs: config.py only ────────────────► docs (parallel)
Step 7: main.py             ── needs: all modules ───────────────────► orchestrator
```

### Recommended Build Sequence

Build in this order, writing tests at each step before advancing:

1. **config.py + constants.py** — weight definitions, tier thresholds, file paths.
   Test: load config dict, assert required keys present.

2. **ingestion.py** — merge 3 CSVs, normalize, validate schema.
   Test: with synthetic CSVs, assert output column set + dtypes + no duplicate IDs.

3. **risk_engine.py** — deterministic scoring.
   Test: with known input values, assert expected score and tier assignments. Pure
   function — no mocking needed, trivially testable.

4. **llm_engine.py (offline path first)** — build all helpers before the API call.
   Test: `_build_campus_batches()`, `_parse_llm_response()`, `_rule_based_intervention()`
   with pre-canned response strings. Use `unittest.mock.patch` on
   `anthropic.Anthropic.messages.create` to test the retry logic without real calls.

5. **output_generator.py** — one writer at a time, smallest first (CSV, then Excel,
   then HTML, then Word).
   Test: write to `tmp_path` (pytest fixture), load back with `openpyxl.load_workbook()`,
   assert expected worksheets, cell values, fill colors.

6. **Integration test** — run full pipeline on 50-row synthetic dataset.
   Assert all output files created, non-empty, no uncaught exceptions, run log valid JSON.

7. **doc_generator.py** — lowest priority, pure formatting, no live-data dependencies.
   Can be developed in parallel with Steps 4–5.

### Critical Cross-Dependencies

- `output_generator.py` must be written AFTER `llm_engine.py` output schema is frozen.
  The `llm_source` column controls "rule-based" footnotes in Excel and Word.
- `_write_whatsapp_csv()` depends on `phone_whatsapp` being E.164-formatted — this is
  an ingestion contract, not an output contract. Assert in ingestion tests.
- `doc_generator.py` can be developed in parallel since it reads config + static
  templates, not the live DataFrame.
- `risk_engine.py` weights must be finalized before `llm_engine.py` prompt references
  specific score thresholds (e.g. "risk_score > 75 = CRITICAL").

---

## Scaling Path (18 -> 100 Campuses)

### Current State (18 campuses, 1,000 students)

- Sequential batch processing: one campus at a time, synchronous API calls.
- Target CRITICAL + HIGH: assume ~30% = 300 students / 10 per batch = 30 API calls.
- Wall time: ~30 calls x ~3s each = ~90 seconds. Fast.

### 6-Month State (100 campuses, 5,000 students)

- Same 30% fraction: 1,500 students / 10 per batch = 150 API calls.
- Sequential: ~150 x 3s = ~7.5 minutes. Borderline acceptable.
- If latency matters: switch `llm_engine.py` to async. The Anthropic Python SDK
  supports async natively (`anthropic.AsyncAnthropic`). Near-drop-in replacement.

```python
# Async upgrade path — change in llm_engine.py only
import asyncio
import anthropic

async def enrich_with_llm_async(
    df: pd.DataFrame,
    api_key: str,
    tiers: list[str] = ["CRITICAL", "HIGH"],
    batch_size: int = 10,
    concurrency: int = 5,  # Tune to stay under rate limits
) -> pd.DataFrame:
    client    = anthropic.AsyncAnthropic(api_key=api_key)
    batches   = _build_campus_batches(df, tiers, batch_size)
    semaphore = asyncio.Semaphore(concurrency)
    results_map: dict = {}

    async def process_batch(batch):
        async with semaphore:
            raw    = await _call_with_retry_async(client, SYSTEM_PROMPT, _build_prompt(batch))
            parsed = _parse_llm_response(raw, batch) if raw else {}
            _merge_batch_results(parsed, batch, df, results_map)

    await asyncio.gather(*[process_batch(b) for b in batches])
    return _apply_results_to_df(df, results_map)
```

### Scaling Decision Matrix

| Scale | Students | Campuses | LLM Approach | Est. Runtime |
|-------|----------|----------|--------------|--------------|
| Now   | 1,000    | 18       | Sync sequential | ~2 min |
| 6 mo  | 5,000    | 100      | Async concurrent (concurrency=5) | ~2-3 min |
| 1 yr  | 20,000   | 400      | Anthropic Message Batches API | ~10 min async or scheduled |

**Anthropic Message Batches API** (for 1-year scale): Submit all requests as a single
Batch API job, poll for completion, retrieve results. Allows 100,000 requests/batch,
50% cost reduction, but introduces 1-24 hour latency. Only use if pipeline runs
scheduled overnight rather than on-demand.

### DataFrame Scaling Notes

- At 5,000 students, pandas stays in-memory fine. No chunking, no Dask.
- The only expensive operation is `groupby("campus_id")` — using `pd.Categorical`
  makes this O(n) and fast.
- `openpyxl` is slow for >10,000 rows. At 5,000 rows across 100 campus sheets,
  expect ~30-60 seconds for Excel generation. Acceptable for a batch pipeline.
  If it becomes a bottleneck, switch the master list to `xlsxwriter`
  (write-only, 5-10x faster, but loses read support).

### Output File Count at Scale

| Campuses | Excel files | Total output files |
|----------|-------------|-------------------|
| 18       | 19          | ~25 |
| 100      | 101         | ~108 |

Create `outputs/{YYYY-MM-DD}/` subdirectory per run. Do not flatten all outputs
into a single directory — file managers become unusable at 100+ files with no
structure.

---

## Sources

- Anthropic Python SDK (HIGH confidence — stable API since v0.20, async support
  via `AsyncAnthropic` documented since 2024)
- openpyxl 3.x documentation (HIGH confidence — PatternFill, freeze_panes, column
  dimensions API stable since 3.0)
- pandas 2.x documentation (HIGH confidence — DataFrame groupby, Categorical,
  to_dict patterns unchanged)
- Python asyncio + semaphore concurrency (HIGH confidence — standard library)
- Single-file HTML / file:// CORS constraint (HIGH confidence — browser security
  model, no external source needed)
- Anthropic Message Batches API (MEDIUM confidence — documented in 2024 SDK
  releases, 50% cost reduction claim from official announcement)
