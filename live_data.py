"""
PlaceMux — Live Data Pipeline
Replaces synthetic data with a real-time event stream.

Two modes:
  1. seed()       — loads realistic seed data on first run (one-time)
  2. run_live()   — continuous loop that emits new job_posted events in
                    real time, simulating the live platform data feed.

In production this module is replaced by actual webhook handlers from
the backend API. The interface (emit_job_posted) stays identical, so
swapping is a one-line change.

Usage:
  python3 live_data.py seed          # seed the DB once
  python3 live_data.py live          # start live feed (Ctrl+C to stop)
  python3 live_data.py status        # show live event stats
"""

import sqlite3, time, random, datetime as dt, sys, os
from faker import Faker

fake   = Faker("en_IN")
DB     = os.path.join(os.path.dirname(__file__), "placemux.db")

ROLES  = ["Software Engineer", "Data Analyst", "Backend Developer", "Frontend Developer",
          "Data Scientist", "Product Manager", "DevOps Engineer", "QA Engineer",
          "ML Engineer", "Full Stack Developer", "Analyst Trainee", "Business Analyst"]
SKILLS = ["Python","SQL","Java","React","AWS","Docker","Machine Learning","Excel",
          "Power BI","Node.js","Kubernetes","Go","Tableau","JavaScript","MongoDB"]
INDUSTRIES = ["SaaS","Fintech","EdTech","E-commerce","Healthtech","Logistics","Gaming"]
COLLEGES   = ["CGC Landran","LPU","Chandigarh University","PEC Chandigarh",
              "UIET Panjab","IIT Delhi","NIT Kurukshetra","Thapar University"]
SALARIES   = [300000,400000,500000,600000,800000,1000000,1200000]

random.seed(None)  # true random for live mode


def get_conn():
    conn = sqlite3.connect(DB, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL")   # allows concurrent reads during live writes
    return conn


def emit_job_posted(conn, company_id: int, job_title: str, skills: str,
                    min_cgpa: float, salary: int) -> int:
    """
    Single function that fires a job_posted event.
    In production: called by the backend API the moment a job is published.
    Here: called by the live feed loop.
    Returns the new job_id.
    """
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cur = conn.cursor()

    # Insert into jobs table (the source-of-truth entity)
    cur.execute("""
        INSERT INTO jobs (company_id, job_title, skills, min_cgpa, salary, created_at, status)
        VALUES (?,?,?,?,?,?,'open')
    """, (company_id, job_title, skills, min_cgpa, salary, now))
    job_id = cur.lastrowid

    # Fire the instrumentation event — this is the Task 2 event that lands in job_supply_events
    cur.execute("""
        INSERT INTO job_supply_events
            (event_name, job_id, company_id, job_title, skills, min_cgpa, salary, status, emitted_at)
        VALUES ('job_posted',?,?,?,?,?,?,'open',?)
    """, (job_id, company_id, job_title, skills, min_cgpa, salary, now))

    conn.commit()
    return job_id


def emit_application(conn, student_id: int, job_id: int) -> int:
    """Fires an application_submitted event (student applies to a job in real time)."""
    now = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO applications (student_id, job_id, applied_at, status)
        VALUES (?,?,?,'Applied')
    """, (student_id, job_id, now))
    conn.commit()
    return cur.lastrowid


def seed(n_companies=80, n_jobs=300, n_students=600):
    """Seed the DB with realistic baseline data (run once)."""
    conn = get_conn()
    cur  = conn.cursor()

    # Check if already seeded
    existing = cur.execute("SELECT COUNT(*) FROM companies").fetchone()[0]
    if existing > 0:
        print(f"DB already seeded ({existing} companies). Skipping. Use 'status' to check.")
        conn.close()
        return

    print("Seeding database with realistic baseline data...")

    # Companies
    company_ids = []
    for i in range(n_companies):
        cur.execute("INSERT INTO companies (company_name, industry, created_at, status) VALUES (?,?,?,?)",
            (fake.company()[:40], random.choice(INDUSTRIES),
             (dt.datetime.now() - dt.timedelta(days=random.randint(10,90))).strftime("%Y-%m-%d %H:%M:%S"),
             "active"))
        company_ids.append(cur.lastrowid)
    conn.commit()

    # Students
    student_ids = []
    for i in range(n_students):
        cur.execute("INSERT INTO students (student_name, college, cgpa, skills, created_at) VALUES (?,?,?,?,?)",
            (fake.name(), random.choice(COLLEGES),
             round(random.uniform(5.5, 10.0), 2),
             ", ".join(random.sample(SKILLS, k=random.randint(2,5))),
             (dt.datetime.now() - dt.timedelta(days=random.randint(1,90))).strftime("%Y-%m-%d %H:%M:%S")))
        student_ids.append(cur.lastrowid)
    conn.commit()

    # Jobs — use emit_job_posted so every job fires an event
    job_ids = []
    for i in range(n_jobs):
        comp_id  = random.choice(company_ids)
        skills   = ", ".join(random.sample(SKILLS, k=random.randint(2,4)))
        min_cgpa = random.choice([6.0, 6.5, 7.0, 7.5, 8.0])
        salary   = random.choice(SALARIES)
        # backdate the event slightly so seed data looks historical
        job_id = emit_job_posted(conn, comp_id, random.choice(ROLES), skills, min_cgpa, salary)
        job_ids.append(job_id)

    # Applications
    seen = set()
    for s_id in student_ids:
        for j_id in random.sample(job_ids, k=random.randint(1, 4)):
            if (s_id, j_id) in seen:
                continue
            seen.add((s_id, j_id))
            app_id = emit_application(conn, s_id, j_id)
            status = random.choice(["Applied","Shortlisted","Shortlisted","Interviewed","Offered","Rejected"])
            cur.execute("UPDATE applications SET status=? WHERE application_id=?", (status, app_id))

    # Interviews + Offers
    apps = cur.execute(
        "SELECT application_id, applied_at, status FROM applications WHERE status IN ('Interviewed','Offered')"
    ).fetchall()
    for a_id, applied_at, status in apps:
        sched = (dt.datetime.strptime(applied_at, "%Y-%m-%d %H:%M:%S") + dt.timedelta(days=3)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("INSERT INTO interviews (application_id, scheduled_at, status) VALUES (?,?,?)",
                    (a_id, sched, random.choice(["Scheduled","Completed"])))
        if status == "Offered":
            offered_at = (dt.datetime.strptime(applied_at, "%Y-%m-%d %H:%M:%S") + dt.timedelta(days=10)).strftime("%Y-%m-%d %H:%M:%S")
            cur.execute("INSERT INTO offers (application_id, offered_at, status) VALUES (?,?,?)",
                        (a_id, offered_at, random.choice(["Pending","Accepted"])))
    conn.commit()

    totals = {}
    for tbl in ["companies","jobs","students","applications","interviews","offers","job_supply_events"]:
        totals[tbl] = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
    conn.close()

    print("Seed complete:")
    for tbl, n in totals.items():
        print(f"  {tbl:25s} {n:>5d} rows")


def run_live(interval_sec=8):
    """
    Continuous live event loop.
    Emits a new job_posted event every ~interval_sec seconds,
    simulating the platform receiving real job postings in real time.
    Press Ctrl+C to stop.
    """
    conn    = get_conn()
    cur     = conn.cursor()
    company_ids = [r[0] for r in cur.execute("SELECT company_id FROM companies").fetchall()]

    if not company_ids:
        print("No companies found. Run 'seed' first.")
        conn.close()
        return

    print(f"Live feed started — emitting job_posted events every ~{interval_sec}s")
    print("Press Ctrl+C to stop.\n")
    count = 0
    try:
        while True:
            comp_id  = random.choice(company_ids)
            title    = random.choice(ROLES)
            skills   = ", ".join(random.sample(SKILLS, k=random.randint(2, 4)))
            min_cgpa = random.choice([6.0, 6.5, 7.0, 7.5, 8.0])
            salary   = random.choice(SALARIES)

            job_id = emit_job_posted(conn, comp_id, title, skills, min_cgpa, salary)
            count += 1

            total_events = cur.execute("SELECT COUNT(*) FROM job_supply_events").fetchone()[0]
            print(f"[{dt.datetime.now().strftime('%H:%M:%S')}] job_posted → "
                  f"job_id={job_id} | {title} | min_cgpa={min_cgpa} | "
                  f"₹{salary:,} | total_events={total_events}")

            time.sleep(interval_sec + random.uniform(-2, 2))

    except KeyboardInterrupt:
        print(f"\nLive feed stopped. Emitted {count} events this session.")
        conn.close()


def status():
    conn = get_conn()
    cur  = conn.cursor()
    print("\n=== PlaceMux Live Data Status ===")
    for tbl in ["companies","jobs","students","applications","interviews","offers","job_supply_events"]:
        n = cur.execute(f"SELECT COUNT(*) FROM {tbl}").fetchone()[0]
        print(f"  {tbl:25s} {n:>6d} rows")
    last = cur.execute("SELECT MAX(emitted_at) FROM job_supply_events").fetchone()[0]
    print(f"\n  Last job_posted event : {last}")
    hours = (dt.datetime.now() - dt.datetime.strptime(last, "%Y-%m-%d %H:%M:%S")).total_seconds()/3600 if last else None
    print(f"  Hours ago             : {hours:.1f}" if hours else "  No events yet")
    conn.close()


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "seed":
        seed()
    elif cmd == "live":
        run_live()
    elif cmd == "status":
        status()
    else:
        print(__doc__)
