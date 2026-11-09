# PulseIQ demo & interview walkthrough (WS-15)

**Synthetic CRM — not real customers.**

---

## A. Three-minute recruiter walkthrough

PulseIQ is a **portfolio product-analytics platform** for a fictional B2B CRM. I built a **reproducible DuckDB pipeline** (Bronze/Silver/Gold), fixed **event chronology** so metrics are trustworthy, and defined **contracts** for engagement, adoption, retention, and activation.

**Problem:** Product teams need to know whether new accounts truly *activate*, which features matter, and whether users return — without mixing broken timestamps or full-history denominators into an “as-of” board meeting.

**Solution:** Qualified event facts, separate **FULL_DATASET** vs **AS_OF 2026-07-11** contexts, and Gold tables exported for Power BI.

**Headline findings (as-of, mature cohort):** Strong **feature and deal reach**, but **0 / 15** FR10 eligible activation; account exact-day retention **0%**; user D7 ~**3.6%**. Full-history activation is **21/120 (17.5%)** — a different question.

**Recommendations:** P0 **activation milestone guide**; P1 **rolling retention** measurement before nudges.

**Demonstrates:** Analytics engineering + product thinking + honest limitations on synthetic, small-n data.

---

## B. Five-minute technical walkthrough

1. **Ingestion:** Snapshots → Bronze scripts (`sql/bronze/`).
2. **Silver:** Standardised keys, statuses, geography fixture.
3. **Gold dimensions:** Accounts, users, geography.
4. **Event identity:** Attribution populations; quarantine pre-creation anomalies.
5. **Qualified facts:** `gold_fact_qualified_product_events` for official analytics.
6. **Metric models:** Engagement periodic, feature adoption/breadth, retention cohorts, FR10 activation (full + as-of), descriptive funnel, segment rollups.
7. **Orchestration:** `run_pipeline.py` → disposable DB → CSV export + manifest.
8. **Power BI:** Folder parameter, star relationships where grain allows; DAX mostly reads Gold aggregates; context slicers mandatory.

---

## C. Product interview questions

### 1. What problem does PulseIQ solve?
It shows how to produce **trustworthy product KPIs** from event data: chronology-safe facts, explicit reporting context, and metric definitions that product can act on.

### 2. Why these KPIs?
They map to standard SaaS product loops: **activation** (FR10), **engagement** (DAU/WAU/MAU), **adoption/breadth**, **retention**, **funnel reach**, **segments**.

### 3. User vs account activation?
FR10 is **account-level** (deal + core signals in 14 days). User metrics describe participation, not the same activation contract.

### 4. Why 17.5% full-dataset but 0% as-of?
**17.5%** uses all **120** accounts over the full timeline. **As-of** asks which accounts were **eligible and window-complete** by 2026-07-11 (**15**); **none** met FR10 by that date. Different denominators and questions.

### 5. Invalid event chronology?
Pre-creation and mis-ordered events are labelled; **official** metrics use **qualified** events only (see `docs/chronology_integrity_audit.md`).

### 6. D7/D14 retention?
**Exact calendar-day** return on day 7 or 14 after cohort anchor — **not** rolling 7-day windows. Show eligible and retained counts.

### 7. Why descriptive funnel?
Event order in raw data does not prove sequential onboarding; stages report **reach** among eligible accounts, not conversion rates.

### 8. Top priority?
**OPP-01 activation guide** — data shows usage without as-of FR10 success; aligns to existing events.

### 9. Test the activation guide?
Randomise **new accounts**, treatment vs control, primary metric **IsActivatedAsOf** at day 14; needs larger **n** than current synthetic slice.

### 10. Build next on a real SaaS?
Instrument assignment + checklist impressions, add **rolling retention** Gold metric, scale segment samples, connect CRM actions to experiment platform.

---

**Power BI:** Build report locally per [`powerbi_setup.md`](powerbi_setup.md). No pre-validated `.pbix` ships with the repo.
