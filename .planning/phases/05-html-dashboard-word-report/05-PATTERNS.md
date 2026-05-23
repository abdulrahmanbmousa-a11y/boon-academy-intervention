# Phase 5: HTML Dashboard + Word Report - Pattern Map

**Mapped:** 2026-05-23
**Files analyzed:** 4 (2 modified, 1 new, 1 extended test file)
**Analogs found:** 4 / 4

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `src/output_generator.py` (extend) | service | file-I/O | `src/output_generator.py` (Phase 4 helpers) | exact |
| `src/config.py` (extend) | config | transform | `src/config.py` lines 119-130 (`OUTPUT_COLS_PRIORITY`, `OUTPUT_COLS_CAMPUS`) | exact |
| `src/templates/dashboard.html.j2` | utility | file-I/O | `src/llm_templates.yaml` + `src/llm_engine.py` lines 55-59 (file-adjacent loading) | role-match |
| `tests/test_output_generator.py` (extend) | test | request-response | `tests/test_output_generator.py` lines 24-604 (existing Phase 4 tests) | exact |

---

## Pattern Assignments

### `src/output_generator.py` — `_write_html_dashboard()` helper

**Analog:** `src/output_generator.py` — `_write_whatsapp_csv()` (lines 28-57)

**Private helper signature pattern** (lines 28-30):
```python
def _write_whatsapp_csv(df: pd.DataFrame, output_dir: Path) -> Path:
    """Write whatsapp_messages.csv for all CRITICAL and HIGH risk students.
    ...
    """
```
Phase 5 mirrors this exactly:
```python
def _write_html_dashboard(df: pd.DataFrame, output_dir: Path) -> Path:
    """Write facilitator_dashboard.html — fully self-contained HTML file.
    ...
    """
```

**df.copy() purity discipline** (lines 98-99 from `_write_priority_list`):
```python
def _write_priority_list(df: pd.DataFrame, output_dir: Path) -> Path:
    df_copy = df.copy()
```
Apply same pattern in `_write_html_dashboard` and `_write_report` — never mutate the incoming df.

**Column selection pattern** (lines 43-53 from `_write_whatsapp_csv`):
```python
    df_copy = df.copy()
    mask = df_copy[cfg.COL_RISK_LEVEL].isin(["CRITICAL", "HIGH"])
    cols = [
        cfg.COL_STUDENT_ID,
        cfg.COL_STUDENT_NAME,
        cfg.COL_PARENT_PHONE,
        cfg.COL_FACILITATOR_EMAIL,
        cfg.COL_CAMPUS_ID,
        cfg.COL_RISK_LEVEL,
        cfg.COL_WHATSAPP_MESSAGE,
        cfg.COL_GENERATED_BY,
    ]
```
Phase 5 replaces `cols` list with `cfg.DISPLAY_COLS_DASHBOARD` tuple (defined in config.py).

**Logging + return pattern** (lines 56-57 from `_write_whatsapp_csv`):
```python
    logger.info("Wrote whatsapp CSV: %s (%d rows)", path, mask.sum())
    return path
```
Phase 5 mirrors: `logger.info("Wrote HTML dashboard: %s (%d students)", path, len(df_copy))` then `return path`.

**Jinja2 file-adjacent loading pattern** (from `src/llm_engine.py` lines 55-59):
```python
_TEMPLATES_PATH = Path(__file__).parent / "llm_templates.yaml"

with _TEMPLATES_PATH.open("r", encoding="utf-8") as _f:
    _TEMPLATES: dict = yaml.safe_load(_f)
```
Phase 5 mirrors inside `_write_html_dashboard()` (lazy load, not module-level, since Jinja2 env is not needed until the helper is called):
```python
from jinja2 import Environment, FileSystemLoader
template_dir = Path(__file__).parent / "templates"
env = Environment(loader=FileSystemLoader(str(template_dir)), autoescape=False)
template = env.get_template("dashboard.html.j2")
```

**JSON injection safety** (from CLAUDE.md Critical Pitfalls):
```python
students_json = json.dumps(records).replace("</", "<\\/")
html = template.render(students_json=students_json, campus_ids=campus_ids)
```

**File write pattern** (from `_write_run_log` lines 77-78):
```python
    path = output_dir / "run_log.json"
    path.write_text(json.dumps(run_log, indent=2, default=str), encoding="utf-8")
```
Phase 5 mirrors for HTML:
```python
    path = output_dir / "facilitator_dashboard.html"
    path.write_text(html, encoding="utf-8")
```

---

### `src/output_generator.py` — `_write_report()` helper

**Analog:** `src/output_generator.py` — `_write_campus_dashboards()` (lines 155-287)

**Multi-parameter private helper signature** (lines 155-157):
```python
def _write_campus_dashboards(
    df: pd.DataFrame, output_dir: Path
) -> dict[str, Path]:
```
Phase 5 `_write_report` needs `run_log` as a third parameter (per CONTEXT.md Discretion):
```python
def _write_report(df: pd.DataFrame, run_log: dict, output_dir: Path) -> Path:
    """Write intervention_report.docx — programmatic Word document.
    ...
    """
```

**Stats computation pattern** (lines 201-206 from `_write_campus_dashboards`):
```python
        total = len(campus_df)
        critical_count = int((campus_df[cfg.COL_RISK_LEVEL] == "CRITICAL").sum())
        high_count = int((campus_df[cfg.COL_RISK_LEVEL] == "HIGH").sum())
        coverage_pct = (
            round((critical_count + high_count) / total * 100, 1) if total > 0 else 0.0
        )
```
Phase 5 uses the same groupby/value_counts approach for the executive summary risk breakdown table and campus summary table.

**Logging + return pattern** (lines 283-285):
```python
        logger.info("Wrote campus dashboard: %s (%d students)", path, total)
        results[f"campus_{campus_id}"] = path
```
Phase 5 mirrors: `logger.info("Wrote Word report: %s (%d students)", path, len(df_copy))` then `return path`.

---

### `src/output_generator.py` — `write_outputs()` orchestrator extension

**Analog:** `src/output_generator.py` lines 290-341 (the existing orchestrator)

**Current orchestrator pattern** (lines 322-340):
```python
    paths: dict[str, Path] = {}

    priority_path = _write_priority_list(df, output_dir)
    paths["priority_list"] = priority_path

    campus_paths = _write_campus_dashboards(df, output_dir)
    paths.update(campus_paths)

    whatsapp_path = _write_whatsapp_csv(df, output_dir)
    paths["whatsapp"] = whatsapp_path

    run_log_path = _write_run_log(run_log, output_dir)
    paths["run_log"] = run_log_path

    logger.info(
        "All outputs written to %s — keys: %s",
        output_dir,
        list(paths.keys()),
    )
    return paths
```
Phase 5 appends two more calls before the final `logger.info`:
```python
    dashboard_path = _write_html_dashboard(df, output_dir)
    paths["dashboard"] = dashboard_path

    report_path = _write_report(df, run_log, output_dir)
    paths["report"] = report_path
```
The docstring's `Returns:` section gains `"dashboard"` and `"report"` keys. The comment on line 302 ("D-09: Phase 5 will add...") is replaced with the actual calls.

---

### `src/config.py` — `DISPLAY_COLS_DASHBOARD` tuple

**Analog:** `src/config.py` lines 119-130 (`OUTPUT_COLS_PRIORITY`, `OUTPUT_COLS_CAMPUS`)

**Existing tuple pattern** (lines 120-130):
```python
# OUT-01 column order — 12 columns, exact sequence for intervention_priority_list.xlsx
OUTPUT_COLS_PRIORITY: tuple[str, ...] = (
    COL_RANK, COL_STUDENT_ID, COL_STUDENT_NAME, COL_CAMPUS_ID,
    COL_FACILITATOR_EMAIL, COL_RISK_SCORE, COL_RISK_LEVEL,
    COL_ATTENDANCE_RATE, COL_AVG_PRACTICE, COL_TREND_DIR,
    COL_DAYS_SINCE_NOTE, COL_RECOMMENDED_ACTION,
)

# OUT-02 campus dashboard columns — standard 12 + 3 LLM columns = 15 total (D-05)
OUTPUT_COLS_CAMPUS: tuple[str, ...] = OUTPUT_COLS_PRIORITY + (
    COL_FACILITATOR_SUMMARY, COL_WHATSAPP_MESSAGE, COL_GENERATED_BY,
)
```
Phase 5 adds immediately after (same style, same section, comment format matches):
```python
# OUT-05 HTML dashboard display columns — 12 columns (D-02)
DISPLAY_COLS_DASHBOARD: tuple[str, ...] = (
    COL_STUDENT_ID, COL_STUDENT_NAME, COL_CAMPUS_ID,
    COL_RISK_SCORE, COL_RISK_LEVEL,
    COL_ATTENDANCE_RATE, COL_AVG_PRACTICE, COL_TREND_DIR,
    COL_DAYS_SINCE_NOTE, COL_FACILITATOR_SUMMARY,
    COL_WHATSAPP_MESSAGE, COL_GENERATED_BY,
)
```
Note: No `COL_RANK` (rank is not pre-computed for HTML; JS sorts client-side). No `COL_RECOMMENDED_ACTION` (replaced by `COL_FACILITATOR_SUMMARY` in dashboard view per CONTEXT.md D-02).

**COLOR_* constants** (lines 109-114) — used directly in HTML template CSS, not re-declared:
```python
COLOR_CRITICAL: str = "FFFFCCCC"   # light red  — strip FF prefix -> #FFCCCC for CSS
COLOR_HIGH: str     = "FFFFE5CC"   # light orange -> #FFE5CC
COLOR_MEDIUM: str   = "FFFFFFCC"   # light yellow -> #FFFFCC
COLOR_LOW: str      = "FFCCFFCC"   # light green  -> #CCFFCC
```
CSS hex is the last 6 chars of the 8-char ARGB constant (strip the leading `FF`).

**Weight constants** (lines 60-63) — used verbatim in Word report methodology appendix:
```python
WEIGHT_ATTENDANCE: float = 0.35
WEIGHT_PRACTICE: float = 0.30
WEIGHT_TREND: float = 0.20
WEIGHT_NOTES: float = 0.15
```

---

### `src/templates/dashboard.html.j2` — NEW Jinja2 template file

**Analog:** `src/llm_templates.yaml` (file-adjacent resource) + `src/llm_engine.py` lines 55-59 (loading pattern)

This is a new file with no direct HTML analog in the codebase. The loading pattern is modeled on `llm_engine.py`. Key template variables injected from Python:

| Jinja2 variable | Python source | Type |
|---|---|---|
| `{{ students_json }}` | `json.dumps(records).replace("</", "<\\/")` | pre-serialized JSON string |
| `{{ campus_ids }}` | `sorted(df[cfg.COL_CAMPUS_ID].dropna().unique().tolist())` | list of strings |
| `{{ run_timestamp }}` | `run_log["run_timestamp"]` | string (ISO 8601) |

Template must use `autoescape=False` in Jinja2 `Environment` because `students_json` is pre-serialized JSON embedded in a `<script>` tag — Jinja2 HTML-escaping would corrupt the JSON quotes.

Directory to create: `src/templates/` (new subdirectory alongside `src/llm_templates.yaml`).

---

### `tests/test_output_generator.py` — Phase 5 test extensions

**Analog:** `tests/test_output_generator.py` lines 86-604 (existing Phase 4 test patterns)

**Import extension pattern** (lines 15-21):
```python
from src.output_generator import (
    _write_campus_dashboards,
    _write_priority_list,
    _write_run_log,
    _write_whatsapp_csv,
    write_outputs,
)
```
Phase 5 adds `_write_html_dashboard` and `_write_report` to this import block.

**Helper-scoped fixture pattern** (lines 194-197):
```python
@pytest.fixture
def priority_list_path(sample_df: pd.DataFrame, tmp_path: Path) -> Path:
    """Write priority list to tmp_path and return the path for round-trip assertions."""
    return _write_priority_list(sample_df, tmp_path)
```
Phase 5 mirrors:
```python
@pytest.fixture
def html_dashboard_path(sample_df: pd.DataFrame, tmp_path: Path) -> Path:
    """Write HTML dashboard to tmp_path and return the path for round-trip assertions."""
    return _write_html_dashboard(sample_df, tmp_path)

@pytest.fixture
def report_path(sample_df: pd.DataFrame, sample_run_log: dict, tmp_path: Path) -> Path:
    """Write Word report to tmp_path and return the path for round-trip assertions."""
    return _write_report(sample_df, sample_run_log, tmp_path)
```

**Returns-Path assertion pattern** (lines 129-134):
```python
def test_whatsapp_csv_returns_path(sample_df: pd.DataFrame, tmp_path: Path) -> None:
    """Return value is a Path object pointing to the written file."""
    result = _write_whatsapp_csv(sample_df, tmp_path)
    assert isinstance(result, Path), f"Expected Path, got {type(result)}"
    assert result.exists(), f"Returned path does not exist: {result}"
    assert result.name == "whatsapp_messages.csv"
```
Phase 5 mirrors for both new helpers — assert `isinstance(result, Path)`, `result.exists()`, and exact filename.

**Integration test key-assertion pattern** (lines 559-578):
```python
def test_write_outputs_returns_all_keys(...) -> None:
    """write_outputs returns dict with 'priority_list', campus_* keys, 'whatsapp', 'run_log'."""
    result = write_outputs(full_sample_df, tmp_path, sample_run_log_full)
    assert "priority_list" in result, ...
    campus_keys = [k for k in result if k.startswith("campus_")]
    assert len(campus_keys) >= 1, ...
    assert "whatsapp" in result, ...
    assert "run_log" in result, ...
```
Phase 5 extends this test to also assert:
```python
    assert "dashboard" in result, f"Missing key 'dashboard' in result: {list(result.keys())}"
    assert "report" in result, f"Missing key 'report' in result: {list(result.keys())}"
```

**File-content round-trip pattern** (lines 142-156 from `test_run_log_keys`):
```python
def test_run_log_keys(sample_run_log: dict, tmp_path: Path) -> None:
    path = _write_run_log(sample_run_log, tmp_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    required_keys = {...}
    missing = required_keys - set(data.keys())
    assert not missing, f"Missing keys in run_log.json: {missing}"
```
Phase 5 HTML dashboard test reads the file and parses the embedded JSON:
```python
def test_html_dashboard_contains_student_data(html_dashboard_path: Path) -> None:
    content = html_dashboard_path.read_text(encoding="utf-8")
    assert "studentsData" in content, "Expected JS const 'studentsData' in HTML"
    assert "S001" in content, "Expected student_id S001 in embedded JSON"
```
Phase 5 Word report test opens with python-docx:
```python
from docx import Document
def test_report_file_exists(report_path: Path) -> None:
    assert report_path.exists()
    assert report_path.name == "intervention_report.docx"
    doc = Document(str(report_path))
    assert len(doc.paragraphs) > 0, "Expected non-empty Word document"
```

**sample_df fixture** (lines 24-69) — reused as-is for Phase 5 helper tests. It already contains all columns needed (`COL_FACILITATOR_SUMMARY`, `COL_WHATSAPP_MESSAGE`, `COL_GENERATED_BY`, all risk levels). `sample_run_log` fixture (lines 72-83) reused as-is for `_write_report` tests.

---

## Shared Patterns

### Logger instantiation
**Source:** `src/output_generator.py` line 25
**Apply to:** All additions to `output_generator.py`
```python
logger = logging.getLogger(__name__)
```
Already present at module level — no re-declaration needed.

### Column name constants (never bare strings)
**Source:** `src/config.py` lines 70-103; `src/output_generator.py` throughout
**Apply to:** `_write_html_dashboard`, `_write_report`, template variable preparation
```python
from src import config as cfg
# Always: cfg.COL_RISK_LEVEL, cfg.COL_STUDENT_NAME, etc.
# Never: "risk_level", "student_name"
```

### df.copy() at entry for purity
**Source:** `src/output_generator.py` lines 98, 175
**Apply to:** Both new helpers
```python
df_copy = df.copy()
# All operations on df_copy, never on df
```

### zero print statements
**Source:** CLAUDE.md Code Standards
**Apply to:** All new code — `logging.getLogger(__name__)` calls only, no `print()`.

### Path return discipline
**Source:** `src/output_generator.py` lines 55-57, 77-78, 150-152
**Apply to:** Both new helpers — always `return path` where `path = output_dir / "filename"`.

---

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `src/templates/dashboard.html.j2` | utility (template) | file-I/O | No HTML/Jinja2 templates exist in codebase; loading pattern borrowed from `llm_engine.py` file-adjacent YAML pattern |

---

## Metadata

**Analog search scope:** `src/`, `tests/`
**Files scanned:** `src/output_generator.py` (342 lines), `src/config.py` (130 lines), `src/llm_engine.py` (lines 1-59), `tests/test_output_generator.py` (605 lines)
**Pattern extraction date:** 2026-05-23
