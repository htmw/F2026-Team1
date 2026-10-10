"""Demo data, created the first time the back end starts.

Every person here is made up. The photos are ODIR-5K training photos from
data/ (Professor Wong approved using the project datasets in the app).
To start again, stop the server and delete backend/storage/.
"""
import os
from datetime import datetime, timedelta

from . import db, service
from .auth import hash_password

DEMO_USER = {
    "name": "Dr. Emily Geller",
    "role": "clinician",
    "email": "emily.geller@example.com",
    "password": os.environ.get("DUAL_DEMO_PASSWORD", "dual-demo"),
}

PATIENTS = [
    {"full_name": "Maria Lopez", "age": 67, "sex": "female", "phone": "555-0101", "email": "maria.lopez@example.com"},
    {"full_name": "James Chen", "age": 58, "sex": "male", "phone": "555-0102", "email": "james.chen@example.com"},
    {"full_name": "Aisha Patel", "age": 45, "sex": "female", "phone": "555-0103", "email": "aisha.patel@example.com"},
    {"full_name": "David Brown", "age": 72, "sex": "male", "phone": "555-0104", "email": "david.brown@example.com"},
]

# (patient, eye, ODIR photo or None when skipped, days ago, skip reason)
SCREENINGS = [
    ("P-003", "right", "4_right.jpg", 10, None),
    ("P-001", "right", "0_right.jpg", 3, None),
    ("P-001", "left", "0_left.jpg", 3, None),
    ("P-002", "right", "1_right.jpg", 1, None),
    ("P-002", "left", None, 1, "Patient could not keep the eye open"),
]

ODIR = service.REPO / "data/Internal/ODIR-5K/Training Images"


def _ago(days, hour=10):
    t = datetime.now().astimezone() - timedelta(days=days)
    return t.replace(hour=hour, minute=15, second=0, microsecond=0).isoformat(timespec="seconds")


def seed(conn):
    if conn.execute("SELECT 1 FROM users").fetchone():
        return
    conn.execute(
        "INSERT INTO users (name, role, email, password_hash) VALUES (?, ?, ?, ?)",
        (DEMO_USER["name"], DEMO_USER["role"], DEMO_USER["email"], hash_password(DEMO_USER["password"])),
    )
    user_id = conn.execute("SELECT id FROM users").fetchone()[0]
    for p in PATIENTS:
        service.create_patient(conn, p, created_at=_ago(30))
    for patient_id, eye, photo, days, reason in SCREENINGS:
        when = _ago(days)
        if photo is None:
            service.create_screening(conn, user_id, patient_id, eye, skipped=True, skip_reason=reason, created_at=when)
            continue
        path = ODIR / photo
        if not path.exists():
            continue  # data/ missing in this clone: skip the sample screenings
        image = service.save_image(conn, patient_id, eye, path.read_bytes(), uploaded_at=when)
        if image["quality_status"] == "passed":
            service.create_screening(conn, user_id, patient_id, eye, image_id=image["id"], created_at=when)


def init():
    """Create the tables, the model version and the demo data if they are missing."""
    conn = db.connect()
    conn.executescript(db.SCHEMA)
    service.ensure_model_version(conn)
    seed(conn)
    conn.commit()
    conn.close()
