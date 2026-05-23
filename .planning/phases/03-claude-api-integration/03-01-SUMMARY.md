---
phase: 03-claude-api-integration
plan: "01"
subsystem: api
tags: [anthropic, yaml, pyyaml, respx, config, llm]

requires:
  - phase: 02-risk-scoring-engine
    provides: COL_NOTES_COMPONENT and other D-09 component constants in config.py

provides:
  - PyYAML==6.0.3 and respx==0.23.1 pinned in requirements.txt
  - 5 LLM tunable constants in src/config.py (ANTHROPIC_MODEL, LLM_ENABLED, MAX_TOKENS, TEMPERATURE, TIMEOUT_SECONDS)
  - 4 LLM output column constants in src/config.py (COL_FACILITATOR_SUMMARY, COL_WHATSAPP_MESSAGE, COL_GENERATED_BY, COL_LLM_ERROR_REASON)
  - src/llm_templates.yaml with CRITICAL and HIGH fallback templates using >- block scalars
  - STATE.md module contract with tuple[DataFrame, dict] return type locked

affects:
  - 03-02 (llm_engine.py Wave 1 implementation — imports these constants and loads this YAML)
  - 03-03 (main.py wiring — unpacks tuple return from enrich_with_llm)

tech-stack:
  added: [PyYAML==6.0.3, respx==0.23.1]
  patterns:
    - os.getenv with safe defaults for optional LLM tunables (not os.environ — D-08)
    - LLM_ENABLED bool parsed as .lower() == "true" (not bool(os.getenv()) which is always True)
    - YAML >- block scalars to preserve Python {format_placeholders} through yaml.safe_load()
    - Templates loaded at module import via Path(__file__).parent / "llm_templates.yaml"

key-files:
  created: [src/llm_templates.yaml]
  modified: [requirements.txt, src/config.py, .planning/STATE.md]

key-decisions:
  - "os.getenv (not os.environ) for LLM tunables — they are optional with safe defaults, only ANTHROPIC_API_KEY uses fail-loud os.environ (D-08)"
  - "LLM_ENABLED uses .lower() == 'true' — bool(os.getenv('LLM_ENABLED', 'true')) is always True for any non-empty string"
  - "YAML >- block scalars for all template strings — prevents YAML parser misreading {curly_braces} as flow mappings (Pitfall 5)"
  - "tuple[DataFrame, dict] return type (not pd.DataFrame) — consistent with plan contract; STATE.md module contracts use unqualified type names"

patterns-established:
  - "Pattern: LLM bool flag: os.getenv('FLAG', 'default').lower() == 'true'"
  - "Pattern: YAML templates co-located with engine (src/llm_templates.yaml next to src/llm_engine.py)"
  - "Pattern: >- block scalar for any YAML string containing Python format placeholders"

requirements-completed: [LLM-04, LLM-07, LLM-09]

duration: 8min
completed: 2026-05-23
---

# Phase 3 Plan 01: Claude API Prerequisites Summary

**PyYAML 6.0.3 + respx 0.23.1 added, 9 D-09 LLM constants wired into config.py, YAML fallback templates created with block-scalar format placeholders, and tuple return contract locked in STATE.md**

## Performance

- **Duration:** ~8 min
- **Started:** 2026-05-23T11:00:00Z
- **Completed:** 2026-05-23T11:08:00Z
- **Tasks:** 3 / 3
- **Files modified:** 4

## Accomplishments

- Added PyYAML==6.0.3 and respx==0.23.1 to requirements.txt (both were already installed under py -3.12; pip install confirmed)
- Added 9 new constants to src/config.py: 5 LLM tunables and 4 output column names — all verified via import assertion
- Created src/llm_templates.yaml with CRITICAL and HIGH keys, each containing facilitator_summary (7 format fields) and whatsapp_message (under 100 words, no risk scores) — format placeholders survive yaml.safe_load()
- Updated STATE.md enrich_with_llm contract: `tuple[DataFrame, dict]` with explicit dict key types locked
- 53 existing tests remain GREEN — zero regressions from config additions

## Task Commits

1. **Task 1: Add PyYAML and respx to requirements.txt** - `fffeef1` (chore)
2. **Task 2: Add 9 D-09 constants to config.py and create llm_templates.yaml** - `96e3943` (feat)
3. **Task 3: Update STATE.md module contract to tuple return type** - `79fcd47` (docs)

## Files Created/Modified

- `requirements.txt` - Added PyYAML==6.0.3 and respx==0.23.1 (9 lines total)
- `src/config.py` - Added 5 LLM tunables + 4 LLM output column constants after existing blocks
- `src/llm_templates.yaml` - New file: CRITICAL and HIGH fallback templates with >- block scalars
- `.planning/STATE.md` - Updated enrich_with_llm contract line; updated Last updated timestamp

## Decisions Made

- Used `os.getenv` (not `os.environ`) for all 5 LLM tunables — they are optional with safe defaults. Only `ANTHROPIC_API_KEY` uses fail-loud `os.environ` per D-08.
- `LLM_ENABLED` parsed as `.lower() == "true"` to correctly handle `"false"`, `"False"`, and `"0"` — `bool(os.getenv(...))` would be `True` for any non-empty string including `"false"`.
- Used YAML `>-` block scalars for all template strings to prevent the YAML parser from misinterpreting Python `{format_placeholders}` as YAML flow mappings.
- Contract uses `tuple[DataFrame, dict]` (unqualified) rather than `tuple[pd.DataFrame, dict]` — consistent with plan verification script and standard for module contract documentation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] STATE.md contract already had http_client=None and tuple return from Phase 3 planning; updated to match exact plan-specified format string**

- **Found during:** Task 3 (Update STATE.md module contract)
- **Issue:** STATE.md already contained `tuple[pd.DataFrame, dict]` from Phase 3 planning commit. Plan verification script asserts `tuple[DataFrame, dict]` (no `pd.` prefix). Also the dict description format differed from plan spec.
- **Fix:** Updated contract line to use `tuple[DataFrame, dict]` with explicit dict key types as specified in the plan action block.
- **Files modified:** `.planning/STATE.md`
- **Verification:** `py -3.12 -c "... assert 'tuple[DataFrame, dict]' in s ..."` passes
- **Committed in:** `79fcd47` (Task 3 commit)

---

**Total deviations:** 1 auto-fixed (Rule 1 — contract text precision)
**Impact on plan:** Minor text normalization only. No logic or behavioral change. Contract was semantically correct; updated to match exact verification assertion.

## Issues Encountered

- No `.env` file present in working directory — `ANTHROPIC_API_KEY` is required at config import time. Verification commands were run with `ANTHROPIC_API_KEY=test-key` inline env var. This is expected for development environments without a live API key configured.

## User Setup Required

None for this plan — no external services called, no API keys consumed. The `.env` file (with real `ANTHROPIC_API_KEY`) is required for Plans 03-02 and 03-03.

## Threat Surface Scan

No new network endpoints, auth paths, or schema changes introduced. Template YAML uses `yaml.safe_load()` (not `yaml.load()`), preventing code execution from tampered YAML files. No new threat surface beyond what the plan's threat model documents.

## Known Stubs

None — this plan lays prerequisites only (config constants and YAML templates). No data flows to UI. `llm_engine.py` (which uses these constants) is implemented in Plan 03-02.

## Next Phase Readiness

- Plan 03-02 (llm_engine.py implementation) can proceed: all required imports (`cfg.ANTHROPIC_MODEL`, `cfg.LLM_ENABLED`, etc.) and the YAML template file are in place
- Plan 03-03 (main.py wiring) has the tuple return contract locked in STATE.md
- No blockers

## Self-Check

- [x] `requirements.txt` — 9 lines, PyYAML==6.0.3 and respx==0.23.1 present
- [x] `src/config.py` — 9 new constants verified via import assertion
- [x] `src/llm_templates.yaml` — CRITICAL and HIGH keys, format placeholders survive yaml.safe_load()
- [x] `.planning/STATE.md` — `tuple[DataFrame, dict]` and `http_client=None` confirmed present
- [x] 53 tests GREEN

## Self-Check: PASSED

---
*Phase: 03-claude-api-integration*
*Completed: 2026-05-23*
