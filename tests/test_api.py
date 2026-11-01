
"""Non-destructive EyeQ API tests using development PostgreSQL.

Creates unique test records and deletes only those records.
Supabase Storage is mocked and never accessed by these tests.

Run:
    python -m pytest tests/test_api.py -v
"""

import asyncio
import io
import uuid

import cv2
import numpy as np
import pytest

from fastapi import UploadFile
from fastapi.testclient import TestClient

from backend import auth, db, main, service
from backend.schemas import ScreeningIn


# ---------- Mock Supabase Storage ----------

@pytest.fixture
def storage(monkeypatch):
    """Replace Supabase Storage with an in-memory dictionary."""

    objects = {}

    def upload(bucket, path, content):
        objects[(bucket, path)] = bytes(content)

    def download(bucket, path):
        key = (bucket, path)

        if key not in objects:
            raise AssertionError(
                f"Missing mocked Storage object: {bucket}/{path}"
            )

        return objects[key]

    def delete(bucket, paths):
        for path in paths:
            objects.pop((bucket, path), None)

    monkeypatch.setattr(
        service,
        "storage_upload",
        upload,
    )

    monkeypatch.setattr(
        service,
        "storage_download",
        download,
    )

    monkeypatch.setattr(
        service,
        "storage_delete",
        delete,
    )

    return objects


# ---------- Temporary Test Records ----------

@pytest.fixture
def demo_record():
    """Create a temporary clinician and patient.

    Uses the existing development PostgreSQL database.

    Does NOT:
    - TRUNCATE any tables
    - Reset sequences
    - Delete demo patients
    - Delete existing clinicians
    - Access real Supabase Storage
    """

    marker = uuid.uuid4().hex

    email = f"test-{marker}@example.invalid"
    password = "Temporary-Test-Password!"

    patient_id = f"TEST-{marker}"
    user_id = None

    # Create test-only records.
    with db.connect_postgres() as conn:
        row = conn.execute(
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
                "Isolated Test Clinician",
                "clinician",
                email,
                auth.hash_password(password),
            ),
        ).fetchone()

        user_id = row["id"]

        conn.execute(
            """
            INSERT INTO patients (
                id,
                full_name,
                age,
                sex,
                created_at
            )
            VALUES (%s, %s, %s, %s, %s)
            """,
            (
                patient_id,
                "Isolated Test Patient",
                42,
                "female",
                db.now(),
            ),
        )

        conn.commit()

    try:
        yield {
            "email": email,
            "password": password,
            "patient_id": patient_id,
            "user_id": user_id,
        }

    finally:
        # Delete only rows owned by this test fixture.
        # Foreign-key dependents are removed first.

        with db.connect_postgres() as conn:
            conn.execute(
                """
                DELETE FROM heatmaps
                WHERE condition_result_id IN (
                    SELECT cr.id
                    FROM condition_results cr
                    JOIN screenings s
                        ON s.id = cr.screening_id
                    WHERE s.patient_id = %s
                )
                """,
                (patient_id,),
            )

            conn.execute(
                """
                DELETE FROM condition_results
                WHERE screening_id IN (
                    SELECT id
                    FROM screenings
                    WHERE patient_id = %s
                )
                """,
                (patient_id,),
            )

            conn.execute(
                """
                DELETE FROM screenings
                WHERE patient_id = %s
                """,
                (patient_id,),
            )

            conn.execute(
                """
                DELETE FROM images
                WHERE patient_id = %s
                """,
                (patient_id,),
            )

            conn.execute(
                """
                DELETE FROM patients
                WHERE id = %s
                """,
                (patient_id,),
            )

            conn.execute(
                """
                DELETE FROM sessions
                WHERE user_id = %s
                """,
                (user_id,),
            )

            conn.execute(
                """
                DELETE FROM users
                WHERE id = %s
                AND email = %s
                """,
                (user_id, email),
            )

            conn.commit()


# ---------- Test Image ----------

def sample_jpeg():
    """Generate a synthetic JPEG image."""

    image = np.zeros(
        (512, 512, 3),
        dtype=np.uint8,
    )

    cv2.circle(
        image,
        (256, 256),
        220,
        (75, 130, 175),
        thickness=-1,
    )

    cv2.circle(
        image,
        (190, 235),
        38,
        (170, 220, 225),
        thickness=-1,
    )

    success, encoded = cv2.imencode(
        ".jpg",
        image,
    )

    assert success

    return encoded.tobytes()


# ---------- Full API Workflow ----------

def test_existing_database_api_workflow(
    monkeypatch,
    storage,
    demo_record,
):
    """Test real PostgreSQL with mocked Storage.

    Covers:
    - Login
    - Session verification
    - Patient retrieval
    - Image upload
    - Image retrieval
    - Screening creation
    - Screening history
    - Screening PDF
    - Patient PDF
    - Logout
    """

    monkeypatch.setattr(
        service.qc,
        "check",
        lambda data: ("passed", None),
    )

    with TestClient(main.app) as client:

        # Unauthenticated requests must fail.
        response = client.get("/auth/me")

        assert response.status_code == 401

        # Login.
        login = client.post(
            "/auth/login",
            json={
                "email": demo_record["email"],
                "password": demo_record["password"],
            },
        )

        assert login.status_code == 200, login.text

        assert (
            login.json()["user"]["id"]
            == demo_record["user_id"]
        )

        # Session should be valid.
        response = client.get("/auth/me")

        assert response.status_code == 200

        # Retrieve temporary patient.
        response = client.get(
            f"/patients/{demo_record['patient_id']}"
        )

        assert response.status_code == 200, response.text

        # Upload an image.
        upload = client.post(
            "/images",
            data={
                "patient_id": demo_record["patient_id"],
                "eye": "left",
            },
            files={
                "file": (
                    "test.jpg",
                    sample_jpeg(),
                    "image/jpeg",
                )
            },
        )

        assert upload.status_code == 201, upload.text

        image_id = upload.json()["id"]

        # Both images should exist in mocked Storage.
        assert (
            "fundus-images",
            f"{image_id}.jpg",
        ) in storage

        assert (
            "processed-images",
            f"{image_id}_512.jpg",
        ) in storage

        # Retrieve uploaded image.
        response = client.get(
            f"/images/{image_id}"
        )

        assert response.status_code == 200

        assert response.headers[
            "content-type"
        ].startswith("image/jpeg")

        # Create screening.
        screening = client.post(
            "/screenings",
            json={
                "patient_id": demo_record["patient_id"],
                "eye": "left",
                "image_id": image_id,
                "skipped": False,
                "skip_reason": None,
            },
        )

        assert screening.status_code == 201, screening.text

        screening_id = screening.json()["id"]

        # Cataract and glaucoma should be present.
        assert len(
            screening.json()["conditions"]
        ) == 2

        # Retrieve screening.
        response = client.get(
            f"/screenings/{screening_id}"
        )

        assert response.status_code == 200

        # Retrieve patient details.
        response = client.get(
            f"/patients/{demo_record['patient_id']}"
        )

        assert response.status_code == 200

        # Screening history.
        response = client.get(
            "/screenings",
            params={
                "patient": demo_record["patient_id"]
            },
        )

        assert response.status_code == 200

        # Verify screening PDF and patient dossier PDF.
        pdf_endpoints = (
            f"/screenings/{screening_id}/export",
            f"/patients/{demo_record['patient_id']}/export",
        )

        for endpoint in pdf_endpoints:
            response = client.get(endpoint)

            assert response.status_code == 200, response.text

            assert response.headers[
                "content-type"
            ].startswith("application/pdf")

            assert response.content.startswith(b"%PDF-")

        # Logout.
        response = client.post("/auth/logout")

        assert response.status_code == 204

        # Previous session should no longer work.
        response = client.get("/auth/me")

        assert response.status_code == 401


# ---------- Partial Upload Failure ----------

def test_partial_upload_is_cleaned_up(
    monkeypatch,
    storage,
    demo_record,
):
    """If the processed upload fails, clean both attempts."""

    monkeypatch.setattr(
        service.qc,
        "check",
        lambda data: ("passed", None),
    )

    attempted = []

    def fail_second_upload(bucket, path, content):
        attempted.append((bucket, path))

        if bucket == "processed-images":
            raise RuntimeError(
                "Simulated processed-image upload failure"
            )

        storage[(bucket, path)] = bytes(content)

    monkeypatch.setattr(
        service,
        "storage_upload",
        fail_second_upload,
    )

    with TestClient(main.app) as client:
        login = client.post(
            "/auth/login",
            json={
                "email": demo_record["email"],
                "password": demo_record["password"],
            },
        )

        assert login.status_code == 200, login.text

        with pytest.raises(
            RuntimeError,
            match="Simulated processed-image",
        ):
            client.post(
                "/images",
                data={
                    "patient_id": demo_record["patient_id"],
                    "eye": "right",
                },
                files={
                    "file": (
                        "test.jpg",
                        sample_jpeg(),
                        "image/jpeg",
                    )
                },
            )

    assert len(attempted) == 2

    # The original image should have been removed.
    assert not storage

    # No image record should have been committed.
    with db.connect_postgres() as conn:
        result = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM images
            WHERE patient_id = %s
            """,
            (demo_record["patient_id"],),
        ).fetchone()

        assert result["n"] == 0


# ---------- Image Commit Failure ----------

def test_image_commit_failure_invokes_cleanup(
    monkeypatch,
):
    """Simulate a PostgreSQL commit failure without
    touching the actual development database.
    """

    class FailingConnection:
        rolled_back = False

        def commit(self):
            raise RuntimeError(
                "Simulated commit failure"
            )

        def rollback(self):
            self.rolled_back = True

    conn = FailingConnection()

    removed = []

    monkeypatch.setattr(
        service,
        "save_image",
        lambda *args, **kwargs: {
            "id": "IMG-SIMULATED",
            "url": "/images/IMG-SIMULATED",
        },
    )

    monkeypatch.setattr(
        service,
        "cleanup_storage_objects",
        lambda objects: removed.extend(objects),
    )

    upload = UploadFile(
        filename="fake.jpg",
        file=io.BytesIO(b"image"),
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated commit failure",
    ):
        asyncio.run(
            main.upload_image(
                conn=conn,
                user={"id": 1},
                file=upload,
                patient_id="SIMULATED",
                eye="left",
            )
        )

    assert conn.rolled_back

    assert (
        "fundus-images",
        "IMG-SIMULATED.jpg",
    ) in removed

    assert (
        "processed-images",
        "IMG-SIMULATED_512.jpg",
    ) in removed


# ---------- Screening Commit Failure ----------

def test_screening_commit_failure_invokes_heatmap_cleanup(
    monkeypatch,
):
    """Simulate failed screening commit without
    writing to the real PostgreSQL database.
    """

    class FakeResult:
        def fetchall(self):
            return [
                {
                    "stored_path": "HM-SIMULATED.jpg"
                }
            ]

    class FailingConnection:
        rolled_back = False

        def execute(self, sql, params):
            assert "FROM heatmaps" in sql

            return FakeResult()

        def commit(self):
            raise RuntimeError(
                "Simulated commit failure"
            )

        def rollback(self):
            self.rolled_back = True

    conn = FailingConnection()

    removed = []

    monkeypatch.setattr(
        service,
        "create_screening",
        lambda *args, **kwargs: "SCR-SIMULATED",
    )

    monkeypatch.setattr(
        service,
        "cleanup_storage_objects",
        lambda objects: removed.extend(objects),
    )

    body = ScreeningIn(
        patient_id="SIMULATED",
        eye="left",
        image_id="IMG-SIMULATED",
    )

    with pytest.raises(
        RuntimeError,
        match="Simulated commit failure",
    ):
        main.screen(
            body=body,
            conn=conn,
            user={"id": 1},
        )

    assert conn.rolled_back

    assert removed == [
        (
            "heatmaps",
            "HM-SIMULATED.jpg",
        )
    ]
