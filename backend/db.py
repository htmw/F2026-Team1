"""SQLite storage for the DUAL app.

All patients are dummy (made-up people). The database file, uploaded photos and
heatmaps live in backend/storage/, which git ignores. Delete that folder to
start again from the demo data.
"""
import os
import sqlite3
from datetime import datetime
from pathlib import Path

STORAGE = Path(os.environ.get("DUAL_STORAGE", Path(__file__).resolve().parent / "storage"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    name          TEXT NOT NULL,
    role          TEXT NOT NULL,            -- clinician / medical_assistant
    email         TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token      TEXT PRIMARY KEY,
    user_id    INTEGER NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS patients (
    id         TEXT PRIMARY KEY,            -- P-001
    full_name  TEXT NOT NULL,
    age        INTEGER NOT NULL,
    sex        TEXT NOT NULL,               -- female / male / other
    phone      TEXT,
    email      TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS images (
    id             TEXT PRIMARY KEY,        -- IMG-0001
    patient_id     TEXT NOT NULL REFERENCES patients(id),
    eye            TEXT NOT NULL,           -- right / left
    file_name      TEXT NOT NULL,           -- P-001_right.jpg, never the patient's name
    stored_path    TEXT,                    -- relative to STORAGE; NULL when unreadable
    width          INTEGER,
    height         INTEGER,
    quality_status TEXT NOT NULL,           -- passed / failed
    quality_reason TEXT,                    -- unreadable / too_dark / not_fundus
    uploaded_at    TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS model_versions (
    id               TEXT PRIMARY KEY,      -- v0-mock now, v1.0 after Task 19
    thresholds       TEXT NOT NULL,         -- JSON: {"cataract": 0.35, "glaucoma": 0.50}
    uncertain_margin REAL NOT NULL,
    commit_hash      TEXT,                  -- NULL until Task 19 tags a commit
    is_mock          INTEGER NOT NULL,
    released_at      TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS screenings (
    id               TEXT PRIMARY KEY,      -- SCR-0001
    patient_id       TEXT NOT NULL REFERENCES patients(id),
    image_id         TEXT REFERENCES images(id),
    eye              TEXT NOT NULL,
    created_at       TEXT NOT NULL,
    created_by       INTEGER NOT NULL REFERENCES users(id),
    model_version_id TEXT REFERENCES model_versions(id),
    overall_result   TEXT,                  -- no_concern / refer; NULL when skipped
    skipped          INTEGER NOT NULL DEFAULT 0,
    skip_reason      TEXT
);
CREATE TABLE IF NOT EXISTS condition_results (
    id               INTEGER PRIMARY KEY,
    screening_id     TEXT NOT NULL REFERENCES screenings(id),
    condition        TEXT NOT NULL,         -- cataract / glaucoma
    raw_score        REAL NOT NULL,
    calibrated_score REAL NOT NULL,
    result           TEXT NOT NULL          -- no_concern / refer / uncertain
);
CREATE TABLE IF NOT EXISTS heatmaps (
    id                  TEXT PRIMARY KEY,   -- HM-0001
    condition_result_id INTEGER NOT NULL REFERENCES condition_results(id),
    stored_path         TEXT NOT NULL
);
"""


def connect():
    STORAGE.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(STORAGE / "dual.db", check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def get_db():
    """One connection per request. Routes that write call conn.commit() themselves."""
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()


def now():
    """Local time with its UTC offset, e.g. 2026-10-08T14:05:00-04:00."""
    return datetime.now().astimezone().isoformat(timespec="seconds")


def today():
    return datetime.now().date().isoformat()


def next_id(conn, table, prefix, width):
    """Next readable ID, e.g. next_id(conn, "patients", "P-", 3) -> "P-005"."""
    row = conn.execute(
        f"SELECT MAX(CAST(SUBSTR(id, {len(prefix) + 1}) AS INTEGER)) FROM {table}"
    ).fetchone()
    return f"{prefix}{(row[0] or 0) + 1:0{width}d}"
