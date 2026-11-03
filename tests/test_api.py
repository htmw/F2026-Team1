
"""Non-destructive integration tests for the DUAL EyeQ API.

Uses the existing development PostgreSQL DATABASE_URL.

Tests create temporary records and remove only those records.
Supabase Storage is mocked entirely in memory.

Run from the repository root:
    python -m pytest tests/test_api.py -v
"""

import asyncio
import io
import uuid

import cv2
import numpy as np
import psycopg
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

    monkeypatch.setattr(service, "storage_upload", upload)
    monkeypatch.setattr(service, "storage_download", download)
    monkeypatch.setattr(service, "storage_delete", delete)

    return objects


# ---------- Temporary Test Data ----------

@pytest.fixture
def demo_record():
    """Create test-only clinician and patient records.

    Does not TRUNCATE tables, reset sequences, or modify
    existing seeded demo records.
    """

    marker = uuid.uuid4().hex

    email = f"test-{marker}@example.invalid"
    password = "Temporary-Test-Password!"
    patient_id = f"TEST-{marker}"

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

    created_patients = []

    try:
        yield {
            "email": email,
            "password": password,
            "patient_id": patient_id,
            "user_id": user_id,
            "created_patients": created_patients,
        }

    finally:
        # Remove dependent records first.
        # Every deletion is scoped to this test's identifiers.

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

            for created_patient_id in created_patients:
                conn.execute(
                    "DELETE FROM patients WHERE id = %s",
                    (created_patient_id,),
                )

            conn.execute(
                "DELETE FROM patients WHERE id = %s",
                (patient_id,),
            )

            conn.execute(
                "DELETE FROM sessions WHERE user_id = %s",
                (user_id,),
            )

            conn.execute(
                """
                DELETE FROM users
                WHERE id = %s AND email = %s
                """,
                (user_id, email),
            )

            conn.commit()


@pytest.fixture
def passed_quality(monkeypatch):
    """Make valid synthetic images pass the quality check."""

    monkeypatch.setattr(
        service.qc,
        "check",
        lambda data: ("passed", None),
    )


@pytest.fixture
def client(storage, demo_record):
    """Create an authenticated API test client."""

    with TestClient(main.app) as api:
        login = api.post(
            "/auth/login",
            json={
                "email": demo_record["email"],
                "password": demo_record["password"],
            },
        )

        assert login.status_code == 200, login.text

        yield api


# ---------- Test Helpers ----------

def sample_jpeg():
    """Create a synthetic JPEG without patient information."""

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

    success, encoded = cv2.imencode(".jpg", image)

    assert success

    return encoded.tobytes()


def upload_photo(
    client,
    patient_id,
    eye="right",
    data=None,
):
    """Upload a synthetic or explicitly provided image."""

    return client.post(
        "/images",
        data={
            "patient_id": patient_id,
            "eye": eye,
        },
        files={
            "file": (
                "test.jpg",
                sample_jpeg() if data is None else data,
                "image/jpeg",
            )
        },
    )


def create_screening(
    client,
    patient_id,
    image_id,
    eye="right",
):
    """Create a screening through the FastAPI endpoint."""

    return client.post(
        "/screenings",
        json={
            "patient_id": patient_id,
            "eye": eye,
            "image_id": image_id,
            "skipped": False,
            "skip_reason": None,
        },
    )


# ---------- Existing Test 1: Full API Workflow ----------

def test_existing_database_api_workflow(
    monkeypatch,
    storage,
    demo_record,
):
    """Test real PostgreSQL, mocked Storage, PDFs and sessions."""

    monkeypatch.setattr(
        service.qc,
        "check",
        lambda data: ("passed", None),
    )

    with TestClient(main.app) as api:
        assert api.get("/auth/me").status_code == 401

        login = api.post(
            "/auth/login",
            json={
                "email": demo_record["email"],
                "password": demo_record["password"],
            },
        )

        assert login.status_code == 200, login.text
        assert login.json()["user"]["id"] == demo_record["user_id"]

        assert api.get("/auth/me").status_code == 200

        patient_id = demo_record["patient_id"]

        response = api.get(f"/patients/{patient_id}")
        assert response.status_code == 200, response.text

        uploaded = upload_photo(api, patient_id, eye="left")
        assert uploaded.status_code == 201, uploaded.text

        image_id = uploaded.json()["id"]

        assert ("fundus-images", f"{image_id}.jpg") in storage
        assert ("processed-images", f"{image_id}_512.jpg") in storage

        assert api.get(f"/images/{image_id}").status_code == 200

        screening = create_screening(
            api,
            patient_id,
            image_id,
            eye="left",
        )

        assert screening.status_code == 201, screening.text

        screening_id = screening.json()["id"]

        assert len(screening.json()["conditions"]) == 2

        assert api.get(
            f"/screenings/{screening_id}"
        ).status_code == 200

        history = api.get(
            "/screenings",
            params={"patient": patient_id},
        )

        assert history.status_code == 200

        # Both PDF exports must be valid.
        for endpoint in (
            f"/screenings/{screening_id}/export",
            f"/patients/{patient_id}/export",
        ):
            pdf = api.get(endpoint)

            assert pdf.status_code == 200, pdf.text
            assert pdf.headers["content-type"].startswith(
                "application/pdf"
            )
            assert pdf.content.startswith(b"%PDF-")

        # Logout invalidates the session.
        assert api.post("/auth/logout").status_code == 204
        assert api.get("/auth/me").status_code == 401


# ---------- Existing Test 2: Partial Upload Cleanup ----------

def test_partial_upload_is_cleaned_up(
    monkeypatch,
    storage,
    demo_record,
):
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

    with TestClient(main.app) as api:
        login = api.post(
            "/auth/login",
            json={
                "email": demo_record["email"],
                "password": demo_record["password"],
            },
        )

        assert login.status_code == 200

        with pytest.raises(
            RuntimeError,
            match="Simulated processed-image",
        ):
            upload_photo(
                api,
                demo_record["patient_id"],
            )

    assert len(attempted) == 2
    assert not storage

    with db.connect_postgres() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS n
            FROM images
            WHERE patient_id = %s
            """,
            (demo_record["patient_id"],),
        ).fetchone()

        assert row["n"] == 0


# ---------- Existing Test 3: Image Commit Failure ----------

def test_image_commit_failure_invokes_cleanup(monkeypatch):
    class FailingConnection:
        rolled_back = False

        def commit(self):
            raise RuntimeError("Simulated commit failure")

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


# ---------- Existing Test 4: Screening Commit Failure ----------

def test_screening_commit_failure_invokes_heatmap_cleanup(
    monkeypatch,
):
    class FakeResult:
        def fetchall(self):
            return [
                {"stored_path": "HM-SIMULATED.jpg"}
            ]

    class FailingConnection:
        rolled_back = False

        def execute(self, sql, params):
            assert "FROM heatmaps" in sql
            return FakeResult()

        def commit(self):
            raise RuntimeError("Simulated commit failure")

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
        ("heatmaps", "HM-SIMULATED.jpg")
    ]


# ---------- Restored Authentication Regression ----------

def test_unauthorized_and_wrong_password(
    demo_record,
    storage,
):
    with TestClient(main.app) as api:
        assert api.get("/patients").status_code == 401
        assert api.get("/auth/me").status_code == 401

        response = api.post(
            "/auth/login",
            json={
                "email": demo_record["email"],
                "password": "incorrect-password",
            },
        )

        assert response.status_code == 401
        assert api.get("/patients").status_code == 401


# ---------- Restored Patient Regression Tests ----------

def test_create_patient_and_read_back(
    client,
    demo_record,
):
    response = client.post(
        "/patients",
        json={
            "full_name": "Temporary Additional Patient",
            "age": 39,
            "sex": "other",
        },
    )

    assert response.status_code == 201, response.text

    patient = response.json()

    # Register for teardown before further assertions.
    demo_record["created_patients"].append(patient["id"])

    assert patient["full_name"] == "Temporary Additional Patient"

    fetched = client.get(f"/patients/{patient['id']}")

    assert fetched.status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {
            "full_name": "",
            "age": 35,
            "sex": "female",
        },
        {
            "full_name": "Invalid Age",
            "age": -1,
            "sex": "male",
        },
        {
            "full_name": "Invalid Sex",
            "age": 35,
            "sex": "unknown",
        },
    ],
)
def test_invalid_patient_input_returns_422(client, payload):
    response = client.post(
        "/patients",
        json=payload,
    )

    assert response.status_code == 422, response.text


def test_patient_search(client, demo_record):
    response = client.get(
        "/patients",
        params={
            "query": demo_record["patient_id"]
        },
    )

    assert response.status_code == 200, response.text

    patient_ids = {
        patient["id"]
        for patient in response.json()
    }

    assert demo_record["patient_id"] in patient_ids


# ---------- Restored Image Regression Tests ----------

def test_image_read_and_delete(
    client,
    demo_record,
    passed_quality,
    storage,
):
    response = upload_photo(
        client,
        demo_record["patient_id"],
    )

    assert response.status_code == 201, response.text

    image = response.json()
    image_id = image["id"]

    assert ("fundus-images", f"{image_id}.jpg") in storage

    assert (
        "processed-images",
        f"{image_id}_512.jpg",
    ) in storage

    for path in (
        image["url"],
        image["original_url"],
    ):
        result = client.get(path)

        assert result.status_code == 200
        assert result.content.startswith(b"\xff\xd8")

    deleted = client.delete(f"/images/{image_id}")

    assert deleted.status_code == 204

    assert ("fundus-images", f"{image_id}.jpg") not in storage

    assert (
        "processed-images",
        f"{image_id}_512.jpg",
    ) not in storage

    assert client.get(
        f"/images/{image_id}"
    ).status_code == 404


def test_unreadable_image_cannot_be_screened(
    client,
    demo_record,
):
    response = upload_photo(
        client,
        demo_record["patient_id"],
        data=b"not a JPEG",
    )

    assert response.status_code == 201, response.text

    image = response.json()

    assert image["quality_status"] == "failed"
    assert image["quality_reason"] == "unreadable"

    blocked = create_screening(
        client,
        demo_record["patient_id"],
        image["id"],
    )

    assert blocked.status_code == 409


def test_missing_patient_image_upload_rejected(
    client,
    passed_quality,
):
    response = upload_photo(
        client,
        "TEST-NONEXISTENT-PATIENT",
    )

    assert response.status_code == 404


# ---------- Restored Screening Regression Tests ----------

def test_same_image_cannot_be_screened_twice(
    client,
    demo_record,
    passed_quality,
):
    response = upload_photo(
        client,
        demo_record["patient_id"],
    )

    assert response.status_code == 201, response.text

    image_id = response.json()["id"]

    first = create_screening(
        client,
        demo_record["patient_id"],
        image_id,
    )

    assert first.status_code == 201

    second = create_screening(
        client,
        demo_record["patient_id"],
        image_id,
    )

    assert second.status_code == 409

    # Images associated with screenings cannot be deleted.
    deleted = client.delete(f"/images/{image_id}")

    assert deleted.status_code == 409


def test_database_enforces_unique_screening_image(
    client,
    demo_record,
    passed_quality,
):
    response = upload_photo(
        client,
        demo_record["patient_id"],
    )

    assert response.status_code == 201, response.text

    image_id = response.json()["id"]

    first = create_screening(
        client,
        demo_record["patient_id"],
        image_id,
    )

    assert first.status_code == 201

    # Bypass FastAPI to verify the database constraint itself.
    with db.connect_postgres() as conn:
        with pytest.raises(
            psycopg.errors.UniqueViolation
        ):
            conn.execute(
                """
                INSERT INTO screenings (
                    id,
                    patient_id,
                    image_id,
                    eye,
                    created_at,
                    created_by
                )
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    "SCR-TEST-" + uuid.uuid4().hex,
                    demo_record["patient_id"],
                    image_id,
                    "right",
                    db.now(),
                    demo_record["user_id"],
                ),
            )

        conn.rollback()


def test_mismatched_eye_is_rejected(
    client,
    demo_record,
    passed_quality,
):
    response = upload_photo(
        client,
        demo_record["patient_id"],
        eye="right",
    )

    assert response.status_code == 201

    blocked = create_screening(
        client,
        demo_record["patient_id"],
        response.json()["id"],
        eye="left",
    )

    assert blocked.status_code == 409


def test_skipped_screening_validation(
    client,
    demo_record,
):
    patient_id = demo_record["patient_id"]

    missing_reason = client.post(
        "/screenings",
        json={
            "patient_id": patient_id,
            "eye": "left",
            "skipped": True,
        },
    )

    assert missing_reason.status_code == 422

    result = client.post(
        "/screenings",
        json={
            "patient_id": patient_id,
            "eye": "left",
            "skipped": True,
            "skip_reason": "Patient declined",
        },
    )

    assert result.status_code == 201, result.text

    screening = result.json()

    assert screening["skipped"] is True
    assert screening["overall_result"] is None

    history = client.get(
        "/screenings",
        params={"patient": patient_id},
    )

    assert history.status_code == 200

    screening_ids = {
        item["id"]
        for item in history.json()
    }

    assert screening["id"] in screening_ids


def test_second_image_same_photo_rejected_after_screening(
    client,
    demo_record,
    passed_quality,
):
    """Reject duplicate photo content for the same eye."""

    photo = sample_jpeg()
    patient_id = demo_record["patient_id"]

    first = upload_photo(
        client,
        patient_id,
        data=photo,
    )

    assert first.status_code == 201, first.text

    first_screening = create_screening(
        client,
        patient_id,
        first.json()["id"],
    )

    assert first_screening.status_code == 201

    second = upload_photo(
        client,
        patient_id,
        data=photo,
    )

    assert second.status_code == 201, second.text

    duplicate = create_screening(
        client,
        patient_id,
        second.json()["id"],
    )

    assert duplicate.status_code == 409


# ---------- Restored Unknown-ID Tests ----------

@pytest.mark.parametrize(
    "method,path",
    [
        ("get", "/patients/TEST-UNKNOWN-ID"),
        ("get", "/screenings/SCR-UNKNOWN-ID"),
        ("get", "/images/IMG-UNKNOWN-ID"),
        ("get", "/heatmaps/HM-UNKNOWN-ID"),
    ],
)
def test_unknown_ids_return_404(
    client,
    method,
    path,
):
    response = getattr(client, method)(path)

    assert response.status_code == 404, response.text
