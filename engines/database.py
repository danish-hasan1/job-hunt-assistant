import sqlite3
import os
from datetime import datetime, date

DB_PATH = "data/jobs.db"

def init_db():
    os.makedirs("data", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            company TEXT,
            location TEXT,
            track TEXT,
            source TEXT,
            url TEXT UNIQUE,
            description TEXT,
            salary TEXT,
            sponsorship TEXT DEFAULT 'unknown',
            score INTEGER DEFAULT 0,
            score_reason TEXT,
            status TEXT DEFAULT 'new',
            date_found TEXT,
            date_applied TEXT,
            cv_path TEXT,
            cl_path TEXT,
            notes TEXT
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS applications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER,
            company TEXT,
            role TEXT,
            location TEXT,
            track TEXT,
            applied_date TEXT,
            cv_filename TEXT,
            cl_filename TEXT,
            jd_filename TEXT,
            status TEXT DEFAULT 'applied',
            response_date TEXT,
            interview_date TEXT,
            notes TEXT,
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        )
    """)
    conn.commit()
    conn.close()

def insert_job(job_dict):
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.execute("""
            INSERT OR IGNORE INTO jobs 
            (title, company, location, track, source, url, description, salary, sponsorship, date_found)
            VALUES (:title, :company, :location, :track, :source, :url, :description, :salary, :sponsorship, :date_found)
        """, job_dict)
        conn.commit()
    finally:
        conn.close()

def get_all_jobs():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM jobs ORDER BY date_found DESC").fetchall()
    conn.close()
    return [dict(row) for row in rows]

def get_jobs_by_status(status):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM jobs WHERE status=? ORDER BY score DESC", (status,)).fetchall()
    conn.close()
    return [dict(row) for row in rows]

def update_job_status(job_id, status):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE jobs SET status=? WHERE id=?", (status, job_id))
    conn.commit()
    conn.close()

def update_job_score(job_id, score, reason):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE jobs SET score=?, score_reason=? WHERE id=?", (score, reason, job_id))
    conn.commit()
    conn.close()

def get_stats():
    conn = sqlite3.connect(DB_PATH)
    today = date.today().isoformat()
    jobs_today = conn.execute("SELECT COUNT(*) FROM jobs WHERE date_found=?", (today,)).fetchone()[0]
    applied_week = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='applied'").fetchone()[0]
    awaiting_review = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='new' AND score>=55").fetchone()[0]
    interviews = conn.execute("SELECT COUNT(*) FROM jobs WHERE status='interview'").fetchone()[0]
    conn.close()
    return {
        "jobs_today": jobs_today,
        "applied_week": applied_week,
        "awaiting_review": awaiting_review,
        "interviews_scheduled": interviews
    }
