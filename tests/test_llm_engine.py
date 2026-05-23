"""Tests for src/llm_engine.py — covers LLM-01 through LLM-09.

Each test maps to one or more LLM-* requirements from REQUIREMENTS.md.
All tests use respx-mocked Anthropic client injected via http_client= parameter.
No real API calls are made.
"""
import logging
import re
from pathlib import Path

import httpx
import pandas as pd
import pytest

from src import config as cfg
from src.llm_engine import enrich_with_llm

# ---------------------------------------------------------------------------
# Module-level constant
# ---------------------------------------------------------------------------

ANTHROPIC_API_URL = "https://api.anthropic.com/v1/messages"


# ---------------------------------------------------------------------------
# Helper: build a single-student row dict (not a fixture — plain function)
# ---------------------------------------------------------------------------

def _build_student_row(
    student_id: str = "S0001",
    campus_id: str = "C01",
    risk_level: str = "CRITICAL",
    risk_score: float = 85.0,
    attendance_rate: float = 0.3,
    avg_practice_questions: float = 2.0,
    trend_direction: str = "declining",
    days_since_last_note: float = 20.0,
    recommended_action: str = "Contact parent immediately",
) -> dict:
    """Build a minimal student row dict for pd.DataFrame([_build_student_row(...)]).

    Includes all columns output by score_risk() that enrich_with_llm() consumes.
    Uses cfg.COL_* for all dict keys — no bare column-name strings.
    student_name and parent_phone are present in the DataFrame but must NOT reach
    the API prompt or any log output (LLM-08).
    """
    return {
        cfg.COL_STUDENT_ID: student_id,
        cfg.COL_STUDENT_NAME: "Test Student",
        cfg.COL_CAMPUS_ID: campus_id,
        cfg.COL_PARENT_PHONE: "0501234567",
        cfg.COL_FACILITATOR_EMAIL: "f@test.com",
        cfg.COL_RISK_LEVEL: risk_level,
        cfg.COL_RISK_SCORE: risk_score,
        cfg.COL_ATTENDANCE_RATE: attendance_rate,
        cfg.COL_AVG_PRACTICE: avg_practice_questions,
        cfg.COL_TREND_DIR: trend_direction,
        cfg.COL_DAYS_SINCE_NOTE: days_since_last_note,
        cfg.COL_RECOMMENDED_ACTION: recommended_action,
        # component columns (present from score_risk output)
        cfg.COL_ATTENDANCE_COMPONENT: 25.0,
        cfg.COL_PRACTICE_COMPONENT: 15.0,
        cfg.COL_TREND_COMPONENT: 10.0,
        cfg.COL_NOTES_COMPONENT: 5.0,
    }


# ---------------------------------------------------------------------------
# Helper: build a fake Anthropic API tool-use response dict
# ---------------------------------------------------------------------------

def _make_tool_response(students: list[dict]) -> dict:
    """Build the raw JSON body the Anthropic API returns for a tool-use call.

    Args:
        students: List of per-student result dicts (student_id, facilitator_summary,
            whatsapp_message).

    Returns:
        Full response dict matching the Anthropic messages API JSON shape.
    """
    return {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": cfg.ANTHROPIC_MODEL,
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "usage": {"input_tokens": 150, "output_tokens": 80},
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_test",
                "name": "generate_interventions",
                "input": {"students": students},
            }
        ],
    }


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_medium_low_students_skipped(respx_mock) -> None:
    """LLM-01: MEDIUM and LOW students receive None in all 4 LLM output columns.

    No API call should be made when the cohort contains only MEDIUM and LOW students.
    """
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", risk_level="MEDIUM"),
        _build_student_row(student_id="S0002", risk_level="LOW"),
    ])
    http_client = httpx.Client(transport=httpx.MockTransport(respx_mock.handler))
    result_df, counts = enrich_with_llm(df, "test-key", http_client=http_client)

    assert counts["api_calls_made"] == 0, (
        "LLM-01: MEDIUM/LOW students must produce zero API calls"
    )
    assert result_df[cfg.COL_GENERATED_BY].isna().all(), (
        "LLM-01: MEDIUM/LOW rows must have None/NaN in generated_by (D-07)"
    )
    assert result_df[cfg.COL_FACILITATOR_SUMMARY].isna().all(), (
        "LLM-01: MEDIUM/LOW rows must have None/NaN in facilitator_summary (D-07)"
    )
    assert result_df[cfg.COL_WHATSAPP_MESSAGE].isna().all(), (
        "LLM-01: MEDIUM/LOW rows must have None/NaN in whatsapp_message (D-07)"
    )
    assert len(respx_mock.calls) == 0, (
        "LLM-01: no HTTP calls should be made for a MEDIUM/LOW-only cohort"
    )


def test_campus_batching(respx_mock) -> None:
    """LLM-02: Two campuses produce exactly two API calls — one per campus.

    Campus C01 has one CRITICAL student; campus C02 has one HIGH student.
    Each campus must trigger a separate API call.
    """
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", campus_id="C01", risk_level="CRITICAL"),
        _build_student_row(student_id="S0002", campus_id="C02", risk_level="HIGH"),
    ])

    respx_mock.post(ANTHROPIC_API_URL).mock(
        side_effect=[
            httpx.Response(
                200,
                json=_make_tool_response([
                    {
                        cfg.COL_STUDENT_ID: "S0001",
                        cfg.COL_FACILITATOR_SUMMARY: "Summary for S0001. Action needed.",
                        cfg.COL_WHATSAPP_MESSAGE: "Dear parent of S0001.",
                    }
                ]),
            ),
            httpx.Response(
                200,
                json=_make_tool_response([
                    {
                        cfg.COL_STUDENT_ID: "S0002",
                        cfg.COL_FACILITATOR_SUMMARY: "Summary for S0002. Follow up.",
                        cfg.COL_WHATSAPP_MESSAGE: "Dear parent of S0002.",
                    }
                ]),
            ),
        ]
    )

    http_client = httpx.Client(transport=httpx.MockTransport(respx_mock.handler))
    _, counts = enrich_with_llm(df, "test-key", http_client=http_client)

    assert len(respx_mock.calls) == 2, (
        f"LLM-02: expected exactly 2 API calls (one per campus), got {len(respx_mock.calls)}"
    )
    assert counts["api_calls_made"] == 2, (
        "LLM-02: api_calls_made counter must reflect both campus calls"
    )


def test_tool_use_structured_output(respx_mock) -> None:
    """LLM-03: Successful tool-use call populates generated_by='llm' with non-empty text.

    A CRITICAL student whose campus call succeeds must have generated_by='llm',
    a non-empty facilitator_summary, and a non-empty whatsapp_message.
    """
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", campus_id="C01", risk_level="CRITICAL"),
    ])

    respx_mock.post(ANTHROPIC_API_URL).mock(
        return_value=httpx.Response(
            200,
            json=_make_tool_response([
                {
                    cfg.COL_STUDENT_ID: "S0001",
                    cfg.COL_FACILITATOR_SUMMARY: "Test summary sentence one. Test summary sentence two.",
                    cfg.COL_WHATSAPP_MESSAGE: "Test message for parent.",
                }
            ]),
        )
    )

    http_client = httpx.Client(transport=httpx.MockTransport(respx_mock.handler))
    result_df, _ = enrich_with_llm(df, "test-key", http_client=http_client)

    row = result_df[result_df[cfg.COL_STUDENT_ID] == "S0001"].iloc[0]
    assert row[cfg.COL_GENERATED_BY] == "llm", (
        "LLM-03: successful LLM call must set generated_by='llm'"
    )
    assert row[cfg.COL_FACILITATOR_SUMMARY] and len(str(row[cfg.COL_FACILITATOR_SUMMARY])) > 0, (
        "LLM-03: facilitator_summary must be non-empty after successful LLM call"
    )
    assert row[cfg.COL_WHATSAPP_MESSAGE] and len(str(row[cfg.COL_WHATSAPP_MESSAGE])) > 0, (
        "LLM-03: whatsapp_message must be non-empty after successful LLM call"
    )


def test_max_retries_config(monkeypatch) -> None:
    """LLM-04: Production Anthropic client is created with max_retries=3.

    When enrich_with_llm is called without an http_client (production path),
    the Anthropic constructor must receive max_retries=3.
    """
    captured_kwargs: dict = {}

    class _FakeClient:
        """Fake Anthropic client that captures constructor kwargs and skips API calls."""

        def __init__(self, **kwargs):
            captured_kwargs.update(kwargs)

        class messages:
            @staticmethod
            def create(**_kwargs):
                # Return a minimal response that simulates empty campus (no CRITICAL/HIGH)
                raise RuntimeError("should not be called in this test")

    import anthropic as _anthropic_module

    monkeypatch.setattr(_anthropic_module, "Anthropic", _FakeClient)

    # Use a df with only MEDIUM students so the client is constructed but no call is made
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", risk_level="MEDIUM"),
    ])

    # http_client=None triggers the production branch
    enrich_with_llm(df, "test-key", http_client=None)

    assert captured_kwargs.get("max_retries") == 3, (
        f"LLM-04: production Anthropic client must have max_retries=3, "
        f"got max_retries={captured_kwargs.get('max_retries')}"
    )


def test_fallback_to_template(respx_mock) -> None:
    """LLM-05: API timeout causes fallback to template; generated_by='template'.

    When every API call raises httpx.TimeoutException the function must:
    - Not raise any exception itself
    - Set generated_by='template' for the affected student
    - Set a non-None llm_error_reason
    """
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", campus_id="C01", risk_level="CRITICAL"),
    ])

    respx_mock.post(ANTHROPIC_API_URL).mock(
        side_effect=httpx.TimeoutException("timed out")
    )

    http_client = httpx.Client(transport=httpx.MockTransport(respx_mock.handler))
    result_df, counts = enrich_with_llm(df, "test-key", http_client=http_client)

    row = result_df[result_df[cfg.COL_STUDENT_ID] == "S0001"].iloc[0]
    assert row[cfg.COL_GENERATED_BY] == "template", (
        "LLM-05: timeout must produce generated_by='template'"
    )
    assert row[cfg.COL_LLM_ERROR_REASON] == "timeout", (
        "LLM-05: httpx.TimeoutException must classify to llm_error_reason='timeout'"
    )
    assert counts["fallbacks_triggered"] >= 1, (
        "LLM-05: fallbacks_triggered counter must be incremented on template fallback"
    )


def test_token_logging(respx_mock) -> None:
    """LLM-06: Successful API call accumulates token counts in the returned counts dict.

    Mock returns input_tokens=150, output_tokens=80.
    The returned counts dict must reflect these values.
    """
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", campus_id="C01", risk_level="CRITICAL"),
    ])

    respx_mock.post(ANTHROPIC_API_URL).mock(
        return_value=httpx.Response(
            200,
            json=_make_tool_response([
                {
                    cfg.COL_STUDENT_ID: "S0001",
                    cfg.COL_FACILITATOR_SUMMARY: "Token test summary. Second sentence here.",
                    cfg.COL_WHATSAPP_MESSAGE: "Token test parent message.",
                }
            ]),
        )
    )

    http_client = httpx.Client(transport=httpx.MockTransport(respx_mock.handler))
    _, counts = enrich_with_llm(df, "test-key", http_client=http_client)

    assert counts["tokens_used"]["input"] == 150, (
        f"LLM-06: input tokens must be 150, got {counts['tokens_used']['input']}"
    )
    assert counts["tokens_used"]["output"] == 80, (
        f"LLM-06: output tokens must be 80, got {counts['tokens_used']['output']}"
    )


def test_api_key_not_in_logs(respx_mock, caplog) -> None:
    """LLM-07: The API key value must never appear in any log record.

    Calls enrich_with_llm with a distinctive api_key value and verifies that
    string does not appear in any log record at DEBUG level or above.
    """
    secret_key = "SUPERSECRETKEY123"
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", campus_id="C01", risk_level="CRITICAL"),
    ])

    respx_mock.post(ANTHROPIC_API_URL).mock(
        side_effect=httpx.TimeoutException("timeout for key test")
    )

    http_client = httpx.Client(transport=httpx.MockTransport(respx_mock.handler))

    with caplog.at_level(logging.DEBUG, logger="src.llm_engine"):
        enrich_with_llm(df, secret_key, http_client=http_client)

    assert secret_key not in caplog.text, (
        f"LLM-07: API key '{secret_key}' must not appear in any log record"
    )


def test_pii_not_in_logs(monkeypatch, caplog) -> None:
    """LLM-08: student_name and parent_phone must never appear in log records.

    Uses LLM_ENABLED=False path to exercise all logging without respx complexity.
    Verifies that neither the student name nor phone appear at DEBUG level or above.
    """
    sensitive_name = "Sensitive Student"
    sensitive_phone = "0509991111"

    row = _build_student_row(student_id="S0001", campus_id="C01", risk_level="CRITICAL")
    row[cfg.COL_STUDENT_NAME] = sensitive_name
    row[cfg.COL_PARENT_PHONE] = sensitive_phone
    df = pd.DataFrame([row])

    monkeypatch.setattr(cfg, "LLM_ENABLED", False)

    with caplog.at_level(logging.DEBUG, logger="src.llm_engine"):
        enrich_with_llm(df, "test-key", http_client=None)

    assert sensitive_name not in caplog.text, (
        f"LLM-08: PII leak — student_name '{sensitive_name}' found in log output"
    )
    assert sensitive_phone not in caplog.text, (
        f"LLM-08: PII leak — parent_phone '{sensitive_phone}' found in log output"
    )


def test_chunk_size_limit(respx_mock) -> None:
    """LLM-09: 15 CRITICAL students on one campus produce exactly 2 API calls (10+5).

    MAX_STUDENTS_PER_LLM_CALL defaults to 10. 15 students must be split into
    a first chunk of 10 and a second chunk of 5, each triggering one API call.
    """
    rows = [
        _build_student_row(
            student_id=f"S{i:04d}",
            campus_id="C01",
            risk_level="CRITICAL",
            risk_score=float(90 - i),
        )
        for i in range(15)
    ]
    df = pd.DataFrame(rows)

    def _make_response_for_call(request, *args, **kwargs):
        """Return a valid tool response for however many students are in this chunk."""
        import json as _json
        body = _json.loads(request.content)
        # Extract student_ids from the prompt — just return one result per student in chunk
        # We look at how many students were sent by counting ids in the prompt text
        content_text = str(body.get("messages", [{}])[0].get("content", ""))
        # Count student ids by scanning for S0 pattern
        import re as _re
        student_ids_in_chunk = _re.findall(r"S\d{4}", content_text)
        # Deduplicate while preserving order
        seen = set()
        unique_ids = []
        for sid in student_ids_in_chunk:
            if sid not in seen:
                seen.add(sid)
                unique_ids.append(sid)
        student_results = [
            {
                cfg.COL_STUDENT_ID: sid,
                cfg.COL_FACILITATOR_SUMMARY: f"Summary for {sid}. Action needed.",
                cfg.COL_WHATSAPP_MESSAGE: f"Parent message for {sid}.",
            }
            for sid in unique_ids
        ]
        return httpx.Response(200, json=_make_tool_response(student_results))

    respx_mock.post(ANTHROPIC_API_URL).mock(side_effect=_make_response_for_call)

    http_client = httpx.Client(transport=httpx.MockTransport(respx_mock.handler))
    _, counts = enrich_with_llm(df, "test-key", http_client=http_client)

    assert len(respx_mock.calls) == 2, (
        f"LLM-09: 15 students with chunk_size=10 must produce 2 API calls, "
        f"got {len(respx_mock.calls)}"
    )
    assert counts["api_calls_made"] == 2, (
        "LLM-09: api_calls_made must be 2 for 15-student single-campus cohort"
    )


def test_llm_disabled_uses_templates(monkeypatch) -> None:
    """D-09/LLM-05: When LLM_ENABLED=False, all CRITICAL/HIGH students get template output.

    Zero API calls must be made. Both CRITICAL and HIGH students must have
    generated_by='template' and llm_error_reason='llm_disabled'.
    """
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", campus_id="C01", risk_level="CRITICAL"),
        _build_student_row(student_id="S0002", campus_id="C01", risk_level="HIGH"),
    ])

    monkeypatch.setattr(cfg, "LLM_ENABLED", False)

    result_df, counts = enrich_with_llm(df, "test-key", http_client=None)

    assert counts["api_calls_made"] == 0, (
        "D-09: LLM_ENABLED=False must make zero API calls"
    )
    for student_id in ["S0001", "S0002"]:
        row = result_df[result_df[cfg.COL_STUDENT_ID] == student_id].iloc[0]
        assert row[cfg.COL_GENERATED_BY] == "template", (
            f"D-09: student {student_id} must have generated_by='template' when LLM disabled"
        )
        assert row[cfg.COL_LLM_ERROR_REASON] == "llm_disabled", (
            f"D-09: student {student_id} must have llm_error_reason='llm_disabled'"
        )


def test_malformed_tool_response(respx_mock) -> None:
    """LLM-05: Malformed tool response (missing 'students' key) causes template fallback.

    When the API returns HTTP 200 but the tool input dict has the wrong key,
    generated_by must be 'template', llm_error_reason must be 'malformed_response',
    and fallbacks_triggered must be 1.
    """
    df = pd.DataFrame([
        _build_student_row(student_id="S0001", campus_id="C01", risk_level="CRITICAL"),
    ])

    malformed_response = {
        "id": "msg_test",
        "type": "message",
        "role": "assistant",
        "model": cfg.ANTHROPIC_MODEL,
        "stop_reason": "tool_use",
        "stop_sequence": None,
        "usage": {"input_tokens": 10, "output_tokens": 5},
        "content": [
            {
                "type": "tool_use",
                "id": "toolu_bad",
                "name": "generate_interventions",
                "input": {"wrong_key": []},
            }
        ],
    }

    respx_mock.post(ANTHROPIC_API_URL).mock(
        return_value=httpx.Response(200, json=malformed_response)
    )

    http_client = httpx.Client(transport=httpx.MockTransport(respx_mock.handler))
    result_df, counts = enrich_with_llm(df, "test-key", http_client=http_client)

    row = result_df[result_df[cfg.COL_STUDENT_ID] == "S0001"].iloc[0]
    assert row[cfg.COL_GENERATED_BY] == "template", (
        "LLM-05: malformed tool response must trigger template fallback (generated_by='template')"
    )
    assert row[cfg.COL_LLM_ERROR_REASON] == "malformed_response", (
        f"LLM-05: llm_error_reason must be 'malformed_response', "
        f"got {row[cfg.COL_LLM_ERROR_REASON]!r}"
    )
    assert counts["fallbacks_triggered"] == 1, (
        f"LLM-05: fallbacks_triggered must be 1, got {counts['fallbacks_triggered']}"
    )


def test_no_bare_column_strings_in_llm_engine() -> None:
    """LLM-08/CLAUDE.md: No bare DataFrame column-name strings in src/llm_engine.py.

    Reads llm_engine.py, strips docstrings and comments, then scans for quoted
    lowercase strings (4+ chars). Asserts none of the known DataFrame column name
    values appear as bare string literals. Non-column-name strings (JSON Schema
    vocabulary, Anthropic API message keys, error reason values, tool name) are
    permitted via the allowed set.

    This enforces CLAUDE.md: 'All column names as constants in src/config.py —
    no hardcoded strings in logic.'
    """
    source_path = Path(__file__).parent.parent / "src" / "llm_engine.py"
    source = source_path.read_text(encoding="utf-8")

    # Strip triple-quoted docstrings (covers both """ styles)
    no_docstrings = re.sub(r'""".*?"""', "", source, flags=re.DOTALL)
    # Strip inline and full-line comments
    no_comments = re.sub(r"#.*", "", no_docstrings)

    # Extract all "quoted" lowercase strings with 4+ chars
    matches = re.findall(r'"([a-z][a-z0-9_]{3,})"', no_comments)
    found = set(matches)

    # Allowed set: error reason values, tool/schema structure, Anthropic API keys,
    # return dict keys, and other non-column structural strings.
    # DataFrame column name values (e.g. "student_id", "risk_level") are NOT allowed.
    allowed: set[str] = {
        # Error reason strings (D-08 values)
        "llm",
        "template",
        "llm_disabled",
        "timeout",
        "rate_limit",
        "malformed_response",
        "max_retries_exceeded",
        # Tool schema structural keys (unavoidable JSON Schema vocabulary)
        "students",
        "tool",
        "name",
        "type",
        "object",
        "array",
        "string",
        "description",
        "required",
        "properties",
        "items",
        "input_schema",
        # Anthropic API message structure keys (unavoidable SDK vocabulary)
        "role",
        "user",
        "content",
        "input",
        "output",
        # Tool name (not a column name)
        "generate_interventions",
        # Return dict keys (not column names — they are counts dict keys)
        "api_calls_made",
        "tokens_used",
        "fallbacks_triggered",
        # Encoding string fragment
        "utf",
        # numpy scalar method name used in CR-01 fix (hasattr(v, "item"))
        "item",
    }

    # The actual column name values from config.py that must NOT appear as bare strings
    known_column_values: set[str] = {
        "student_id", "student_name", "campus_id", "parent_phone", "facilitator_email",
        "metric_date", "session_attended_min", "practice_questions", "note_date", "note_text",
        "attendance_rate", "avg_practice_questions", "trend_direction", "days_since_last_note",
        "risk_score", "risk_level", "recommended_action",
        "attendance_component", "practice_component", "trend_component", "notes_component",
        "facilitator_summary", "whatsapp_message", "generated_by", "llm_error_reason",
    }

    # Any found string that is a known column value is an offender
    column_offenders = found & known_column_values
    assert not column_offenders, (
        f"Bare DataFrame column-name strings found in src/llm_engine.py: "
        f"{sorted(column_offenders)}. Use cfg.COL_* constants instead."
    )

    # Any found string not in the allowed set is unexpected (may be a new column name leak)
    unexpected = found - allowed - known_column_values
    assert not unexpected, (
        f"Unexpected bare lowercase strings in src/llm_engine.py: {sorted(unexpected)}. "
        f"If these are not column names, add them to the allowed set in this test. "
        f"If they are column names, replace with cfg.COL_* constants."
    )
