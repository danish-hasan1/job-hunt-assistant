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
        CREATE TABLE IF NOT EXISTS hiring_targets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company TEXT,
            role TEXT,
            source_role TEXT,
            contact_name TEXT,
            contact_title TEXT,
            linkedin_url TEXT UNIQUE,
            status TEXT DEFAULT 'new',
            message_sent INTEGER DEFAULT 0,
            created_at TEXT,
            updated_at TEXT,
            job_id INTEGER
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


def get_setting(key):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    )
    row = conn.execute(
        "SELECT value FROM settings WHERE key=?", (key,)
    ).fetchone()
    conn.close()
    return row[0] if row else None


def set_setting(key, value):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)"
    )
    conn.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
        (key, value),
    )
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

def insert_hiring_targets(rows):
    if not rows:
        return
    conn = sqlite3.connect(DB_PATH)
    try:
        conn.executemany(
            """
            INSERT OR IGNORE INTO hiring_targets
            (company, role, source_role, contact_name, contact_title, linkedin_url, status, message_sent, created_at, updated_at, job_id)
            VALUES (:company, :role, :source_role, :contact_name, :contact_title, :linkedin_url, :status, :message_sent, :created_at, :updated_at, :job_id)
            """,
            rows,
        )
        conn.commit()
    finally:
        conn.close()

def get_hiring_targets_by_status(status):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM hiring_targets WHERE status=? ORDER BY created_at DESC, id DESC",
        (status,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def update_hiring_target_status(target_id, status):
    conn = sqlite3.connect(DB_PATH)
    now = datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE hiring_targets SET status=?, updated_at=? WHERE id=?",
        (status, now, target_id),
    )
    conn.commit()
    conn.close()

def update_hiring_target_message_flag(target_id, sent):
    conn = sqlite3.connect(DB_PATH)
    now = datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE hiring_targets SET message_sent=?, updated_at=? WHERE id=?",
        (1 if sent else 0, now, target_id),
    )
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
