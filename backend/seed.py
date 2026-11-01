
"""Optional demo-data seeding for DUAL EyeQ.

Uses Supabase PostgreSQL and Supabase Storage.

The existing database schema is managed separately.
Seeding is not performed automatically on API startup.
"""

import os
from datetime import datetime, timedelta

from dotenv import load_dotenv

from . import db, service
from .auth import hash_password


DEMO_USER = {
    "name": "Dr. Emily Geller",
    "role": "clinician",
    "email": "emily.geller@example.com",
}

PATIENTS = [
    {
        "full_name": "Maria Lopez",
        "age": 67,
        "sex": "female",
        "phone": "555-0101",
        "email": "maria.lopez@example.com",
    },
    {
        "full_name": "James Chen",
        "age": 58,
        "sex": "male",
        "phone": "555-0102",
        "email": "james.chen@example.com",
    },
    {
        "full_name": "Aisha Patel",
        "age": 45,
        "sex": "female",
        "phone": "555-0103",
        "email": "aisha.patel@example.com",
    },
    {
        "full_name": "David Brown",
        "age": 72,
        "sex": "male",
        "phone": "555-0104",
        "email": "david.brown@example.com",
    },
]

# patient_id, eye, photo, days_ago, skip_reason
SCREENINGS = [
    ("P-003", "right", "4_right.jpg", 10, None),
    ("P-001", "right", "0_right.jpg", 3, None),
    ("P-001", "left", "0_left.jpg", 3, None),
    ("P-002", "right", "1_right.jpg", 1, None),
    (
        "P-002",
        "left",
        None,
        1,
        "Patient could not keep the eye open",
    ),
]

ODIR = (
    service.REPO
    / "data"
    / "Internal"
    / "ODIR-5K"
    / "Training Images"
)


def _ago(days, hour=10):
    """Return an ISO timestamp for a previous date."""
    timestamp = (
        datetime.now().astimezone()
        - timedelta(days=days)
    )

    return timestamp.replace(
        hour=hour,
        minute=15,
        second=0,
        microsecond=0,
    ).isoformat(timespec="seconds")


def seed(conn):
    """Seed demo data only when the users table is empty."""

    existing_user = conn.execute(
        "SELECT id FROM users LIMIT 1"
    ).fetchone()

    if existing_user is not None:
        print("Existing users found. Skipping demo seeding.")
        return

    load_dotenv()

    demo_password = os.environ.get(
        "DUAL_DEMO_PASSWORD"
    )

    if not demo_password:
        raise RuntimeError(
            "DUAL_DEMO_PASSWORD must be configured "
            "before seeding demo data."
        )

    # Create demo clinician.
    user = conn.execute(
        """
        INSERT INTO users (
            name,
            role,
            email,
            password_hash
        )
        VALUES (%s, %s, %s, %s)
        RETURNING id
        """,
        (
            DEMO_USER["name"],
            DEMO_USER["role"],
            DEMO_USER["email"],
            hash_password(demo_password),
        ),
    ).fetchone()

    user_id = user["id"]

    # Create demo patients.
    patient_ids = {}

    for patient in PATIENTS:
        created = service.create_patient(
            conn,
            patient,
            created_at=_ago(30),
        )

        patient_ids[patient["email"]] = created["id"]

    # Map the original demo identifiers to actual IDs.
    demo_patient_ids = {
        "P-001": patient_ids["maria.lopez@example.com"],
        "P-002": patient_ids["james.chen@example.com"],
        "P-003": patient_ids["aisha.patel@example.com"],
        "P-004": patient_ids["david.brown@example.com"],
    }

    # Create demo screening records.
    for patient_id, eye, photo, days, reason in SCREENINGS:
        actual_patient_id = demo_patient_ids[patient_id]
        created_at = _ago(days)

        if photo is None:
            service.create_screening(
                conn,
                user_id,
                actual_patient_id,
                eye,
                skipped=True,
                skip_reason=reason,
                created_at=created_at,
            )
            continue

        image_path = ODIR / photo

        if not image_path.is_file():
            print(
                f"Skipping missing demo image: {photo}"
            )
            continue

        image = service.save_image(
            conn,
            actual_patient_id,
            eye,
            image_path.read_bytes(),
            uploaded_at=created_at,
        )

        if image["quality_status"] != "passed":
            continue

        service.create_screening(
            conn,
            user_id,
            actual_patient_id,
            eye,
            image_id=image["id"],
            created_at=created_at,
        )

    print("Demo data seeded successfully.")


def init():
    """Optionally seed an already initialized PostgreSQL DB."""

    with db.connect_postgres() as conn:
        service.ensure_model_version(conn)
        seed(conn)
        conn.commit()
