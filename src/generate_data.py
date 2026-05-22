"""Generate synthetic CSVs for the boon-academy-intervention demo.

Invoked by `make demo` or `python -m src.generate_data` BEFORE main.py runs.
Deterministic via seed=42 (D-02: numpy.random.default_rng). NOT imported by main.py.

Outputs 3 CSVs to cfg.DATA_DIR (D-01):
  - student_metadata.csv      — 300 students across 20 campuses (+ ~3% dupe rows)
  - student_daily_metrics.csv — ~4200 rows (300 students x 14 days, edge cases injected)
  - facilitator_notes.csv     — notes for ~70% of students, 1-3 notes each

Edge cases injected per D-03:
  - PCT_MISSING_NUMERIC = 5%  — blank session_attended_min or practice_questions cells
  - PCT_DUPLICATE_ID    = 3%  — duplicate student_id rows in metadata (DUPE suffix)
  - PCT_TYPE_MISMATCH   = 2%  — non-numeric string in practice_questions column

Risk-tier distribution per D-04 (baked into cohort-based metric distributions):
  - 15% CRITICAL: near-zero session / practice (Poisson low-lambda)
  - 25% HIGH:     below-average session / practice (Normal low-mean)
  - 40% MEDIUM:   moderate session / practice (Normal mid-mean)
  - 20% LOW:      high session / practice (Normal high-mean)
"""
import os
from datetime import datetime, timedelta

import numpy as np
import pandas as pd

from src import config as cfg

# ---------------------------------------------------------------------------
# Module-level constants (D-01, D-02, D-03)
# ---------------------------------------------------------------------------
SEED: int = 42                   # D-02: reproducibility
N_CAMPUSES: int = 20             # D-01
STUDENTS_PER_CAMPUS: int = 15    # D-01
N_DAYS: int = 14                 # D-01
PCT_MISSING_NUMERIC: float = 0.05  # D-03
PCT_DUPLICATE_ID: float = 0.03     # D-03
PCT_TYPE_MISMATCH: float = 0.02    # D-03

BASE_DATE: datetime = datetime(2026, 5, 1)

# Canned note texts for realistic facilitator notes
_NOTE_TEXTS: list[str] = [
    "Missed class",
    "Strong performance this week",
    "Parent meeting scheduled",
    "Disengaged in group work",
    "Submitted late assignment",
    "Showed improvement in recent sessions",
    "Needs additional support",
    "Completed all assignments on time",
]


# ---------------------------------------------------------------------------
# Helper: risk cohort assignment (D-04)
# ---------------------------------------------------------------------------

def _assign_risk_cohort(student_idx: int, total: int) -> str:
    """Return the risk cohort label for a student given their index.

    Uses deterministic index-bucket assignment to guarantee cohort counts
    match D-04 percentages (15% CRITICAL / 25% HIGH / 40% MEDIUM / 20% LOW)
    on every run regardless of RNG state.

    Args:
        student_idx: Zero-based index of the student (0 .. total-1).
        total: Total number of base students (300).

    Returns:
        One of "CRITICAL", "HIGH", "MEDIUM", "LOW".
    """
    critical_end = int(total * 0.15)          # 0 ..  44 (45 students)
    high_end = critical_end + int(total * 0.25)  # 45 .. 119 (75 students)
    medium_end = high_end + int(total * 0.40)    # 120 .. 239 (120 students)

    if student_idx < critical_end:
        return "CRITICAL"
    elif student_idx < high_end:
        return "HIGH"
    elif student_idx < medium_end:
        return "MEDIUM"
    else:
        return "LOW"


# ---------------------------------------------------------------------------
# Generator functions
# ---------------------------------------------------------------------------

def generate_metadata(rng: np.random.Generator) -> pd.DataFrame:
    """Build the base student metadata DataFrame (300 rows, 20 campuses x 15 students).

    Each student gets a deterministic campus/student ID, a synthetic phone
    number starting with '0501' (Pitfall #3 — preserves leading zero), and a
    predictable facilitator email.

    Args:
        rng: Seeded numpy random generator (D-02).

    Returns:
        DataFrame with columns matching cfg column constants:
        COL_STUDENT_ID, COL_STUDENT_NAME, COL_CAMPUS_ID,
        COL_PARENT_PHONE, COL_FACILITATOR_EMAIL.
    """
    rows: list[dict] = []
    for c in range(1, N_CAMPUSES + 1):
        campus_id = f"C{c:02d}"
        for s in range(1, STUDENTS_PER_CAMPUS + 1):
            student_id = f"S{c:02d}{s:02d}"
            rows.append(
                {
                    cfg.COL_STUDENT_ID: student_id,
                    cfg.COL_STUDENT_NAME: f"Student {student_id}",
                    cfg.COL_CAMPUS_ID: campus_id,
                    cfg.COL_PARENT_PHONE: f"0501{rng.integers(100000, 999999):06d}",
                    cfg.COL_FACILITATOR_EMAIL: f"facilitator.{campus_id.lower()}@boon.academy",
                }
            )
    return pd.DataFrame(rows)


def generate_metrics(
    rng: np.random.Generator,
    students: list[tuple[str, str]],
) -> pd.DataFrame:
    """Build the daily metrics DataFrame (~4200 rows: 300 students x 14 days).

    Each student's metrics are drawn from distributions calibrated to their
    D-04 risk cohort:
      - CRITICAL: Poisson(2) session_min, Poisson(1) practice_q
      - HIGH:     Normal(15, 5) session_min, Poisson(3) practice_q
      - MEDIUM:   Normal(35, 8) session_min, Poisson(8) practice_q
      - LOW:      Normal(50, 5) session_min, Poisson(15) practice_q

    All values are clipped to [0, 90] for session_min and [0, inf) for
    practice_q, then rounded to the nearest integer.

    Args:
        rng: Seeded numpy random generator (D-02).
        students: List of (student_id, cohort) tuples.

    Returns:
        DataFrame with columns: COL_STUDENT_ID, COL_METRIC_DATE,
        COL_SESSION_MIN, COL_PRACTICE_Q.
    """
    rows: list[dict] = []
    for student_id, cohort in students:
        for day in range(N_DAYS):
            date_str = (BASE_DATE + timedelta(days=day)).strftime("%Y-%m-%d")

            if cohort == "CRITICAL":
                session_min = int(np.clip(rng.poisson(2), 0, 90))
                practice_q = int(rng.poisson(1))
            elif cohort == "HIGH":
                session_min = int(np.clip(round(rng.normal(15, 5)), 0, 90))
                practice_q = int(max(0, rng.poisson(3)))
            elif cohort == "MEDIUM":
                session_min = int(np.clip(round(rng.normal(35, 8)), 0, 90))
                practice_q = int(max(0, rng.poisson(8)))
            else:  # LOW
                session_min = int(np.clip(round(rng.normal(50, 5)), 0, 90))
                practice_q = int(max(0, rng.poisson(15)))

            rows.append(
                {
                    cfg.COL_STUDENT_ID: student_id,
                    cfg.COL_METRIC_DATE: date_str,
                    cfg.COL_SESSION_MIN: session_min,
                    cfg.COL_PRACTICE_Q: practice_q,
                }
            )
    return pd.DataFrame(rows)


def generate_notes(
    rng: np.random.Generator,
    students: list[tuple[str, str]],
) -> pd.DataFrame:
    """Build the facilitator notes DataFrame.

    Approximately 70% of students receive 1-3 notes each; the remaining 30%
    have no notes at all (exercises the 'max days_since_last_note' penalty
    path in Phase 2 risk scoring).

    Note dates are drawn uniformly from the 14-day BASE_DATE window. Note
    texts are sampled from a small canned list of realistic strings.

    Args:
        rng: Seeded numpy random generator (D-02).
        students: List of (student_id, cohort) tuples.

    Returns:
        DataFrame with columns: COL_STUDENT_ID, COL_NOTE_DATE, COL_NOTE_TEXT.
    """
    rows: list[dict] = []
    for student_id, _cohort in students:
        # 70% of students have notes
        if rng.random() < 0.70:
            n_notes = int(rng.integers(1, 4))  # 1, 2, or 3 notes
            for _ in range(n_notes):
                day_offset = int(rng.integers(0, N_DAYS))
                note_date = (BASE_DATE + timedelta(days=day_offset)).strftime(
                    "%Y-%m-%d"
                )
                note_text = _NOTE_TEXTS[int(rng.integers(0, len(_NOTE_TEXTS)))]
                rows.append(
                    {
                        cfg.COL_STUDENT_ID: student_id,
                        cfg.COL_NOTE_DATE: note_date,
                        cfg.COL_NOTE_TEXT: note_text,
                    }
                )
    return pd.DataFrame(rows)


def inject_edge_cases(
    metadata: pd.DataFrame,
    metrics: pd.DataFrame,
    rng: np.random.Generator,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Inject D-03 edge cases into metadata and metrics DataFrames.

    Three injection types per D-03:
      1. Duplicate IDs (PCT_DUPLICATE_ID = 3%): Append copies of randomly
         selected metadata rows with a " DUPE" suffix on student_name.
      2. Missing numeric (PCT_MISSING_NUMERIC = 5%): Set randomly selected
         cells in session_attended_min or practice_questions to pd.NA.
      3. Type mismatches (PCT_TYPE_MISMATCH = 2%): Set randomly selected
         practice_questions cells to a non-numeric string ("abc", "many", "?").

    All selections use the seeded rng for full D-02 reproducibility.

    Args:
        metadata: Base student metadata DataFrame (300 rows).
        metrics: Base daily metrics DataFrame (~4200 rows).
        rng: Seeded numpy random generator (D-02).

    Returns:
        Tuple (metadata_with_dupes, metrics_with_edge_cases).
    """
    # --- 1. Duplicate IDs in metadata ---
    n_dupes = max(1, int(PCT_DUPLICATE_ID * len(metadata)))
    dupe_indices = rng.choice(len(metadata), size=n_dupes, replace=False)
    dupe_rows = metadata.iloc[dupe_indices].copy()
    dupe_rows[cfg.COL_STUDENT_NAME] = dupe_rows[cfg.COL_STUDENT_NAME] + " DUPE"
    metadata = pd.concat([metadata, dupe_rows], ignore_index=True)

    # --- 2. Missing numeric in metrics ---
    n_missing = max(1, int(PCT_MISSING_NUMERIC * len(metrics)))
    # Convert numeric columns to object dtype to allow pd.NA insertion
    metrics = metrics.copy()
    metrics[cfg.COL_SESSION_MIN] = metrics[cfg.COL_SESSION_MIN].astype(object)
    metrics[cfg.COL_PRACTICE_Q] = metrics[cfg.COL_PRACTICE_Q].astype(object)
    missing_indices = rng.choice(len(metrics), size=n_missing, replace=False)
    for idx in missing_indices:
        # Randomly blank session_min or practice_q
        col = cfg.COL_SESSION_MIN if rng.random() < 0.5 else cfg.COL_PRACTICE_Q
        metrics.at[idx, col] = pd.NA

    # --- 3. Type mismatches in metrics ---
    n_mismatch = max(1, int(PCT_TYPE_MISMATCH * len(metrics)))
    mismatch_strings = ["abc", "many", "?"]
    mismatch_indices = rng.choice(len(metrics), size=n_mismatch, replace=False)
    for i, idx in enumerate(mismatch_indices):
        metrics.at[idx, cfg.COL_PRACTICE_Q] = mismatch_strings[
            i % len(mismatch_strings)
        ]

    return metadata, metrics


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Generate 3 deterministic synthetic CSVs and write them to cfg.DATA_DIR.

    Execution order:
      1. Create DATA_DIR if absent.
      2. Seed the RNG (D-02: np.random.default_rng(SEED)).
      3. Generate metadata (300 rows) and assign D-04 risk cohorts.
      4. Generate metrics (~4200 rows).
      5. Generate notes (~70% of students).
      6. Inject D-03 edge cases into metadata and metrics.
      7. Write 3 CSVs (index=False, UTF-8).
      8. Print a single summary line (permitted exception to CLAUDE.md
         'zero print' rule — this is a developer utility, not the pipeline).
    """
    cfg.DATA_DIR.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(SEED)

    # Build metadata + cohort assignments
    metadata = generate_metadata(rng)
    total = len(metadata)
    students: list[tuple[str, str]] = [
        (row[cfg.COL_STUDENT_ID], _assign_risk_cohort(i, total))
        for i, row in metadata.iterrows()
    ]

    # Generate metrics and notes
    metrics = generate_metrics(rng, students)
    notes = generate_notes(rng, students)

    # Inject edge cases (D-03)
    metadata, metrics = inject_edge_cases(metadata, metrics, rng)

    # Write CSVs
    metadata.to_csv(
        cfg.DATA_DIR / "student_metadata.csv", index=False, encoding="utf-8"
    )
    metrics.to_csv(
        cfg.DATA_DIR / "student_daily_metrics.csv", index=False, encoding="utf-8"
    )
    notes.to_csv(
        cfg.DATA_DIR / "facilitator_notes.csv", index=False, encoding="utf-8"
    )

    # Single summary print — permitted for utility scripts (01-RESEARCH.md L611)
    print(
        f"Generated synthetic data: {len(metadata)} students, "
        f"{len(metrics)} metric rows, {len(notes)} notes in {cfg.DATA_DIR}"
    )


if __name__ == "__main__":
    main()
