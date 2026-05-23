---
phase: 2
slug: risk-scoring-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-05-23
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (already installed — see requirements.txt) |
| **Config file** | `pytest.ini` or `pyproject.toml [tool.pytest]` |
| **Quick run command** | `pytest tests/test_risk_engine.py -x -q` |
| **Full suite command** | `pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `pytest tests/test_risk_engine.py -x -q`
- **After every plan wave:** Run `pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 2-01-01 | 01 | 0 | RISK-08 | — | N/A | unit | `pytest tests/test_config.py -q` | ❌ W0 | ⬜ pending |
| 2-01-02 | 01 | 1 | RISK-01 | — | N/A | unit | `pytest tests/test_risk_engine.py::test_score_risk_returns_required_columns -q` | ❌ W0 | ⬜ pending |
| 2-01-03 | 01 | 1 | RISK-02 | — | N/A | unit | `pytest tests/test_risk_engine.py::test_attendance_component -q` | ❌ W0 | ⬜ pending |
| 2-01-04 | 01 | 1 | RISK-03 | — | N/A | unit | `pytest tests/test_risk_engine.py::test_practice_component -q` | ❌ W0 | ⬜ pending |
| 2-01-05 | 01 | 1 | RISK-04 | — | N/A | unit | `pytest tests/test_risk_engine.py::test_trend_component -q` | ❌ W0 | ⬜ pending |
| 2-01-06 | 01 | 1 | RISK-05 | — | N/A | unit | `pytest tests/test_risk_engine.py::test_notes_component -q` | ❌ W0 | ⬜ pending |
| 2-01-07 | 01 | 1 | RISK-06 | — | N/A | unit | `pytest tests/test_risk_engine.py::test_risk_level_thresholds -q` | ❌ W0 | ⬜ pending |
| 2-01-08 | 01 | 1 | RISK-07 | — | N/A | unit | `pytest tests/test_risk_engine.py::test_worst_student_is_critical -q` | ❌ W0 | ⬜ pending |
| 2-01-09 | 01 | 1 | RISK-07 | — | N/A | unit | `pytest tests/test_risk_engine.py::test_perfect_student_is_low -q` | ❌ W0 | ⬜ pending |
| 2-01-10 | 01 | 2 | RISK-01 | — | N/A | unit | `pytest tests/ -q` | — | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_risk_engine.py` — NEW file with stubs for RISK-01 through RISK-08 (14-row test matrix, boundary parametrize, worst/perfect student, purity assertions)
- [ ] `src/config.py` — add 4 missing COL_*_COMPONENT constants (COL_ATTENDANCE_COMPONENT, COL_PRACTICE_COMPONENT, COL_TREND_COMPONENT, COL_NOTES_COMPONENT)
- [ ] `tests/test_config.py` — extend to assert 4 new constants exist and are non-empty strings

*Existing conftest.py covers ANTHROPIC_API_KEY mocking — no new fixture file needed.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| score_risk() produces no I/O side effects | RISK-01 | Purity is structural — assert no file writes, no network calls, no print statements in risk_engine.py | Code review: grep risk_engine.py for `print\|open\|request\|logging.` — only logging.getLogger allowed |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
