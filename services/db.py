import sqlite3
import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
import config

class Database:
    def __init__(self, db_path: Path = config.DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _get_connection(self):
        return sqlite3.connect(self.db_path)

    def _init_db(self):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS applications (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT UNIQUE,
                    title TEXT NOT NULL,
                    company TEXT NOT NULL,
                    location TEXT,
                    portal TEXT,
                    job_url TEXT,
                    match_score INTEGER,
                    status TEXT, -- 'DISCOVERED', 'APPLIED', 'FAILED', 'SKIPPED'
                    applied_date TEXT,
                    reference_id TEXT,
                    screenshot_path TEXT,
                    response_details TEXT,
                    email_sent_status TEXT DEFAULT 'PENDING',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Automatically migrate existing schema if columns are missing
            cursor.execute("PRAGMA table_info(applications)")
            columns = [col[1] for col in cursor.fetchall()]
            if "reference_id" not in columns:
                cursor.execute("ALTER TABLE applications ADD COLUMN reference_id TEXT")
            if "screenshot_path" not in columns:
                cursor.execute("ALTER TABLE applications ADD COLUMN screenshot_path TEXT")

            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    applications_count INTEGER DEFAULT 0,
                    emails_sent_count INTEGER DEFAULT 0,
                    last_run_at TIMESTAMP
                )
            """)
            conn.commit()

    def is_job_applied(self, job_id: str) -> bool:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, status FROM applications WHERE job_id = ? AND status = 'APPLIED'", (job_id,))
            return cursor.fetchone() is not None

    def get_today_applied_count(self) -> int:
        today = datetime.date.today().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM applications 
                WHERE status = 'APPLIED' AND applied_date LIKE ?
            """, (f"{today}%",))
            row = cursor.fetchone()
            return row[0] if row else 0

    def record_job(self, job: Dict[str, Any], match_score: int) -> int:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            job_id = job.get("job_id") or f"{job.get('company')}_{job.get('title')}_{job.get('location')}".replace(" ", "_").lower()
            cursor.execute("""
                INSERT OR IGNORE INTO applications 
                (job_id, title, company, location, portal, job_url, match_score, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, 'DISCOVERED')
            """, (
                job_id,
                job.get("title", ""),
                job.get("company", ""),
                job.get("location", ""),
                job.get("portal", "Web"),
                job.get("job_url", ""),
                match_score
            ))
            conn.commit()
            return cursor.lastrowid

    def update_application_status(self, job_id: str, status: str, response_details: str = "", email_sent: bool = False, reference_id: str = None, screenshot_path: str = None):
        today = datetime.date.today().isoformat()
        now = datetime.datetime.now().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE applications
                SET status = ?, 
                    applied_date = ?, 
                    reference_id = ?,
                    screenshot_path = ?,
                    response_details = ?, 
                    email_sent_status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE job_id = ?
            """, (
                status,
                today if status == "APPLIED" else None,
                reference_id,
                screenshot_path,
                response_details,
                "SENT" if email_sent else "PENDING",
                job_id
            ))
            
            if status == "APPLIED":
                cursor.execute("""
                    INSERT INTO daily_stats (date, applications_count, emails_sent_count, last_run_at)
                    VALUES (?, 1, ?, ?)
                    ON CONFLICT(date) DO UPDATE SET 
                        applications_count = applications_count + 1,
                        emails_sent_count = emails_sent_count + ?,
                        last_run_at = ?
                """, (today, 1 if email_sent else 0, now, 1 if email_sent else 0, now))

            conn.commit()

    def get_all_applications(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications ORDER BY created_at DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_applications_by_date(self, date_str: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM applications WHERE applied_date = ? ORDER BY id DESC", (date_str,))
            return [dict(row) for row in cursor.fetchall()]

db = Database()
