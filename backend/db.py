
"""Database connections and helpers for Dual Eye Q."""

import os
import sqlite3
from datetime import datetime
from pathlib import Path

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


# ---------- Original SQLite implementation ----------

STORAGE = Path(
    os.environ.get(
        "DUAL_STORAGE",
        Path(__file__).resolve().parent / "storage",
    )
)

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    expires_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS patients (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    age INTEGER NOT NULL,
    sex TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS images (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patients(id),
    eye TEXT NOT NULL,
    file_name TEXT NOT NULL,
    stored_path TEXT,
    width INTEGER,
    height INTEGER,
    quality_status TEXT NOT NULL,
    quality_reason TEXT,
    uploaded_at TEXT NOT NULL,
    sha256 TEXT
);
CREATE TABLE IF NOT EXISTS model_versions (
    id TEXT PRIMARY KEY,
    thresholds TEXT NOT NULL,
    uncertain_margin REAL NOT NULL,
    commit_hash TEXT,
    is_mock INTEGER NOT NULL,
    released_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS screenings (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL REFERENCES patients(id),
    image_id TEXT REFERENCES images(id),
    eye TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(id),
    model_version_id TEXT REFERENCES model_versions(id),
    overall_result TEXT,
    skipped INTEGER NOT NULL DEFAULT 0,
    skip_reason TEXT
);
CREATE TABLE IF NOT EXISTS condition_results (
    id INTEGER PRIMARY KEY,
    screening_id TEXT NOT NULL REFERENCES screenings(id),
    condition TEXT NOT NULL,
    raw_score REAL NOT NULL,
    calibrated_score REAL NOT NULL,
    result TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS heatmaps (
    id TEXT PRIMARY KEY,
    condition_result_id INTEGER NOT NULL
        REFERENCES condition_results(id),
    stored_path TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS one_screening_per_image
ON screenings(image_id);
"""


# Original SQLite helpers kept for reference.
# PostgreSQL-backed routes do not call these functions.

# def upgrade(conn):
#     columns = [
#         row[1]
#         for row in conn.execute("PRAGMA table_info(images)")
#     ]
#     if "sha256" not in columns:
#         conn.execute(
#             "ALTER TABLE images ADD COLUMN sha256 TEXT"
#         )


# def connect():
#     STORAGE.mkdir(parents=True, exist_ok=True)
#     conn = sqlite3.connect(
#         STORAGE / "dual.db",
#         check_same_thread=False,
#     )
#     conn.row_factory = sqlite3.Row
#     conn.execute("PRAGMA foreign_keys = ON")
#     return conn


# def get_db():
#     conn = connect()
#     try:
#         yield conn
#     finally:
#         conn.close()


# def next_id(conn, table, prefix, width):
#     row = conn.execute(
#         f"SELECT MAX(CAST(SUBSTR(id, "
#         f"{len(prefix) + 1}) AS INTEGER)) FROM {table}"
#     ).fetchone()
#     return f"{prefix}{(row[0] or 0) + 1:0{width}d}"


# ---------- Shared date helpers ----------

def now():
    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


def today():
    return datetime.now().date().isoformat()


# ---------- Supabase PostgreSQL ----------

def connect_postgres():
    """Connect to Supabase PostgreSQL."""

    load_dotenv()

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is missing"
        )

    return psycopg.connect(
        database_url,
        row_factory=dict_row,
        connect_timeout=10,
    )


def get_postgres_db():
    """Provide a PostgreSQL connection per request."""

    conn = connect_postgres()

    try:
        yield conn
    finally:
        conn.close()


def next_id_postgres(conn, table, prefix, width):
    """Generate readable IDs with a transaction lock."""

    allowed_tables = {
        "patients",
        "images",
        "screenings",
        "heatmaps",
    }

    if table not in allowed_tables:
        raise ValueError("Unsupported table")

    conn.execute(
        "SELECT pg_advisory_xact_lock(hashtext(%s))",
        (f"dual-id:{table}",),
    )

    position = len(prefix) + 1

    row = conn.execute(
        f"""
        SELECT COALESCE(
            MAX(
                CAST(
                    SUBSTRING(id FROM %s)
                    AS INTEGER
                )
            ),
            0
        ) + 1 AS next_number
        FROM {table}
        WHERE id ~ %s
        """,
        (
            position,
            f"^{prefix}[0-9]+$",
        ),
    ).fetchone()

    return f"{prefix}{row['next_number']:0{width}d}"
