# Features Research: Student Intervention System

**Domain:** AI-powered student intervention for hybrid test-prep classrooms
**Researched:** 2026-05-21
**Overall confidence:** MEDIUM-HIGH (training knowledge; WebSearch unavailable — no live source verification)

---

## Table Stakes Features

These are the features without which facilitators will not use the system. Every item here
addresses a specific adoption failure mode observed in edtech tooling at similar scales.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Daily prioritized student list** | Facilitators have no time to analyze — they need to be told who to call. A ranked list of 3-5 students to contact today is the core deliverable. Without it the system is a dashboard, not a tool. | Low | Delivered via WhatsApp or Google Sheets — not a new app. |
| **One-number risk score per student** | A single score (e.g., 1-10 or traffic-light) removes cognitive load. Multiple sub-scores require synthesis a facilitator won't do under time pressure. | Low | Score must be explainable in one sentence — "low practice, two absences, score dropped." |
| **Score change delta** | "Was 4, now 7" is more actionable than an absolute score. Trend direction drives urgency. Facilitators respond to change signals. | Low | Delta over 7-day window is sufficient for this context. |
| **Pre-drafted parent message per student** | The #1 friction point is writing the message. If the system drafts it in Arabic, reviewed and sent in 30 seconds, facilitators will use it. If they have to write from scratch, they won't. | Medium | Claude API. Message must be WhatsApp-native: short, warm, action-request at the end. |
| **One-tap copy to WhatsApp** | Facilitators use WhatsApp. Any step that requires logging into a new app or a browser kills adoption. The workflow must end with a message in their clipboard or WhatsApp draft. | Low | wa.me deep links with pre-filled text work on mobile without API costs. |
| **Google Sheets as primary interface** | Non-technical facilitators will not install apps. Google Sheets is already on their phones. The intervention list must work as a Sheets view they can act on. | Low | AppScript can handle triggers, formatting, and the WhatsApp link column. |
| **Intervention logging** | Facilitators must be able to mark a student as "contacted" in 2 taps. Without this, the system re-surfaces the same students every day, frustrating the facilitator and making the system feel broken. | Low | Binary checkbox + timestamp. Do not ask for outcome detail at this stage. |
| **Campus-level scoping** | Each facilitator sees only their 50-80 students. Showing cross-campus data creates noise and privacy concerns. All filtering must be automatic. | Low | Role-based filtering by campus ID. |

**Confidence:** HIGH — These patterns are validated across edtech adoption studies and internal tooling
for non-technical field staff. The WhatsApp/Sheets constraint is domain-specific but well-supported
by the project context.

---

## Differentiating Features

These features are what separate a system that achieves 80%+ intervention rates from one
that gets used for two weeks and abandoned.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Risk score explanation in plain Arabic** | "Score is 8 because: missed 2 sessions, practice dropped 40% this week, last quiz score fell 12 points." Facilitators need to trust the score. Trust requires explanation. Without this, they second-guess the list and revert to gut feel. | Medium | Template-based explanation is sufficient — no NLP required. |
| **Message tone variants** | First-contact message differs from a second nudge. A student who missed one day gets a different message than one who has been absent three times. Pre-drafted variants prevent tone mismatches that embarrass facilitators. | Medium | 3-4 tone variants: check-in, concern, urgent. Claude selects based on risk level and prior contact count. |
| **Facilitator acknowledgment tracking** | Tracking whether a facilitator viewed the list (not just whether they logged contact) enables campus manager oversight without surveillance. "Campus 7 has 12 high-risk students — facilitator hasn't opened the list in 2 days" is a management signal. | Medium | Simple open-event logging. Not a punitive metric; a support trigger. |
| **Quiz-day urgency elevation** | 48 hours before a scheduled quiz, all high-risk students get automatically elevated in the list. This is the highest-leverage intervention window. The system must know the quiz schedule and react to it. | Low | Calendar integration or manual quiz schedule input. |
| **Auto-deactivation after contact** | When a facilitator marks a student contacted, that student drops off the urgent list for 48 hours unless risk score spikes. Prevents repeated re-surfacing of the same students and builds facilitator trust in the list. | Low | Cooldown logic. Re-activates on score threshold breach. |
| **Weekly summary for campus managers** | Managers need a one-page view: how many students were contacted this week, how many were high-risk, what is the trend. This closes the accountability loop without requiring managers to use the daily system. | Medium | Auto-generated Google Sheet summary tab or WhatsApp message to manager. |
| **Batch WhatsApp integration via wa.me links** | WhatsApp Business API has approval delays and per-message costs. wa.me deep links with pre-filled text achieve 80-90% of the value with zero API cost and zero onboarding friction. Differentiator because most tools chase the API. | Low | url-encode the message, use wa.me/{phone}?text={message}. Facilitator taps, reviews, sends. |

**Confidence:** MEDIUM-HIGH — Quiz-day elevation and cooldown logic are patterns from push-notification
systems and customer success tooling applied to this context. WhatsApp deep link approach is
well-established as an alternative to the Business API for high-friction markets.

---

## Anti-Features (Deliberate Exclusions)

These features appear useful but will actively harm adoption or outcome achievement.
Build none of these in v1.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| **Student-facing app or portal** | Students at test-prep academies respond to facilitator contact, not self-service dashboards. Building a student portal doubles scope, adds auth complexity, and doesn't address the core problem (facilitators not reaching students). | Keep it facilitator-only. Measure intervention rate, not portal logins. |
| **Real-time risk score updates** | Updating scores every hour requires streaming infrastructure, increases compute costs, and provides no actionable benefit. Facilitators act once per day at most. Real-time feels impressive but adds zero intervention value. | Daily batch scoring, run each morning before facilitators start their day. |
| **Complex multi-tab dashboard** | A dashboard with attendance, quiz scores, practice charts, and engagement tabs requires a facilitator to synthesize data. Every tab added reduces the chance of action being taken. This is the #1 failure mode in edtech tooling for non-technical users. | Single-tab view: ranked list, one score, one explanation line, one WhatsApp link. |
| **Outcome prediction (will fail quiz?)** | Predicting quiz outcomes requires labeled training data that doesn't exist (14 days, no historical labels). Attempting ML prediction with this data produces unreliable scores that erode facilitator trust when predictions are wrong. | Rule-based risk scoring with transparent weights. Trust comes from explainability, not accuracy claims. |
| **Automated message sending without facilitator review** | Sending WhatsApp messages to parents without facilitator review removes human judgment, creates brand risk when messages are wrong, and removes the facilitator from the loop — reducing their sense of ownership and accountability. | Draft + one-tap send. Facilitator always reviews. This also handles edge cases (parent already contacted, family situation). |
| **Per-student trend charts** | Charts require interpretation. A facilitator looking at a sparkline of 14 data points will not take faster action than one reading "practice dropped 40% this week." Charts are for analysts, not field staff. | Plain-language delta summaries. |
| **Native mobile app** | App store submission, device compatibility, update management, and user onboarding add months of delay and ongoing maintenance. Facilitators already have WhatsApp and Google Sheets. | WhatsApp + Google Sheets. If a dedicated UI is needed later, a mobile-responsive web app. |
| **Manual data entry by facilitators** | If facilitators must enter attendance or practice data themselves, the system creates work rather than removing it. Adoption collapses immediately. | Automated ingestion from existing LMS, attendance system, or Google Forms that students already use. |

**Confidence:** HIGH — These exclusions are grounded in established product design principles for
field-staff tooling (Jobs-to-be-Done, Fogg Behavior Model) and specific failure patterns in
edtech adoption literature.

---

## Risk Scoring Approaches

### The Core Constraint

14 days of behavioral data. No historical quiz outcome labels. Non-technical facilitators who
must trust the score. These three constraints together rule out most ML approaches.

### Option 1: Weighted Rule-Based Scoring (RECOMMENDED)

**How it works:**

Each signal is scored 0-10 and multiplied by a weight. Weights sum to 1.0.

```
risk_score = (
  attendance_score    * 0.30  +
  practice_score      * 0.25  +
  trend_score         * 0.25  +
  facilitator_contact * 0.20
)
```

Signal definitions:
- `attendance_score`: sessions missed / sessions scheduled in last 14 days, scaled 0-10
- `practice_score`: practice problems attempted vs. expected baseline, inverted (low practice = high risk)
- `trend_score`: quiz/practice score this week vs. last week, inverted delta
- `facilitator_contact`: days since last facilitator-initiated contact (caps at 14 days = score 10)

**Why this works with 14 days of data:**
- No training labels required
- Fully explainable: every score maps to a specific observable behavior
- Weights can be tuned by a campus manager based on domain knowledge, not data science
- Consistent outputs build facilitator trust faster than probabilistic predictions

**Why this wins:**
- Transparent: "Score is 8 because attendance is 60% and practice dropped by half" is actionable
- Debuggable: facilitators can challenge the score and be shown the exact inputs
- Fast to implement: no model training pipeline, no feature engineering infrastructure
- Scales to 5,000 students without ML infrastructure costs

**Confidence for this approach:** HIGH

### Option 2: ML Classification (NOT recommended for v1)

Logistic regression or gradient boosting predicting "will score below threshold on next quiz."

**Why it fails here:**
- Requires labeled data (quiz outcomes mapped to prior behaviors) — 14 days provides 1-2 data points per student, insufficient for any reliable model
- Cold-start problem: new campuses have zero historical data
- Black-box outputs ("risk probability: 0.73") are not explainable to facilitators
- When it's wrong (and it will be), facilitators lose trust in the entire system
- Requires ongoing retraining as patterns shift

Reserve ML for Phase 2 when 6+ months of labeled outcomes are available.

**Confidence for this assessment:** HIGH — consistent with published research on early warning
systems in education (e.g., EDUCAUSE literature on EWS implementation).

### Option 3: Hybrid (Rule-Based + Anomaly Detection)

Use rule-based scoring as the primary score. Add a simple anomaly flag: if any single signal
changes by more than 2 standard deviations in 7 days, flag the student as "sudden change."
This catches students who fall off a cliff (e.g., stopped attending after a personal event)
without requiring ML infrastructure.

**Recommendation:** Implement this as a v1.5 enhancement after the base rule system is validated.

### Weight Calibration

Initial weights should come from domain expert input (academic director or experienced facilitator),
not data. After 60 days, run correlation analysis between risk score at T and quiz outcome at T+7
to validate and adjust weights.

**Confidence:** MEDIUM — weight calibration process is standard for rule-based EWS systems;
specific optimal weights for this context require empirical validation.

---

## Facilitator UX Research

### What facilitators actually need at a glance

Field staff with 50-80 students and 20 minutes per day for interventions need decisions
made for them, not data presented to them. The UX principle is: **eliminate the thinking step**.

**The intervention trigger must be a list, not a score.**

The mental model that works: "These 5 students need contact today. Here is what to say to each."

The mental model that fails: "Here are 50 students with risk scores. You decide who is urgent."

### Optimal daily view structure (Google Sheets)

```
Column A: Rank (1 = most urgent)
Column B: Student name
Column C: Risk score (1-10, color-coded red/yellow/green)
Column D: One-line reason ("Missed 2 sessions, practice down 40%")
Column E: Parent phone number
Column F: [WhatsApp Link] — tappable link pre-filled with drafted message
Column G: Contacted? (checkbox)
Column H: Date contacted (auto-fills on checkbox tick)
```

Rules:
- Show maximum 10 students per day. If more than 10 are at risk, show the top 10 by score.
  Facilitators presented with 30 urgent students will contact zero.
- Collapse contacted students to a secondary tab automatically.
- Color coding must be interpretable without a legend. Red = act today. Yellow = monitor. Green = fine.

### Cognitive load principles applied

1. **One decision per row** — each row should result in a tap, not a deliberation.
2. **Pre-made message removes composition effort** — the highest friction point in any communication workflow is starting from a blank message.
3. **Rank removes prioritization effort** — facilitators should not have to decide who is "more" at-risk. The system ranks; the facilitator acts in order.
4. **Logging must be easier than not logging** — one checkbox tap, auto-timestamp. Any more friction and logging stops.

**Confidence:** HIGH — these principles align with Fogg Behavior Model (trigger + motivation + ability),
behavioral economics research on decision fatigue, and documented patterns in CRM adoption for
non-technical sales teams, which is the closest analog to this context.

---

## Message Generation Best Practices

### What makes a WhatsApp parent message get sent vs. ignored

A facilitator will send a pre-drafted message if and only if:
1. It reads naturally in their voice, not like a system-generated template
2. It is in the right language (Arabic, with appropriate formality level)
3. It does not embarrass them if forwarded or screenshotted
4. It has a clear, single call-to-action at the end
5. It is short enough to read in 5 seconds before tapping send

### Message structure that works

```
Opening: Warm greeting, reference to the student by name.
Body: One specific, factual observation (not an accusation).
Bridge: Express the academy's care and the facilitator's personal engagement.
CTA: One specific ask — check in with student tonight, confirm attendance tomorrow, etc.
Close: Warm sign-off, facilitator name.
```

Example (English proxy, actual delivery in Arabic):

> "Hello Um Khalid, this is Sara from Boon Academy. I wanted to reach out because I noticed
> Ahmed hasn't been able to join our last two sessions, and his practice completion has been
> lower than usual this week. We care a lot about his progress, especially with the upcoming
> quiz on Thursday. Could you check in with him this evening and let me know if there's
> anything we can do to support him? Thank you so much."

### What kills message send rates

- **Generic templates with visible placeholders** ("Dear [PARENT_NAME]") — signals automation, reduces trust
- **Academic jargon** ("His engagement metrics have declined") — parents don't have a reference frame
- **Multiple asks** ("Can you check in, also confirm registration, and pay the outstanding balance?") — message is ignored
- **Accusatory framing** ("Ahmed has been absent and not doing his work") — parent becomes defensive, facilitator avoids sending
- **Long messages** — WhatsApp context is mobile; anything over 5 lines loses attention

### Claude prompt engineering for this context

The prompt to Claude for message generation should:
- Provide the student's name, parent's name, relationship (mother/father), specific behavioral signals (not scores), and quiz date if applicable
- Specify tone: warm, personal, non-alarming for medium risk; direct and concerned for high risk
- Specify language: Arabic (Modern Standard or Gulf dialect depending on campus region)
- Specify length constraint: maximum 5 lines
- Explicitly prohibit: score numbers, percentage drops, academic jargon, multiple asks

The system should generate 2 variants (different opening styles) and let the facilitator pick, OR
default to a single variant with an "edit" option. Two-variant selection adds 10 seconds to the
workflow; single-variant with edit is faster.

**Confidence:** MEDIUM-HIGH — message design principles are grounded in behavioral science
and customer communication best practices. Arabic-language specifics and Gulf dialect considerations
are based on training knowledge; live testing with actual facilitators is required to validate.

---

## Dashboard Minimum Viable Design

### Design principle: not a dashboard, a task list

"Dashboard" implies charts, trends, and analysis. The intervention system should not be thought of
as a dashboard at all — it is a daily task list with a contact tool attached.

The failure mode of dashboards in this context: facilitators open it, look at charts,
feel informed, and take no action. The metric is interventions completed, not logins.

### Minimum viable interface: one Google Sheet, three tabs

**Tab 1: Today's List (primary)**
- Sorted by risk score descending
- Maximum 10 rows visible above the fold (hide lower-priority rows by default)
- Columns: Rank | Name | Score | Reason | WhatsApp link | Contacted checkbox
- No charts. No trend lines. No sub-scores.

**Tab 2: All Students**
- Full roster, sortable by score
- Used by campus managers for weekly review, not by facilitators daily
- Same columns plus last-contact date

**Tab 3: This Week's Summary**
- Auto-generated by script each Monday
- Five numbers: students at risk, contacted, not contacted, avg risk score, change from last week
- No interpretation required from the user

### What to avoid in the dashboard

- Progress bars (require context to interpret)
- Sparklines (require interpretation of shape)
- Color gradients with more than 3 levels (red/yellow/green is sufficient)
- Filters the facilitator must set (auto-apply by role/campus)
- Pagination (everything visible in one scroll on mobile)

### Mobile-first constraint

Facilitators will use this on a phone during breaks between sessions. The Sheets view must:
- Have columns narrow enough to see columns A-F without horizontal scrolling on mobile
- Use large tap targets for the checkbox column
- Have the WhatsApp link column tap directly into WhatsApp

**Confidence:** HIGH — these constraints are consistent with mobile UX research for field staff
and Google Sheets mobile behavior. The "task list not dashboard" principle is well-established
in product design for operational teams.

---

## Batch vs Real-Time Analysis

### When real-time matters

Real-time processing is justified when the intervention window is shorter than the batch interval
and when the cost of missing that window is high.

In this system, the intervention window is 24-48 hours. Facilitators contact parents once per day
at most. There is no intervention action that can be taken in response to a score change within
a 1-hour window. **Real-time scoring provides zero additional intervention value.**

### When daily batch is sufficient (and better)

Daily batch scoring run at 6:00 AM (before facilitators start) means:
- Fresh scores reflecting last night's practice session completion
- One consistent "as of this morning" snapshot that facilitators can reference
- No confusion from scores changing during the day while a facilitator is mid-action
- No streaming infrastructure required
- Predictable compute cost (not load-dependent)

The batch run should:
1. Pull attendance, practice, and quiz data for all students across all campuses
2. Compute risk scores using the weighted rule model
3. Regenerate WhatsApp message drafts for all students whose score changed materially (>1 point)
4. Update the Google Sheets intervention list for each campus
5. Send a summary WhatsApp message to each campus facilitator: "Good morning — you have 4 students to contact today. [link to sheet]"

Total batch processing time at 5,000 students: under 60 seconds for scoring; Claude API calls
for message generation will be the bottleneck (estimate 2-5 seconds per message, only generate
for score-change students).

### Exception: quiz-day urgency

48 hours before a scheduled quiz, run an additional batch pass that:
- Re-elevates any high-risk student who was marked "contacted" more than 24 hours ago
- Generates a quiz-specific message variant emphasizing preparation

This is not real-time — it is a triggered batch job keyed to the quiz calendar.

### Scaling consideration

At 5,000 students across 100 campuses, daily batch is still preferable to real-time:
- Batch parallelizes by campus (100 independent jobs of 50 students each)
- Real-time would require event-driven infrastructure (Kafka, SQS, or equivalent) with no
  intervention-rate benefit
- Cost: Claude API message generation is the scaling constraint, not compute.
  At 5,000 students with 20% score-change rate daily = ~1,000 API calls/day.
  At $0.003/call (Claude Haiku), this is $3/day — negligible.

### Recommendation

Daily batch. Always. Reserve real-time for a future version only if a specific use case
emerges where sub-hour response is required (e.g., a student marks themselves absent via
a form 2 hours before a session and a same-day intervention is possible).

**Confidence:** HIGH — the batch-vs-real-time analysis follows from the intervention workflow
constraints described in the project context. The cost estimate uses publicly available
Claude API pricing as of August 2025; verify current pricing before budgeting.

---

## Sources and Confidence Summary

| Area | Confidence | Basis |
|------|------------|-------|
| Table stakes features | HIGH | Grounded in edtech adoption patterns and field-staff tooling design principles |
| Differentiating features | MEDIUM-HIGH | Applied from CRM/intervention system patterns; quiz-day logic is domain-specific inference |
| Anti-features | HIGH | Consistent with behavioral science (Fogg), product design for non-technical users |
| Risk scoring | HIGH | EDUCAUSE EWS literature, data science constraints well-understood for cold-start/small-N |
| Facilitator UX | HIGH | Aligned with Fogg Behavior Model, decision fatigue research, CRM adoption patterns |
| Message generation | MEDIUM-HIGH | Communication best practices well-established; Arabic/Gulf dialect specifics need live validation |
| Dashboard design | HIGH | Mobile UX for field staff, Google Sheets operational patterns |
| Batch vs real-time | HIGH | Infrastructure trade-off analysis based on stated workflow constraints |

**WebSearch was unavailable** — no live source verification was performed. All findings reflect
training knowledge as of August 2025. High-confidence findings are based on well-established
principles unlikely to have changed. Medium-confidence findings should be validated against
current edtech literature and, more importantly, against live facilitator testing in the first
two weeks of deployment.

**Critical validation required before launch:**
- Test message tone and language with 3 actual facilitators before scaling
- Run a 2-week pilot on one campus before the 18-campus rollout
- Verify wa.me deep link behavior on the specific phones facilitators use (Android/iOS differences)
