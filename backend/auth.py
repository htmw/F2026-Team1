"""Login, hashed passwords and sessions.

After login the browser keeps a session cookie, so every later request (and
every <img> for a photo or heatmap) is signed in automatically. Scripts and
tests can send "Authorization: Bearer <token>" instead.
"""
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from .db import get_db

COOKIE = "dual_session"
SESSION_HOURS = 12
ITERATIONS = 200_000


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), ITERATIONS)
    return f"pbkdf2_sha256${ITERATIONS}${salt}${digest.hex()}"


def verify_password(password, stored):
    _, iterations, salt, expected = stored.split("$")
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations))
    return hmac.compare_digest(digest.hex(), expected)


def new_session(conn, user_id):
    token = secrets.token_urlsafe(32)
    expires = (datetime.now().astimezone() + timedelta(hours=SESSION_HOURS)).isoformat(timespec="seconds")
    conn.execute("INSERT INTO sessions (token, user_id, expires_at) VALUES (?, ?, ?)", (token, user_id, expires))
    return token


def session_token(request: Request):
    header = request.headers.get("Authorization", "")
    if header.startswith("Bearer "):
        return header[len("Bearer "):]
    return request.cookies.get(COOKIE)


def current_user(request: Request, conn=Depends(get_db)):
    """Every route except login depends on this: 401 when not signed in."""
    token = session_token(request)
    row = None
    if token:
        row = conn.execute(
            "SELECT u.id, u.name, u.role, u.email, s.expires_at FROM sessions s "
            "JOIN users u ON u.id = s.user_id WHERE s.token = ?",
            (token,),
        ).fetchone()
    if row is None or datetime.fromisoformat(row["expires_at"]) < datetime.now().astimezone():
        raise HTTPException(401, "Not signed in")
    return {"id": row["id"], "name": row["name"], "role": row["role"], "email": row["email"]}


CurrentUser = Annotated[dict, Depends(current_user)]
