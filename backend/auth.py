
"""Authentication, password hashing and sessions."""

import hashlib
import hmac
import secrets

from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from .db import get_postgres_db


COOKIE = "dual_session"
SESSION_HOURS = 12
ITERATIONS = 200_000


# ---------- Password hashing ----------

def hash_password(password):
    salt = secrets.token_hex(16)

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        bytes.fromhex(salt),
        ITERATIONS,
    )

    return (
        f"pbkdf2_sha256${ITERATIONS}$"
        f"{salt}${digest.hex()}"
    )


def verify_password(password, stored):
    _, iterations, salt, expected = stored.split("$")

    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode(),
        bytes.fromhex(salt),
        int(iterations),
    )

    return hmac.compare_digest(
        digest.hex(),
        expected,
    )


def session_token(request: Request):
    header = request.headers.get(
        "Authorization", ""
    )

    if header.startswith("Bearer "):
        return header[len("Bearer "):]

    return request.cookies.get(COOKIE)


# ---------- Original SQLite implementation ----------

# from .db import get_db
#
#
# def new_session(conn, user_id):
#     token = secrets.token_urlsafe(32)
#     expires = (
#         datetime.now().astimezone()
#         + timedelta(hours=SESSION_HOURS)
#     ).isoformat(timespec="seconds")
#
#     conn.execute(
#         "INSERT INTO sessions "
#         "(token, user_id, expires_at) "
#         "VALUES (?, ?, ?)",
#         (token, user_id, expires),
#     )
#     return token
#
#
# def current_user(
#     request: Request,
#     conn=Depends(get_db),
# ):
#     token = session_token(request)
#     row = None
#
#     if token:
#         row = conn.execute(
#             "SELECT u.id, u.name, u.role, "
#             "u.email, s.expires_at "
#             "FROM sessions s "
#             "JOIN users u ON u.id = s.user_id "
#             "WHERE s.token = ?",
#             (token,),
#         ).fetchone()
#
#     if (
#         row is None
#         or datetime.fromisoformat(
#             row["expires_at"]
#         ) < datetime.now().astimezone()
#     ):
#         raise HTTPException(401, "Not signed in")
#
#     return {
#         "id": row["id"],
#         "name": row["name"],
#         "role": row["role"],
#         "email": row["email"],
#     }
#
#
# CurrentUser = Annotated[
#     dict,
#     Depends(current_user),
# ]


# ---------- PostgreSQL implementation ----------

def new_postgres_session(conn, user_id):
    """Create a PostgreSQL-backed session."""

    token = secrets.token_urlsafe(32)

    expires = (
        datetime.now().astimezone()
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
            expires,
        ),
    )

    return token


def current_postgres_user(
    request: Request,
    conn=Depends(get_postgres_db),
):
    """Retrieve the authenticated PostgreSQL user."""

    token = session_token(request)

    if not token:
        raise HTTPException(
            401,
            "Not signed in",
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
            401,
            "Not signed in",
        )

    expires_at = datetime.fromisoformat(
        row["expires_at"]
    )

    if expires_at < datetime.now().astimezone():
        raise HTTPException(
            401,
            "Session expired",
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
