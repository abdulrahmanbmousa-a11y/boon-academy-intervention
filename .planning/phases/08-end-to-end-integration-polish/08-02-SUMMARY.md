# Plan 08-02 Summary — Live Pipeline Run + Demo Output Commit

**Status:** COMPLETE
**Wave:** 2
**Commits:** 39e936a

## Live Run Stats (from run_log.json)

| Metric | Value |
|--------|-------|
| students_processed | 300 |
| api_calls_made | 14 |
| tokens_used (input) | 18,113 |
| tokens_used (output) | 7,784 |
| errors_encountered | 0 |
| fallbacks_triggered | 30 |

The `data_quality_warnings` and `fallbacks_triggered` counts are expected — they reflect
the intentional synthetic edge cases (missing numerics ~5%, type mismatches ~2%, duplicate IDs ~3%)
and the three-layer fallback working as designed for MEDIUM/LOW students not enriched by LLM.

## Output Files Verified

**outputs/ (5 shared committed + 20 campus files gitignored):**
- ✅ intervention_priority_list.xlsx
- ✅ whatsapp_messages.csv
- ✅ run_log.json
- ✅ facilitator_dashboard.html
- ✅ intervention_report.docx
- ✅ facilitator_dashboard_C01.xlsx … facilitator_dashboard_C20.xlsx (gitignored)

**docs/ (all 8 .docx + analysis.md):**
- ✅ alternatives.docx, analysis.docx, architecture.docx, data_handling.docx
- ✅ engineering_decisions.docx, scalability.docx, security.docx, system_design.docx

**Project root:**
- ✅ analysis.md — updated with live run numbers (300 students, 14 API calls, 25897 tokens, 30 fallbacks)

## .gitignore Changes

Changed `outputs/` to `outputs/*` with negation exceptions for 5 shared demo files.
Campus-specific xlsx files (20 files) remain gitignored.
`docs/` was not in .gitignore — all docs/ files track automatically.

## Acceptance Criteria Results

| Check | Result |
|-------|--------|
| python main.py completes without exception | ✅ |
| run_log.json students_processed > 0 | 300 ✅ |
| run_log.json api_calls_made >= 1 | 14 ✅ |
| All 8 docs/*.docx files present | ✅ |
| analysis.md has real numbers (not "N students") | ✅ |
| .gitignore allows 5 shared output files | ✅ |
| Demo commit pushed to git | ✅ (39e936a) |

## Ready for Wave 3

Wave 3 (08-03) runs automated quality gates and requires a human to open
`outputs/facilitator_dashboard.html` in Chrome for the UI verification.
