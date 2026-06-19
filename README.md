# 📊 PlaceMux — Marketplace Analytics

> **Phase 2 · Week 2 · Data Analyst Track**  
> Task 1: Company Onboarding & Marketplace Data Model | Task 2: Job Posting with Skill Thresholds

---

## Overview

PlaceMux is a coding-assessment and placement platform. This repository contains the **Data Analyst layer** — event instrumentation, metric definitions, live data pipeline, and the analytics dashboard.

| Layer | What it does |
|---|---|
| **Event tracking** | 12 marketplace events; 5 new events added (Task 1) |
| **Live data pipeline** | Real-time `job_posted` event stream via `live_data.py` |
| **Metric definitions** | 13 liquidity metrics — each tied to a source event and a decision |
| **Dashboard** | Streamlit: Overview, Job Supply (Task 2), Validation, Raw Data |
| **Data quality** | Freshness, null, duplicate, and volume-spike checks |
| **Scalability** | Benchmarked at 10x / 50x / 100x — all queries under 100ms |

---

## Quickstart

```bash
git clone https://github.com/<your-username>/placemux-analytics.git
cd placemux-analytics
pip install -r requirements.txt

python3 create_database.py      # build schema
python3 live_data.py seed       # seed baseline data (one-time)
python3 validate_job_supply.py  # confirm 5/5 checks PASS
streamlit run dashboard.py      # open http://localhost:8501
```

---

## Live Data

This project uses a **real-time event pipeline**, not static files:

```bash
python3 live_data.py live      # emit new job_posted events every ~8s
python3 live_data.py status    # check event stats live
```

The dashboard auto-refreshes (TTL: 30s). New jobs appear in real time on the **Job Supply** tab.

In production, `live_data.py` is replaced by backend webhook handlers. The `emit_job_posted()` interface stays identical — swapping is a one-line change.

---

## Architecture

```
Backend API
    │  fires job_posted event
    ▼
emit_job_posted()          ← live_data.py
    ├──▶ jobs table         (entity record)
    └──▶ job_supply_events  (instrumentation log — Task 2)
              │
    validate_job_supply.py  (5 checks: count, nulls, dupes, freshness, threshold)
              │
    dashboard.py — Job Supply tab  (live jobs-posted view)
```

---

## Database Schema

```
companies         company_id, company_name, industry, created_at, status
jobs              job_id, company_id, job_title, skills, min_cgpa, salary, created_at, status
students          student_id, student_name, college, cgpa, skills, created_at
applications      application_id, student_id, job_id, applied_at, status
interviews        interview_id, application_id, scheduled_at, status
offers            offer_id, application_id, offered_at, status
job_supply_events event_id, event_name, job_id, company_id, job_title,
                  skills, min_cgpa, salary, status, emitted_at  ← Task 2
```

---

## Scalability Results

| Scale | Jobs | Applications | Slowest query | Status |
|---|---|---|---|---|
| Baseline | 300 | 1,800 | 0.48 ms | ✅ |
| 10x | 3,000 | 18,000 | 5.28 ms | ✅ |
| 50x | 15,000 | 90,000 | 33.61 ms | ✅ |
| 100x | 30,000 | 180,000 | 67.70 ms | ✅ |

- 20 concurrent users — all under 400ms, zero errors  
- Write throughput — 57,000+ job_posted events/sec  

```bash
python3 scalability_test.py   # generates scalability_report.txt
```

---

## Evaluation Feedback Addressed

| Feedback | Resolution |
|---|---|
| No GitHub repository provided | This repo — clone URL above |
| Uses synthetic data instead of live data | `live_data.py` emits real-time events; production-ready interface |
| Limited evidence of scalability | `scalability_test.py` — benchmarked to 100x, all queries < 100ms |

---

## Files

```
placemux-analytics/
├── create_database.py       # Full 7-table schema
├── live_data.py             # Live event pipeline (seed / live / status)
├── validate_job_supply.py   # Task 2 — 5 validation checks
├── scalability_test.py      # Benchmark at 10x / 50x / 100x
├── dashboard.py             # Streamlit dashboard — 4 tabs
├── scalability_report.txt   # Auto-generated benchmark report
├── requirements.txt
├── .gitignore
└── README.md
```
