
"""Database connections and helpers for DUAL EyeQ."""

import os
from datetime import datetime

import psycopg
from psycopg.rows import dict_row
from dotenv import load_dotenv


# ---------- Date helpers ----------

def now():
    """Return the current datetime in ISO 8601 format."""
    return datetime.now().astimezone().isoformat(
        timespec="seconds"
    )


def today():
    """Return the current date in ISO 8601 format."""
    return datetime.now().date().isoformat()


# ---------- Supabase PostgreSQL ----------

def connect_postgres():
    """Connect to the Supabase PostgreSQL database."""

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
    """Generate sequential readable IDs safely."""

    allowed_tables = {
        "patients",
        "images",
        "screenings",
        "heatmaps",
    }

    if table not in allowed_tables:
        raise ValueError("Unsupported table")

    # Prevent concurrent requests from generating
    # the same identifier.
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
