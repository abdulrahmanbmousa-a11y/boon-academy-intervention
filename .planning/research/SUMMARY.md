# Research Summary: boon-academy-intervention

> Synthesized: 2026-05-21 | Sources: STACK.md, FEATURES.md, ARCHITECTURE.md, PITFALLS.md

---

## Recommended Stack

### Pinned Versions

| Package | Version | Role |
|---------|---------|------|
| `pandas` | 2.2.3 | CSV ingestion, DataFrame pipeline |
| `openpyxl` | 3.1.5 | Excel generation (read+write+style) |
| `python-docx` | 1.1.2 | Word report + 8 documentation files |
| `anthropic` | 0.103.1 | Claude API client |
| `python-dotenv` | 1.2.2 | API key / config management |
| `jinja2` | 3.1.6 | Self-contained HTML dashboard |
| `tenacity` | 9.1.4 | Optional: only if custom retry callbacks needed |
| `pytest` | 8.3.5 | Test runner |
| `pytest-mock` | 3.15.1 | `mocker` fixture |
| `pytest-cov` / `coverage` | 7.1.0 / 7.14.0 | Coverage reporting |
| `respx` | 0.23.1 | Mock Anthropic SDK HTTP calls (uses httpx internally) |
| `freezegun` | 1.5.5 | Freeze timestamps for run_log assertions |

### Key Technology Choices

- **pandas 2.2.3 not 3.x** — pandas 3.0 forces Copy-on-Write as mandatory default; 2.2.3 has it as opt-in. Avoids silent mutation bugs for a new codebase.
- **openpyxl not xlsxwriter** — xlsxwriter is write-only. openpyxl supports read+write+append, required for ExcelWriter append mode and post-write cell assertions in tests.
- **python-docx 1.1.2 not 1.2.0** — 1.2.0 broke `OxmlElement` namespace and has open table-border issues.
- **respx not responses** — The Anthropic SDK uses `httpx`, not `requests`. The `responses` library silently fails to intercept SDK calls.
- **SDK built-in retries first** — `anthropic.Anthropic(max_retries=3)` handles 429/500/502/503/529 with exponential backoff.
- **Model: `claude-sonnet-4-5`** — as specified in project constraints.

### What NOT to Use

| Library | Reason |
|---------|--------|
| `xlsxwriter` | Write-only, no append mode |
| `pandas >= 3.0` | Mandatory CoW breaks chained assignment patterns |
| `responses` (mock) | Mocks `requests`, not `httpx` — won't intercept Anthropic SDK |
| `python-docx >= 1.2.0` | Unstable `OxmlElement` refactor |
| `httpretty` | Socket-level mocking, incompatible with `httpx` |

---

## Table Stakes Features

Without these, facilitators will not use the system:

| Feature | Why Non-Negotiable |
|---------|-------------------|
| **Daily prioritized student list (top 10 max)** | More than 10 urgent students = zero contacts made |
| **Single risk score per student (traffic-light)** | Multiple sub-scores require synthesis they will not do |
| **Pre-drafted parent message** | Highest friction point is message composition |
| **WhatsApp deep link (wa.me)** | Facilitators live in WhatsApp — extra app login kills adoption |
| **Campus-level scoping** | Cross-campus data = noise + privacy |
| **Intervention logging** | Without this, same students resurface daily |
| **Google Sheets / Excel as primary UI** | Non-technical staff will not install new apps |

**Anti-features to exclude:** student-facing portal, real-time scoring, multi-tab dashboards, ML-based predictions, automated message sending without review, per-student trend charts.

---

## Architecture Shape

### Pipeline Structure

```
CSV files (3)
     |
[ingestion.py]       --> unified DataFrame (one row per student_id)
     |
[risk_engine.py]     --> +risk_score, +risk_tier, +score_components
     |
[llm_engine.py]      --> +llm_intervention, +llm_rationale, +llm_source, +llm_error
     |                    (CRITICAL + HIGH students only, batched 10/campus-call)
[output_generator.py]--> Excel (master + per-campus) | Word | HTML | CSV | JSON
     |
[doc_generator.py]   --> 8 x .docx documentation files (can run in parallel)
     |
[main.py]            --> orchestrator only, zero business logic
```

### Module Contracts

- **ingestion.py**: `ingest(data_paths) -> DataFrame` — merges, normalizes dtypes, deduplicates, validates schema. All downstream modules assume clean data.
- **risk_engine.py**: `score_risk(df) -> DataFrame` — pure function, deterministic, no I/O
- **llm_engine.py**: `enrich_with_llm(df, api_key) -> DataFrame` — never raises; failures recorded in `llm_error`
- **output_generator.py**: `write_outputs(df, output_dir) -> dict[str, Path]` — idempotent

### Build Order

1. `config.py` + constants
2. `ingestion.py` (freeze schema before anything else)
3. `risk_engine.py`
4. `llm_engine.py` (offline helpers first, then API)
5. `output_generator.py` (CSV → Excel → HTML → Word)
6. Integration test on synthetic dataset
7. `doc_generator.py` (can parallelize with 4-5)

---

## Top 10 Pitfalls to Avoid

| # | Pitfall | Prevention |
|---|---------|-----------|
| 1 | pandas reads numeric IDs as float64 | `dtype={"student_id": "str"}` in every `read_csv` |
| 2 | Claude returns markdown-wrapped JSON | Strip code fences; use tool-use for structured output |
| 3 | PatternFill silently produces no color | Always `PatternFill(fill_type="solid", fgColor="RRGGBB")` |
| 4 | `</script>` injection breaks HTML | `json.dumps(data).replace("</", "<\\/")` |
| 5 | Prompt injection via student notes | Wrap in `<student_data>` XML delimiters |
| 6 | openpyxl color assertions fail (8-char hex) | Assert `"00FFCCCC"` not `"FFCCCC"` in tests |
| 7 | `responses` mock doesn't intercept Anthropic SDK | Use `respx` |
| 8 | Phone numbers drop leading zeros | `dtype={"parent_phone": "str"}` at ingestion |
| 9 | Missing value fillna(0) inflates risk scores | Keep NaN; handle explicitly in scorer |
| 10 | Date format ambiguity produces wrong attendance | `pd.to_datetime(col, format="%Y-%m-%d", errors="raise")` |

---

## Key Decisions Already Made

1. Daily batch pipeline, not real-time
2. Rule-based risk scoring, not ML (defer to v2 after labeled data accumulates)
3. One API call per campus batch (10 students), not per-student
4. openpyxl over xlsxwriter
5. Jinja2 for self-contained HTML (no server, no CDN, works via file://)
6. wa.me deep links, not WhatsApp Business API
7. Three-layer LLM error handling — pipeline never halts on API failure
8. `llm_source` column tracks fallback origin for output footnotes
9. `os.environ["KEY"]` not `os.getenv("KEY")` — fail at startup
10. UTF-8 only for CSVs — no encoding auto-detection

---

## Open Questions

1. Risk weight calibration — defaults need academic director validation
2. Arabic dialect per campus — Modern Standard vs. Gulf dialect
3. Expected CRITICAL+HIGH student count in real data (affects cost estimate)
4. LibreOffice vs Excel on facilitator PCs

---

## Phase Implications

| Phase | Focus | Critical Pitfall |
|-------|-------|-----------------|
| Phase 1: Foundation + Ingestion | config.py, ingestion.py, synthetic data | dtype float promotion, phone mangling, silent duplicates |
| Phase 2: Risk Scoring | risk_engine.py (pure function) | Weight boundary conditions, NaN handling |
| Phase 3: Claude API | llm_engine.py, three-layer fallback | JSON parsing, prompt injection, respx mocking |
| Phase 4: Excel + CSV Output | output_generator.py (Excel + CSV) | PatternFill fill_type, 8-char hex in tests |
| Phase 5: HTML + Word Output | output_generator.py (HTML + docx) | </script> injection, python-docx cross-app compat |
| Phase 6: Documentation | doc_generator.py (8 x .docx) | python-docx table borders in Google Docs |
| Phase 7: Tests + Integration | Full test suite + integration test | respx setup, freezegun, edge case fixtures |
| Phase 8: Polish + Hardening | End-to-end verification, quality gates | All of the above at once |
