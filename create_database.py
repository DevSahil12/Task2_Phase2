import sqlite3

conn = sqlite3.connect("placemux.db")
cur = conn.cursor()

cur.executescript("""
DROP TABLE IF EXISTS job_supply_events;
DROP TABLE IF EXISTS offers;
DROP TABLE IF EXISTS interviews;
DROP TABLE IF EXISTS applications;
DROP TABLE IF EXISTS students;
DROP TABLE IF EXISTS jobs;
DROP TABLE IF EXISTS companies;

CREATE TABLE companies (
    company_id   INTEGER PRIMARY KEY,
    company_name TEXT,
    industry     TEXT,
    created_at   TEXT,
    status       TEXT
);

CREATE TABLE jobs (
    job_id        INTEGER PRIMARY KEY,
    company_id    INTEGER,
    job_title     TEXT,
    skills        TEXT,
    min_cgpa      REAL,
    salary        INTEGER,
    created_at    TEXT,
    status        TEXT,
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);

CREATE TABLE students (
    student_id   INTEGER PRIMARY KEY,
    student_name TEXT,
    college      TEXT,
    cgpa         REAL,
    skills       TEXT,
    created_at   TEXT
);

CREATE TABLE applications (
    application_id INTEGER PRIMARY KEY,
    student_id     INTEGER,
    job_id         INTEGER,
    applied_at     TEXT,
    status         TEXT,
    FOREIGN KEY (student_id) REFERENCES students(student_id),
    FOREIGN KEY (job_id)     REFERENCES jobs(job_id)
);

CREATE TABLE interviews (
    interview_id   INTEGER PRIMARY KEY,
    application_id INTEGER,
    scheduled_at   TEXT,
    status         TEXT,
    FOREIGN KEY (application_id) REFERENCES applications(application_id)
);

CREATE TABLE offers (
    offer_id       INTEGER PRIMARY KEY,
    application_id INTEGER,
    offered_at     TEXT,
    status         TEXT,
    FOREIGN KEY (application_id) REFERENCES applications(application_id)
);

-- ── TASK 2: Job-supply instrumentation event log ──────────────────────────
-- Every time a job is posted this event fires and lands here.
-- Columns mirror the tracking plan payload exactly.
CREATE TABLE job_supply_events (
    event_id      INTEGER PRIMARY KEY AUTOINCREMENT,
    event_name    TEXT    DEFAULT 'job_posted',
    job_id        INTEGER,
    company_id    INTEGER,
    job_title     TEXT,
    skills        TEXT,
    min_cgpa      REAL,
    salary        INTEGER,
    status        TEXT,
    emitted_at    TEXT,
    FOREIGN KEY (job_id)    REFERENCES jobs(job_id),
    FOREIGN KEY (company_id) REFERENCES companies(company_id)
);
""")

conn.commit()
conn.close()
print("Database created with full schema.")
