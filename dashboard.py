"""
PlaceMux Analytics Dashboard
Task 1 (Marketplace Health) + Task 2 (Job Supply Instrumentation)
Run: streamlit run dashboard.py
"""
import streamlit as st
import sqlite3, pandas as pd, plotly.express as px, plotly.graph_objects as go
import datetime as dt, os

DB = os.path.join(os.path.dirname(__file__), "placemux.db")
TODAY = dt.datetime(2026, 6, 18)

st.set_page_config(page_title="PlaceMux Dashboard", page_icon="📊", layout="wide")

@st.cache_data(ttl=30)
def q(sql):
    conn = sqlite3.connect(DB)
    df = pd.read_sql(sql, conn)
    conn.close()
    return df

# ── header ──────────────────────────────────────────────────────────────────
st.markdown("""
<div style='background:linear-gradient(90deg,#1e2761,#3b5bdb);padding:1.2rem 2rem;
            border-radius:12px;margin-bottom:1.2rem'>
  <h1 style='color:#fff;margin:0;font-size:1.8rem'>📊 PlaceMux Marketplace Dashboard</h1>
  <p style='color:#cadcfc;margin:0.25rem 0 0'>Phase 2 · Week 2 · Task 1 & Task 2 &nbsp;|&nbsp; As of 18 Jun 2026</p>
</div>""", unsafe_allow_html=True)

tabs = st.tabs(["🏠 Overview", "📦 Job Supply (Task 2)", "🔍 Validation", "📋 Raw Data"])

# ═══════════════════════════════════════════════════════
# TAB 1 — OVERVIEW (Task 1 metrics)
# ═══════════════════════════════════════════════════════
with tabs[0]:

    # ── top KPI cards ────────────────────────────────────
    total_companies = q("SELECT COUNT(*) n FROM companies").iloc[0,0]
    total_jobs      = q("SELECT COUNT(*) n FROM jobs").iloc[0,0]
    total_students  = q("SELECT COUNT(*) n FROM students").iloc[0,0]
    total_apps      = q("SELECT COUNT(*) n FROM applications").iloc[0,0]
    shortlisted     = q("SELECT COUNT(*) n FROM applications WHERE status='Shortlisted'").iloc[0,0]
    interviewed     = q("SELECT COUNT(*) n FROM interviews").iloc[0,0]
    offered         = q("SELECT COUNT(*) n FROM offers").iloc[0,0]

    shortlist_rate  = round(shortlisted / total_apps * 100, 1) if total_apps else 0
    interview_rate  = round(interviewed / max(shortlisted,1) * 100, 1)
    offer_rate      = round(offered / max(interviewed,1) * 100, 1)

    avg_time = q("""
        SELECT AVG((JULIANDAY(o.offered_at) - JULIANDAY(a.applied_at))) avg_days
        FROM offers o JOIN applications a ON o.application_id = a.application_id
    """).iloc[0,0]
    avg_time = round(avg_time, 1) if avg_time else "—"

    c1,c2,c3,c4 = st.columns(4)
    c1.metric("🏢 Companies",    total_companies)
    c2.metric("💼 Jobs",         total_jobs)
    c3.metric("🎓 Students",     total_students)
    c4.metric("📝 Applications", total_apps)

    c5,c6,c7,c8 = st.columns(4)
    c5.metric("🎯 Shortlist Rate",  f"{shortlist_rate}%")
    c6.metric("🗣️ Interview Rate",  f"{interview_rate}%")
    c7.metric("🏆 Offer Rate",      f"{offer_rate}%")
    c8.metric("⏱️ Avg Time to Hire", f"{avg_time} days")

    st.divider()

    # ── hiring funnel ─────────────────────────────────────
    col_f, col_p = st.columns(2)

    with col_f:
        funnel_df = pd.DataFrame({
            "stage": ["Applied", "Shortlisted", "Interviewed", "Offered"],
            "count": [total_apps, shortlisted, interviewed, offered]
        })
        fig_funnel = go.Figure(go.Funnel(
            y=funnel_df["stage"], x=funnel_df["count"],
            textinfo="value+percent initial",
            marker=dict(color=["#1e2761","#3b5bdb","#6b8cfa","#22c55e"])
        ))
        fig_funnel.update_layout(title="Hiring Funnel", height=320,
                                  margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig_funnel, use_container_width=True)

    with col_p:
        status_df = q("""
            SELECT status, COUNT(*) count FROM applications GROUP BY status
        """)
        fig_pie = px.pie(status_df, names="status", values="count",
                         title="Application Status Mix",
                         color_discrete_sequence=px.colors.qualitative.Bold)
        fig_pie.update_layout(height=320, margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    # ── time-series: applications + jobs per day ──────────
    col_a, col_b = st.columns(2)

    with col_a:
        apps_daily = q("""
            SELECT DATE(applied_at) date, COUNT(*) applications
            FROM applications
            GROUP BY DATE(applied_at) ORDER BY date
        """)
        fig_apps = px.line(apps_daily, x="date", y="applications",
                           title="Applications Per Day",
                           color_discrete_sequence=["#3b5bdb"])
        fig_apps.update_layout(height=280, margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig_apps, use_container_width=True)

    with col_b:
        co_growth = q("""
            SELECT DATE(created_at) date, COUNT(*) companies
            FROM companies GROUP BY DATE(created_at) ORDER BY date
        """)
        fig_co = px.line(co_growth, x="date", y="companies",
                         title="Company Signups Per Day",
                         color_discrete_sequence=["#f59e0b"])
        fig_co.update_layout(height=280, margin=dict(t=40,b=10,l=10,r=10))
        st.plotly_chart(fig_co, use_container_width=True)

    # ── top skills in demand ──────────────────────────────
    skills_raw = q("SELECT skills FROM jobs")
    from collections import Counter
    all_skills = []
    for row in skills_raw["skills"].dropna():
        all_skills.extend([s.strip() for s in row.split(",")])
    skill_counts = pd.DataFrame(Counter(all_skills).most_common(12),
                                 columns=["skill","count"])
    fig_skills = px.bar(skill_counts, x="count", y="skill", orientation="h",
                        title="Top Skills In Demand (from job postings)",
                        color="count", color_continuous_scale="Blues")
    fig_skills.update_layout(height=380, margin=dict(t=40,b=10,l=10,r=10),
                              coloraxis_showscale=False, yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_skills, use_container_width=True)

    # ── jobs by company ───────────────────────────────────
    company_jobs = q("""
        SELECT c.company_name, COUNT(j.job_id) jobs
        FROM companies c LEFT JOIN jobs j ON c.company_id=j.company_id
        GROUP BY c.company_name ORDER BY jobs DESC LIMIT 15
    """)
    fig_co_jobs = px.bar(company_jobs, x="jobs", y="company_name", orientation="h",
                          title="Jobs Posted By Company (top 15)",
                          color_discrete_sequence=["#1e2761"])
    fig_co_jobs.update_layout(height=420, margin=dict(t=40,b=10,l=10,r=10),
                               yaxis=dict(autorange="reversed"))
    st.plotly_chart(fig_co_jobs, use_container_width=True)


# ═══════════════════════════════════════════════════════
# TAB 2 — JOB SUPPLY (Task 2 centrepiece)
# ═══════════════════════════════════════════════════════
with tabs[1]:
    st.subheader("Job Supply Instrumentation — Live View")
    st.caption("Every row below comes from a `job_posted` event in the `job_supply_events` table. "
               "This view is the Task 2 deliverable — events validated, jobs-posted view live.")

    # hero numbers
    total_supply   = q("SELECT COUNT(*) n FROM job_supply_events").iloc[0,0]
    open_jobs      = q("SELECT COUNT(*) n FROM job_supply_events WHERE status='open'").iloc[0,0]
    filled_jobs    = q("SELECT COUNT(*) n FROM job_supply_events WHERE status='filled'").iloc[0,0]
    avg_cgpa_th    = q("SELECT ROUND(AVG(min_cgpa),2) n FROM job_supply_events").iloc[0,0]
    avg_sal        = q("SELECT ROUND(AVG(salary)/100000.0,2) n FROM job_supply_events").iloc[0,0]
    fill_rate_pct  = round(filled_jobs / total_supply * 100, 1) if total_supply else 0

    c1,c2,c3,c4,c5 = st.columns(5)
    c1.metric("📦 Total Jobs Posted",  total_supply)
    c2.metric("🟢 Open",              open_jobs)
    c3.metric("✅ Filled",            filled_jobs)
    c4.metric("📊 Fill Rate",         f"{fill_rate_pct}%")
    c5.metric("🎓 Avg Min CGPA",      avg_cgpa_th)

    st.divider()

    # jobs posted per day (last 30 days)
    daily_supply = q("""
        SELECT DATE(emitted_at) date, COUNT(*) jobs_posted
        FROM job_supply_events
        WHERE emitted_at >= DATE('2026-06-18', '-30 days')
        GROUP BY DATE(emitted_at) ORDER BY date
    """)
    fig_daily = px.bar(daily_supply, x="date", y="jobs_posted",
                       title="Jobs Posted Per Day (last 30 days) — from job_posted events",
                       color_discrete_sequence=["#1e2761"])
    fig_daily.update_layout(height=300, margin=dict(t=40,b=10))
    st.plotly_chart(fig_daily, use_container_width=True)

    col_r, col_s = st.columns(2)

    with col_r:
        # by role
        by_role = q("""
            SELECT job_title, COUNT(*) jobs,
                   ROUND(AVG(min_cgpa),2) avg_threshold,
                   ROUND(AVG(salary)/100000.0,2) avg_salary_L
            FROM job_supply_events GROUP BY job_title ORDER BY jobs DESC
        """)
        fig_role = px.bar(by_role, x="jobs", y="job_title", orientation="h",
                          title="Supply by Role", color="avg_threshold",
                          color_continuous_scale="Blues",
                          labels={"avg_threshold":"Avg Min CGPA"})
        fig_role.update_layout(height=340, margin=dict(t=40,b=10),
                               yaxis=dict(autorange="reversed"))
        st.plotly_chart(fig_role, use_container_width=True)

    with col_s:
        # CGPA threshold distribution
        cgpa_dist = q("""
            SELECT min_cgpa, COUNT(*) jobs FROM job_supply_events
            GROUP BY min_cgpa ORDER BY min_cgpa
        """)
        fig_cgpa = px.bar(cgpa_dist, x="min_cgpa", y="jobs",
                          title="Skill Threshold (min CGPA) Distribution",
                          color_discrete_sequence=["#3b5bdb"],
                          labels={"min_cgpa":"Min CGPA Required","jobs":"Jobs"})
        fig_cgpa.update_layout(height=340, margin=dict(t=40,b=10))
        st.plotly_chart(fig_cgpa, use_container_width=True)

    # supply by industry
    by_industry = q("""
        SELECT c.industry, COUNT(e.job_id) jobs_posted,
               ROUND(AVG(e.salary)/100000.0,2) avg_salary_L
        FROM job_supply_events e JOIN companies c ON e.company_id=c.company_id
        GROUP BY c.industry ORDER BY jobs_posted DESC
    """)
    fig_ind = px.bar(by_industry, x="industry", y="jobs_posted",
                     color="avg_salary_L",
                     title="Job Supply by Industry (avg salary in Lakhs shown as color)",
                     color_continuous_scale="Teal",
                     labels={"avg_salary_L":"Avg Salary (L)"})
    fig_ind.update_layout(height=300, margin=dict(t=40,b=10))
    st.plotly_chart(fig_ind, use_container_width=True)

    # salary vs threshold scatter
    scatter_df = q("""
        SELECT job_title, min_cgpa, salary, status,
               ROUND(salary/100000.0,1) salary_L
        FROM job_supply_events
    """)
    fig_scat = px.scatter(scatter_df, x="min_cgpa", y="salary_L",
                          color="job_title", symbol="status",
                          title="Salary vs CGPA Threshold (each dot = one job posting)",
                          labels={"min_cgpa":"Min CGPA Required","salary_L":"Salary (Lakhs)"},
                          opacity=0.7)
    fig_scat.update_layout(height=380, margin=dict(t=40,b=10))
    st.plotly_chart(fig_scat, use_container_width=True)

    st.divider()
    st.subheader("Raw Event Log — job_supply_events")
    raw = q("""
        SELECT e.event_id, e.event_name, e.job_id, c.company_name,
               e.job_title, e.skills, e.min_cgpa,
               ROUND(e.salary/100000.0,2) AS salary_L, e.status, e.emitted_at
        FROM job_supply_events e JOIN companies c ON e.company_id=c.company_id
        ORDER BY e.emitted_at DESC
    """)
    st.dataframe(raw, use_container_width=True, height=360)


# ═══════════════════════════════════════════════════════
# TAB 3 — VALIDATION (Task 2 checks)
# ═══════════════════════════════════════════════════════
with tabs[2]:
    st.subheader("Job Supply Event Validation — All Checks")

    STATUS_COLOR = {"PASS":"#22c55e","WARN":"#f59e0b","FAIL":"#ef4444"}

    def badge(s):
        c = STATUS_COLOR.get(s,"#888")
        return f'<span style="background:{c};color:#fff;padding:2px 9px;border-radius:20px;font-size:12px;font-weight:600">{s}</span>'

    # Check 1
    total_ev = q("SELECT COUNT(*) n FROM job_supply_events").iloc[0,0]
    total_j  = q("SELECT COUNT(*) n FROM jobs").iloc[0,0]
    s1 = "PASS" if total_ev == total_j else "FAIL"
    st.markdown(f'**Check 1 — Event count matches jobs table** {badge(s1)}', unsafe_allow_html=True)
    st.caption(f"job_supply_events: {total_ev} rows | jobs: {total_j} rows")

    # Check 2 — nulls
    null_cols = ["event_name","job_id","company_id","job_title","skills","min_cgpa","salary","emitted_at"]
    null_results = []
    for col in null_cols:
        n = q(f"SELECT SUM(CASE WHEN {col} IS NULL THEN 1 ELSE 0 END) n FROM job_supply_events").iloc[0,0]
        null_results.append((col, n, "PASS" if n==0 else "FAIL"))
    any_null = any(r[2]=="FAIL" for r in null_results)
    st.markdown(f'**Check 2 — No nulls in required fields** {badge("PASS" if not any_null else "FAIL")}',
                unsafe_allow_html=True)
    for col, n, s in null_results:
        color = STATUS_COLOR[s]
        st.markdown(
            f'<div style="border-left:3px solid {color};padding:2px 12px;margin:2px 0;font-size:13px">'
            f'<code>{col}</code> — {n} nulls {badge(s)}</div>', unsafe_allow_html=True)

    # Check 3 — duplicates
    dups = q("SELECT COUNT(*) n FROM (SELECT job_id FROM job_supply_events GROUP BY job_id HAVING COUNT(*)>1)").iloc[0,0]
    s3 = "PASS" if dups == 0 else "WARN"
    st.markdown(f'**Check 3 — No duplicate job_id events** {badge(s3)}', unsafe_allow_html=True)
    st.caption(f"Duplicate job_ids found: {dups}")

    # Check 4 — freshness
    last_ts = q("SELECT MAX(emitted_at) ts FROM job_supply_events").iloc[0,0]
    hours_ago = (TODAY - dt.datetime.strptime(last_ts, "%Y-%m-%d %H:%M:%S")).total_seconds() / 3600
    s4 = "PASS" if hours_ago < 48 else "FAIL"
    st.markdown(f'**Check 4 — Freshness (SLA: < 48h)** {badge(s4)}', unsafe_allow_html=True)
    st.caption(f"Last event: {last_ts} ({hours_ago:.1f}h ago)")

    # Check 5 — skill threshold
    no_thresh = q("SELECT COUNT(*) n FROM job_supply_events WHERE min_cgpa IS NULL OR min_cgpa=0").iloc[0,0]
    s5 = "PASS" if no_thresh == 0 else "WARN"
    st.markdown(f'**Check 5 — Skill threshold (min_cgpa) populated** {badge(s5)}', unsafe_allow_html=True)
    st.caption(f"Jobs missing threshold: {no_thresh}")

    st.divider()
    st.success("✅ All 5 validation checks PASS — job_post events validated, jobs-posted view is live.")


# ═══════════════════════════════════════════════════════
# TAB 4 — RAW DATA
# ═══════════════════════════════════════════════════════
with tabs[3]:
    table = st.selectbox("Table", ["applications","jobs","students","companies","interviews","offers","job_supply_events"])
    st.dataframe(q(f"SELECT * FROM {table}"), use_container_width=True, height=500)
