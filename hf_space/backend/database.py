import sqlite3
import uuid
import os
from datetime import datetime, timezone

DB_PATH = os.getenv("DB_PATH", "/data/charges.db")

SCHEMA = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS charges (
    id TEXT PRIMARY KEY,
    amount REAL NOT NULL CHECK(amount > 0),
    currency TEXT NOT NULL DEFAULT 'USD',
    customer_id TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'PENDING'
        CHECK(status IN ('PENDING','PROCESSING','SUCCESS','FAILED')),
    max_retries INTEGER NOT NULL DEFAULT 3,
    retry_count INTEGER NOT NULL DEFAULT 0,
    next_retry_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS charge_attempts (
    id TEXT PRIMARY KEY,
    charge_id TEXT NOT NULL REFERENCES charges(id),
    attempt_number INTEGER NOT NULL,
    status TEXT NOT NULL CHECK(status IN ('SUCCESS','FAILED')),
    error_code TEXT,
    error_message TEXT,
    processor_response TEXT,
    attempted_at TEXT NOT NULL,
    duration_ms INTEGER NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_charges_status ON charges(status);
CREATE INDEX IF NOT EXISTS idx_charges_next_retry ON charges(next_retry_at);
CREATE INDEX IF NOT EXISTS idx_attempts_charge ON charge_attempts(charge_id);
"""

def get_db_path() -> str:
    return DB_PATH

def init_db(db_path: str) -> None:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.executescript(SCHEMA)
    conn.commit()
    conn.close()

def get_connection(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    return conn

def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()

def insert_charge(conn, charge_id, amount, currency, customer_id, description, max_retries=3):
    ts = now_iso()
    conn.execute(
        "INSERT INTO charges (id,amount,currency,customer_id,description,max_retries,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?)",
        (charge_id, amount, currency, customer_id, description, max_retries, ts, ts)
    )
    conn.commit()

def get_charge(conn, charge_id: str):
    row = conn.execute("SELECT * FROM charges WHERE id=?", (charge_id,)).fetchone()
    return dict(row) if row else None

def update_charge_status(conn, charge_id: str, status: str, retry_count: int = None, next_retry_at: str = None):
    parts = ["status=?", "updated_at=?"]
    vals = [status, now_iso()]
    if retry_count is not None:
        parts.append("retry_count=?")
        vals.append(retry_count)
    if next_retry_at is not None:
        parts.append("next_retry_at=?")
        vals.append(next_retry_at)
    vals.append(charge_id)
    conn.execute(f"UPDATE charges SET {', '.join(parts)} WHERE id=?", vals)
    conn.commit()

def insert_attempt(conn, charge_id, attempt_number, status, error_code, error_message, processor_response, duration_ms):
    conn.execute(
        "INSERT INTO charge_attempts (id,charge_id,attempt_number,status,error_code,error_message,processor_response,attempted_at,duration_ms) "
        "VALUES (?,?,?,?,?,?,?,?,?)",
        (str(uuid.uuid4()), charge_id, attempt_number, status, error_code, error_message, processor_response, now_iso(), duration_ms)
    )
    conn.commit()

def get_attempts(conn, charge_id: str):
    rows = conn.execute(
        "SELECT * FROM charge_attempts WHERE charge_id=? ORDER BY attempt_number", (charge_id,)
    ).fetchall()
    return [dict(r) for r in rows]

def get_stats(conn):
    row = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN status='SUCCESS' THEN 1 ELSE 0 END) as success,
            SUM(CASE WHEN status='FAILED'  THEN 1 ELSE 0 END) as failed,
            SUM(CASE WHEN status='PENDING' THEN 1 ELSE 0 END) as pending,
            SUM(CASE WHEN status='PROCESSING' THEN 1 ELSE 0 END) as processing
        FROM charges
    """).fetchone()
    total = row["total"] or 0
    success = row["success"] or 0
    avg_row = conn.execute(
        "SELECT AVG(attempt_number) FROM charge_attempts WHERE status='SUCCESS'"
    ).fetchone()
    return {
        "total_charges": total,
        "success_count": success,
        "failed_count": row["failed"] or 0,
        "pending_count": row["pending"] or 0,
        "processing_count": row["processing"] or 0,
        "success_rate": round(success / total, 3) if total > 0 else 0.0,
        "avg_attempts_to_success": round(avg_row[0] or 0.0, 2),
    }