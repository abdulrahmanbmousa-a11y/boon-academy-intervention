---
phase: 06-documentation-suite
reviewed: 2026-05-24T15:30:00Z
depth: standard
files_reviewed: 3
files_reviewed_list:
  - main.py
  - src/doc_generator.py
  - src/templates/docs_content.yaml
findings:
  critical: 2
  warning: 4
  info: 2
  total: 8
status: issues_found
---

# Phase 6: Code Review Report

**Reviewed:** 2026-05-24T15:30:00Z
**Depth:** standard
**Files Reviewed:** 3
**Status:** issues_found

## Summary

Three files were reviewed at standard depth: the pipeline orchestrator (`main.py`), the new documentation generation module (`src/doc_generator.py`), and the static YAML content template (`src/templates/docs_content.yaml`).

The `main.py` wiring is correct — import, call signature (`write_docs(df, run_log, cfg.DOCS_DIR)`), and log statement all match `doc_generator.write_docs()` exactly. The YAML is structurally valid and all seven required top-level keys are present.

Two critical defects were found. First, the module-level YAML load executes at import time with no error handling; a missing or malformed `docs_content.yaml` raises an unhandled exception that kills the entire process before `main()` runs, before logging is even configured, producing a bare Python traceback rather than a logged pipeline error. Second, `analysis.md` is written to `docs_dir.parent` (the project root) but `docs_dir.mkdir()` is the only directory creation in `write_docs()` — if the project root directory does not exist (unlikely but possible in some deployment paths), the `path.write_text()` call crashes with `FileNotFoundError` and is not caught. More importantly, the `analysis.md` path escapes the `docs_dir` subtree entirely, which contradicts the CLAUDE.md rule "all paths from env vars."

Four warnings were also found, including duplicate `logger.info` calls for every `_render_doc_from_content`-based helper, a missing `docs_dir` existence guard before the analysis.md write, an unused `content` parameter in `_write_analysis_docx`, and a silent empty-dict fallback that produces blank documents if a YAML key is missing.

---

## Critical Issues

### CR-01: Module-level YAML load crashes process at import with no error handling

**File:** `src/doc_generator.py:41-43`

**Issue:** Lines 41–43 open and parse `docs_content.yaml` unconditionally at module import time:

```python
with _CONTENT_PATH.open(encoding="utf-8") as _fh:
    _DOCS_CONTENT: dict = yaml.safe_load(_fh)
```

If the file is absent, renamed, or malformed YAML, this raises `FileNotFoundError` or `yaml.YAMLError` during `import src.doc_generator` — which happens inside `main()` before `setup_logging()` has configured the root logger. The exception propagates through `main.py` line 13 (`from src import doc_generator`), bypasses the `try/except` block in `main()` entirely, and surfaces as a raw Python traceback on stderr with no structured log message. The pipeline cannot write a partial `run_log.json` because it never reaches the `try` block.

`llm_engine.py` uses the identical pattern for `llm_templates.yaml` (per CLAUDE.md), but that module is also a known risk. The pattern is fragile here because `docs_content.yaml` is a new file added in Phase 6 and has a higher chance of being absent in a fresh clone that hasn't run the generator yet.

**Fix:** Wrap the module-level load in a try/except and re-raise with a descriptive message, or defer the load into `write_docs()`:

```python
# Option A — fail loudly at import with a clean message
try:
    with _CONTENT_PATH.open(encoding="utf-8") as _fh:
        _DOCS_CONTENT: dict = yaml.safe_load(_fh)
except FileNotFoundError as exc:
    raise FileNotFoundError(
        f"docs_content.yaml not found at {_CONTENT_PATH}. "
        "Ensure src/templates/docs_content.yaml is present."
    ) from exc
except yaml.YAMLError as exc:
    raise ValueError(f"docs_content.yaml is malformed: {exc}") from exc

# Option B — defer load into write_docs() so it runs inside main()'s try/except
def write_docs(df: pd.DataFrame, run_log: dict, docs_dir: Path) -> dict[str, Path]:
    docs_content = _load_docs_content()  # raises inside the try block, gets logged
    ...
```

---

### CR-02: `analysis.md` written outside `docs_dir` subtree — path escapes env-var-controlled directory

**File:** `src/doc_generator.py:185`

**Issue:** `_write_analysis_md` writes to `docs_dir.parent / "analysis.md"` — the project root — not into `docs_dir`:

```python
path = docs_dir.parent / "analysis.md"
```

This violates the CLAUDE.md rule "all paths from env vars — zero hardcoded paths." The `docs_dir` variable comes from `cfg.DOCS_DIR` (env-var controlled), but `docs_dir.parent` is the parent of that directory and is not controlled by any env var. If `DOCS_DIR` is set to `docs` (the default), `docs_dir.parent` is the current working directory — acceptable for local runs but not for any deployment where the working directory differs from the project root. If `DOCS_DIR` is set to an absolute path (e.g., `/var/pipeline/docs`), `docs_dir.parent` becomes `/var/pipeline`, which is silently wrong.

Additionally, `write_docs()` only calls `docs_dir.mkdir(parents=True, exist_ok=True)` — it does not guarantee the parent directory exists. If it does not exist, `path.write_text()` raises `FileNotFoundError`.

**Fix:** Either write `analysis.md` into `docs_dir` (making its location consistent with all other outputs), or accept an explicit `project_root` parameter in `write_docs()` and pass `cfg.PROJECT_ROOT` from `config.py`:

```python
# Option A — write into docs_dir (simplest fix, no API change)
path = docs_dir / "analysis.md"

# Option B — explicit project_root parameter (matches documented D-11 intent)
def write_docs(
    df: pd.DataFrame,
    run_log: dict,
    docs_dir: Path,
    project_root: Path | None = None,
) -> dict[str, Path]:
    root = project_root or Path.cwd()
    ...
    # in _write_analysis_md:
    path = root / "analysis.md"
```

Option A is the minimal correct fix. Option B matches the docstring's "project root" intent but requires updating `main.py` and adding `PROJECT_ROOT` to `config.py`.

---

## Warnings

### WR-01: Double `logger.info` for every `_render_doc_from_content`-based helper

**File:** `src/doc_generator.py:90, 401, 423, 446, 471, 577, 600`

**Issue:** `_render_doc_from_content()` logs `"Wrote doc: %s"` at line 90. Each calling helper (`_write_architecture`, `_write_security`, `_write_engineering_decisions`, `_write_data_handling`, `_write_system_design`, `_write_alternatives`) also logs a second `"Wrote <name>.docx: %s"` message after calling the shared helper. Every one of these six files produces two log lines per write — one generic, one specific. The generic line from the shared helper is redundant noise that adds nothing over the specific line from the caller.

**Fix:** Remove `logger.info("Wrote doc: %s", path)` from `_render_doc_from_content()` (line 90). Each caller's specific log message is already sufficient. The shared helper should be a pure rendering function with no logging side effect.

---

### WR-02: `content` parameter of `_write_analysis_docx` is accepted but never used — misleading signature

**File:** `src/doc_generator.py:282`

**Issue:** `_write_analysis_docx(run_log, docs_dir, content)` accepts a `content: dict` parameter (line 282) that is documented as "Unused" and is never referenced in the function body. The call site at line 135 passes `_DOCS_CONTENT` (the full parsed YAML dict, not a specific sub-key):

```python
paths["analysis_docx"] = _write_analysis_docx(run_log, docs_dir, _DOCS_CONTENT)
```

This is confusing — the parameter is named `content` but receives the entire YAML document, and then does nothing with it. It adds noise to every call site and the function signature, and any future developer who sees `content: dict` in the signature will reasonably assume it is used.

**Fix:** Remove the `content` parameter entirely from `_write_analysis_docx` and from its call site:

```python
# Function signature
def _write_analysis_docx(run_log: dict, docs_dir: Path) -> Path:

# Call site in write_docs()
paths["analysis_docx"] = _write_analysis_docx(run_log, docs_dir)
```

---

### WR-03: Silent empty-dict fallback silently produces blank documents when YAML keys are missing

**File:** `src/doc_generator.py:136-152`

**Issue:** Every call to a `_write_*` helper uses `.get(key, {})` as the content source:

```python
paths["architecture"] = _write_architecture(docs_dir, _DOCS_CONTENT.get("architecture", {}))
paths["security"] = _write_security(docs_dir, _DOCS_CONTENT.get("security", {}))
# ... etc for all 7 static docs
```

If a YAML key is missing or misspelled (e.g., `architectur` instead of `architecture`), `_DOCS_CONTENT.get()` returns `{}` silently. `_render_doc_from_content` then receives an empty dict, produces a `.docx` file with only a fallback title and no sections, and logs success. The pipeline completes with no error indication. The defect is only discovered when a human opens the document and finds it blank.

**Fix:** Assert or raise on missing keys before dispatching, or validate `_DOCS_CONTENT` keys at load time:

```python
_REQUIRED_KEYS = {
    "architecture", "security", "engineering_decisions",
    "data_handling", "scalability", "system_design", "alternatives"
}

# After loading YAML:
missing = _REQUIRED_KEYS - set(_DOCS_CONTENT.keys())
if missing:
    raise ValueError(f"docs_content.yaml is missing required keys: {missing}")
```

Alternatively, replace `.get(key, {})` with `_DOCS_CONTENT[key]` in `write_docs()` so a `KeyError` surfaces immediately with a clear key name.

---

### WR-04: `_write_analysis_md` accesses `df[cfg.COL_RISK_LEVEL]` without guarding against a missing column

**File:** `src/doc_generator.py:188`

**Issue:** Line 188 directly indexes the DataFrame:

```python
risk_dist = df[cfg.COL_RISK_LEVEL].value_counts().to_dict()
```

If `score_risk()` failed to add the `risk_level` column (e.g., due to a bug in Phase 2 that silently returned the DataFrame without the column), this raises `KeyError: 'risk_level'`. The exception propagates out of `_write_analysis_md`, out of `write_docs()`, and is caught by `main()`'s broad `except Exception` block — but at that point `paths` is partially populated (analysis_md failed, analysis_docx and all static docs were never attempted). The run_log records `"unrecoverable_error"` but gives no indication that 8 of 9 documentation files were never written.

This is especially risky because `doc_generator` is called after `write_outputs()` has already succeeded — a crash here discards all documentation with no user-visible explanation beyond the generic error log.

**Fix:** Add a column guard at the start of `_write_analysis_md`:

```python
if cfg.COL_RISK_LEVEL not in df.columns:
    logger.warning(
        "Column '%s' missing from DataFrame — risk distribution will show all zeros",
        cfg.COL_RISK_LEVEL,
    )
    risk_dist = {}
else:
    risk_dist = df[cfg.COL_RISK_LEVEL].value_counts().to_dict()
```

---

## Info

### IN-01: `write_docs()` logs its own summary but so does `main.py` — duplicate summary log

**File:** `src/doc_generator.py:154` and `main.py:99`

**Issue:** `write_docs()` logs `"docs written: %s"` at line 154. `main.py` logs the identical message at line 99:

```python
# doc_generator.py line 154
logger.info("docs written: %s", list(paths.keys()))

# main.py line 99
logger.info("docs written: %s", list(doc_paths.keys()))
```

Both log at INFO level and produce the same key list. The main.py log uses logger name `"main"`; the doc_generator log uses `"src.doc_generator"`. Operators reading the log will see the same key list twice within milliseconds. This is minor noise but inconsistent with how `output_generator` is handled (only `main.py` logs the output paths summary).

**Fix:** Remove the redundant `logger.info("docs written: ...")` from `write_docs()` at line 154. The per-file logs from each helper are sufficient for `src.doc_generator`; the summary belongs in `main.py`.

---

### IN-02: Hardcoded cost figures in `_write_scalability` docstring and YAML will drift from reality

**File:** `src/doc_generator.py:484-489` and `src/templates/docs_content.yaml:351-453`

**Issue:** Cost projection numbers (31,771 tokens, 106 tokens/student, $6/million blended, 20 campuses = 14 API calls) are duplicated between the `_write_scalability` docstring (lines 484–489) and the YAML content (lines 351–453). These are demo-run snapshot numbers. When the pipeline is run against real student data, these numbers will be wrong but the documents will still assert them as facts. The YAML is static content, so it will never auto-update.

This is not a code bug — it is a documentation maintenance hazard. The numbers are at least consistent between the docstring and YAML (no contradiction), but anyone updating the demo run will need to remember to update both locations.

**Fix:** Add a comment at the top of the `scalability:` block in `docs_content.yaml` noting that these are demo-run snapshot figures and must be updated when run against real data:

```yaml
# MAINTENANCE NOTE: figures below are from the 300-student synthetic demo run.
# Update token counts, API call counts, and cost estimates after the first real-data run.
scalability:
```

---

_Reviewed: 2026-05-24T15:30:00Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
