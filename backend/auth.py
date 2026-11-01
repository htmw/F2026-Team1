
"""Authentication, password hashing, and PostgreSQL sessions."""

import hashlib
import hmac
import secrets

from datetime import datetime, timedelta, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from .db import get_postgres_db


COOKIE = "dual_session"
SESSION_HOURS = 12
ITERATIONS = 200_000


# ---------- Password hashing ----------

def hash_password(password):
    """Hash a password using PBKDF2-SHA256."""

    salt = secrets.token_hex(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        ITERATIONS,
    )

    return (
        f"pbkdf2_sha256${ITERATIONS}$"
        f"{salt}${digest.hex()}"
    )


def verify_password(password, stored):
    """Verify a password, safely rejecting malformed hashes."""

    if not isinstance(password, str) or not isinstance(stored, str):
        return False

    try:
        algorithm, iterations_text, salt, expected = stored.split("$")

        if algorithm != "pbkdf2_sha256":
            return False

        iterations = int(iterations_text)

        if iterations < 1 or iterations > 2_000_000:
            return False

        salt_bytes = bytes.fromhex(salt)
        expected_bytes = bytes.fromhex(expected)

        if len(expected_bytes) != hashlib.sha256().digest_size:
            return False

        digest = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt_bytes,
            iterations,
        )

        return hmac.compare_digest(digest, expected_bytes)

    except (ValueError, TypeError, OverflowError):
        return False


# ---------- Sessions ----------

def session_token(request: Request):
    """Return the bearer token, or the session cookie."""

    authorization = request.headers.get("Authorization", "")

    if authorization.startswith("Bearer "):
        return authorization[len("Bearer "):].strip() or None

    return request.cookies.get(COOKIE)


def new_postgres_session(conn, user_id):
    """Create a PostgreSQL session.

    The Supabase sessions.expires_at column is TEXT,
    so the expiration is stored as an ISO-formatted string.
    """

    token = secrets.token_urlsafe(32)

    expires_at = (
        datetime.now(timezone.utc)
        + timedelta(hours=SESSION_HOURS)
    ).isoformat(timespec="seconds")

    conn.execute(
        """
        INSERT INTO sessions (
            token,
            user_id,
            expires_at
        )
        VALUES (%s, %s, %s)
        """,
        (
            token,
            user_id,
            expires_at,
        ),
    )

    return token


def current_postgres_user(
    request: Request,
    conn=Depends(get_postgres_db),
):
    """Retrieve the user belonging to a valid session."""

    token = session_token(request)

    if not token:
        raise HTTPException(
            status_code=401,
            detail="Not signed in",
        )

    row = conn.execute(
        """
        SELECT
            u.id,
            u.name,
            u.role,
            u.email,
            s.expires_at
        FROM sessions s
        JOIN users u
            ON u.id = s.user_id
        WHERE s.token = %s
        """,
        (token,),
    ).fetchone()

    if row is None:
        raise HTTPException(
            status_code=401,
            detail="Not signed in",
        )

    try:
        expires_at = row["expires_at"]

        if isinstance(expires_at, str):
            expires_at = datetime.fromisoformat(expires_at)

        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

    except (ValueError, TypeError, AttributeError):
        raise HTTPException(
            status_code=401,
            detail="Session expired",
        )

    if expires_at <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=401,
            detail="Session expired",
        )

    return {
        "id": row["id"],
        "name": row["name"],
        "role": row["role"],
        "email": row["email"],
    }


PostgresCurrentUser = Annotated[
    dict,
    Depends(current_postgres_user),
]
