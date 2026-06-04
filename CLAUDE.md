# boon-academy-intervention

AI-powered student intervention pipeline for Boon Academy. Raises facilitator intervention rates from 30% to 80%+ by scoring student risk,
generating prioritized action lists, and drafting WhatsApp parent messages using Claude AI.

## Quick Start

pip install -r requirements.txt
cp .env.example .env  # fill in ANTHROPIC_API_KEY
python main.py

## Project Structure

main.py                  # Orchestrator - pure coordination, zero business logic
src/
  config.py              # Env var loading + column name constants (fails loudly if vars missing)
  ingestion.py           # CSV ingestion to clean unified DataFrame
  risk_engine.py         # Deterministic 5-component weighted risk scoring (pure function, no I/O)
  llm_engine.py          # Claude API integration - campus-batched + parallelized, three-layer fallback
  output_generator.py    # All output files: priority list, campus dashboards, WhatsApp CSV, HTML dashboard, PDF report, run log
  doc_generator.py       # PDF documentation suite (architecture, security, scalability, and more) + analysis.md
  llm_templates.yaml     # Fallback message templates (CRITICAL / HIGH variants)
  generate_data.py       # Synthetic data generator (retired - real CSVs now in data/)
data/                    # Input CSVs from Noon Academy (student_metadata, student_daily_metrics, facilitator_notes)
outputs/                 # Generated output files (gitignored except for demo run)
docs/                    # Generated PDF documentation files + analysis.md
tests/                   # pytest suite

## Key Technical Decisions

- Risk scoring is deterministic - 5-component weighted formula (attendance 30%, practice 25%, academic 20%, trend 15%, notes 10%). No training data needed.
- LLM calls are batched by campus and parallelized - ThreadPoolExecutor runs campus batches concurrently; one batch call per campus CRITICAL/HIGH students, not per student
- Three-layer fallback - SDK max_retries=3 then re-prompt on transient API error then rule-based YAML template. Pipeline never halts.
- _build_prompt() uses json.dumps(indent=2) - student data formatted as readable JSON; raw dict repr caused malformed/incomplete LLM responses (10+ fallbacks per run before fix)
- PII discipline - student_name and parent_phone never appear in API prompts or log statements
- openpyxl not xlsxwriter - xlsxwriter is write-only; openpyxl supports read/write/append
- pandas 2.2.3 not 3.x - Copy-on-Write is opt-in in 2.x; mandatory in 3.x (breaking)
- respx for API mocking - Anthropic SDK uses httpx; responses library silently misses SDK calls
- HTML dashboard is fully self-contained - all data embedded as JS const, works via file://
- Report is PDF not docx - fpdf2 generates intervention_report.pdf; no .docx report is produced

## Code Standards

- Type hints on ALL functions
- Docstrings on all public classes and methods
- Python logging module throughout - zero print statements
- All column names as constants in src/config.py - no hardcoded strings in logic
- All paths from env vars - zero hardcoded paths

## Critical Pitfalls (do not repeat these)

- dtype={"student_id": "str", "parent_phone": "str"} in every read_csv - never let pandas infer
- PatternFill(fill_type="solid", fgColor="RRGGBB") - omitting fill_type silently produces no color
- openpyxl color in tests: assert "FFFFCCCC" not "FFCCCC" (8-char hex with alpha prefix)
- HTML: json.dumps(data).replace("</", "<\/") before embedding in script tag
- Use os.environ["KEY"] not os.getenv("KEY") for required secrets - fail at startup
- _build_prompt() must use json.dumps(indent=2) - raw dict/list repr caused 0% LLM success before fix
- LLM prompt must instruct model to return exactly N results, one per student - omitting caused merged/missing results

## GSD Workflow

Planning docs are in .planning/. All 8 phases complete as of 2026-05-25. v1.0 shipped.

- 52/52 requirements delivered, 114+ tests passing, 0 fallbacks on final run (200 students, 5 campuses)
- Progress: /gsd:progress
- All phases: see .planning/ROADMAP.md
