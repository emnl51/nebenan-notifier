import sqlite3
import os
from datetime import datetime

DB_PATH = os.environ.get("DB_PATH", "data/app.db")


def get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_conn()
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS settings (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            telegram_bot_token TEXT,
            telegram_chat_id TEXT,
            nebenan_username TEXT,
            nebenan_password TEXT,
            login_ok INTEGER DEFAULT 0,
            last_login_at TEXT
        );

        CREATE TABLE IF NOT EXISTS jobs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            feed_url TEXT NOT NULL,
            category TEXT,
            keywords TEXT,        -- virgülle ayrılmış, en az biri geçmeli (boşsa hepsi kabul)
            blacklist TEXT,       -- virgülle ayrılmış, biri geçerse elenir
            interval_minutes INTEGER DEFAULT 15,
            active INTEGER DEFAULT 1,
            created_at TEXT,
            last_run_at TEXT,
            last_status TEXT
        );

        CREATE TABLE IF NOT EXISTS listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            job_id INTEGER NOT NULL,
            external_id TEXT NOT NULL,
            title TEXT,
            price TEXT,
            url TEXT,
            image_url TEXT,
            found_at TEXT,
            notified INTEGER DEFAULT 0,
            UNIQUE(job_id, external_id),
            FOREIGN KEY (job_id) REFERENCES jobs(id)
        );
        """
    )
    conn.execute(
        "INSERT OR IGNORE INTO settings (id, login_ok) VALUES (1, 0)"
    )
    conn.commit()
    conn.close()


def get_settings():
    conn = get_conn()
    row = conn.execute("SELECT * FROM settings WHERE id = 1").fetchone()
    conn.close()
    return dict(row) if row else {}


def update_settings(**kwargs):
    conn = get_conn()
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values())
    conn.execute(f"UPDATE settings SET {fields} WHERE id = 1", values)
    conn.commit()
    conn.close()


def list_jobs():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM jobs ORDER BY id DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_job(job_id):
    conn = get_conn()
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    conn.close()
    return dict(row) if row else None


def create_job(name, feed_url, category, keywords, blacklist, interval_minutes):
    conn = get_conn()
    conn.execute(
        """INSERT INTO jobs (name, feed_url, category, keywords, blacklist,
           interval_minutes, active, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 1, ?)""",
        (name, feed_url, category, keywords, blacklist, interval_minutes,
         datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def update_job(job_id, **kwargs):
    conn = get_conn()
    fields = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values()) + [job_id]
    conn.execute(f"UPDATE jobs SET {fields} WHERE id = ?", values)
    conn.commit()
    conn.close()


def delete_job(job_id):
    conn = get_conn()
    conn.execute("DELETE FROM jobs WHERE id = ?", (job_id,))
    conn.execute("DELETE FROM listings WHERE job_id = ?", (job_id,))
    conn.commit()
    conn.close()


def mark_job_run(job_id, status):
    conn = get_conn()
    conn.execute(
        "UPDATE jobs SET last_run_at = ?, last_status = ? WHERE id = ?",
        (datetime.utcnow().isoformat(), status, job_id),
    )
    conn.commit()
    conn.close()


def listing_exists(job_id, external_id):
    conn = get_conn()
    row = conn.execute(
        "SELECT id FROM listings WHERE job_id = ? AND external_id = ?",
        (job_id, external_id),
    ).fetchone()
    conn.close()
    return row is not None


def add_listing(job_id, external_id, title, price, url, image_url):
    conn = get_conn()
    conn.execute(
        """INSERT OR IGNORE INTO listings
           (job_id, external_id, title, price, url, image_url, found_at, notified)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
        (job_id, external_id, title, price, url, image_url,
         datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()


def mark_notified(job_id, external_id):
    conn = get_conn()
    conn.execute(
        "UPDATE listings SET notified = 1 WHERE job_id = ? AND external_id = ?",
        (job_id, external_id),
    )
    conn.commit()
    conn.close()


def recent_listings(limit=50):
    conn = get_conn()
    rows = conn.execute(
        """SELECT listings.*, jobs.name AS job_name
           FROM listings JOIN jobs ON listings.job_id = jobs.id
           ORDER BY listings.found_at DESC LIMIT ?""",
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]
