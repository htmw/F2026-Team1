
"""Integration tests for the DUAL FastAPI backend.

Uses a dedicated PostgreSQL test database.

Supabase Storage is mocked in memory. No files are
uploaded to the real Supabase Storage buckets.

IMPORTANT:
These tests reset application tables in TEST_DATABASE_URL.
Never point TEST_DATABASE_URL at a shared or production DB.

Required environment variables:
    TEST_DATABASE_URL
    DUAL_ALLOW_TEST_DB_RESET=YES

Run from the repository root:
    python -m pytest tests/test_api.py -v

The test PostgreSQL database must have the DUAL
schema installed before running these tests.
"""

import os
from pathlib import Path
from urllib.parse import urlsplit
from uuid import uuid4

import cv2
import numpy as np
import psycopg
import pytest

from dotenv import dotenv_values
from fastapi.testclient import TestClient
from psycopg.rows import dict_row


REPO = Path(__file__).resolve().parents[1]
ODIR = (
    REPO
    / "data"
    / "Internal"
    / "ODIR-5K"
    / "Training Images"
)


# ---------- Test database safety ----------

TEST_DATABASE_URL = os.environ.get(
    "TEST_DATABASE_URL",
    "",
).strip()


def _database_identity(url):
    """Identify a PostgreSQL database without its password."""

    parsed = urlsplit(url)

    return (
        parsed.hostname,
        parsed.port or 5432,
        parsed.path.strip("/"),
    )


def _validate_test_database():
    """Prevent tests from modifying the live database."""

    if not TEST_DATABASE_URL:
        pytest.skip(
            "TEST_DATABASE_URL is not configured.",
            allow_module_level=True,
        )

    if os.environ.get(
        "DUAL_ALLOW_TEST_DB_RESET"
    ) != "YES":
        pytest.skip(
            "Set DUAL_ALLOW_TEST_DB_RESET=YES "
            "to allow resetting the dedicated test DB.",
            allow_module_level=True,
        )

    if not TEST_DATABASE_URL.startswith(
        ("postgresql://", "postgres://")
    ):
        pytest.fail(
            "TEST_DATABASE_URL must be a PostgreSQL URL.",
            pytrace=False,
        )

    if not _database_identity(TEST_DATABASE_URL)[2]:
        pytest.fail(
            "TEST_DATABASE_URL must name a database.",
            pytrace=False,
        )

    live_urls = [
        os.environ.get("DATABASE_URL"),
    ]

    for env_name in (".env", ".env.local"):
        env_path = REPO / env_name

        if env_path.exists():
            live_urls.append(
                dotenv_values(env_path).get(
                    "DATABASE_URL"
                )
            )

    for live_url in live_urls:
        if not live_url:
            continue

        if _database_identity(TEST_DATABASE_URL) == (
            _database_identity(live_url)
        ):
            pytest.fail(
                "Test DB matches the live database. "
                "Use a separate PostgreSQL database.",
                pytrace=False,
            )

    db_name = _database_identity(
        TEST_DATABASE_URL
    )[2].lower()

    if "test" not in db_name:
        pytest.fail(
            "The test database name must contain "
            "'test' as an additional safety check.",
            pytrace=False,
        )


_validate_test_database()

# Protect the backend from accidentally loading
# the live DATABASE_URL from a dotenv file.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL


from backend import db, service  # noqa: E402
from backend.auth import hash_password  # noqa: E402
from backend.main import app  # noqa: E402


# ---------- Test data ----------

TEST_PASSWORD = "EyeQ-Test-Password-123!"

TEST_USER = {
    "name": "EyeQ Test Clinician",
    "role": "clinician",
    "email": "eyeq-test@example.invalid",
}

TEST_PATIENT = {
    "full_name": "Test Patient",
    "age": 50,
    "sex": "other",
    "phone": None,
    "email": "patient@example.invalid",
}


def postgres_connection():
    """Open a dictionary-row connection to the test DB."""

    return psycopg.connect(
        TEST_DATABASE_URL,
        row_factory=dict_row,
        connect_timeout=10,
    )


def reset_test_database():
    """Clear application records in the disposable test DB."""

    with postgres_connection() as conn:
        conn.execute(
            """
            TRUNCATE TABLE
                heatmaps,
                condition_results,
                screenings,
                images,
                sessions,
                patients,
                model_versions,
                users
            RESTART IDENTITY CASCADE
            """
        )
        conn.commit()


def create_test_user(conn):
    """Create a clinician without using production seed data."""

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
            TEST_USER["name"],
            TEST_USER["role"],
            TEST_USER["email"],
            hash_password(TEST_PASSWORD),
        ),
    ).fetchone()

    return row["id"]


def create_test_patient(conn):
    """Create a fresh patient in PostgreSQL."""

    return service.create_patient(
        conn,
        TEST_PATIENT,
    )["id"]


# ---------- Mock Supabase Storage ----------

@pytest.fixture
def mock_storage(monkeypatch):
    """Mock Supabase Storage in memory for each test."""

    objects = {}

    def upload(bucket, path, content):
        key = (bucket, path)

        if key in objects:
            raise RuntimeError(
                f"Storage object already exists: {key}"
            )

        objects[key] = bytes(content)

    def download(bucket, path):
        key = (bucket, path)

        if key not in objects:
            from fastapi import HTTPException

            raise HTTPException(
                404,
                "Stored image not found",
            )

        return objects[key]

    def delete(bucket, paths):
        for path in paths:
            objects.pop(
                (bucket, path),
                None,
            )

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


# ---------- Application fixtures ----------

@pytest.fixture
def test_data():
    """Create isolated test records in the dedicated DB."""

    reset_test_database()

    with postgres_connection() as conn:
        user_id = create_test_user(conn)
        patient_id = create_test_patient(conn)
        conn.commit()

    yield {
        "user_id": user_id,
        "patient_id": patient_id,
    }

    reset_test_database()


@pytest.fixture
def anonymous_client(test_data, mock_storage):
    """Create an unauthenticated FastAPI test client."""

    with TestClient(app) as client:
        yield client


@pytest.fixture
def client(anonymous_client):
    """Create an authenticated clinician test client."""

    response = anonymous_client.post(
        "/auth/login",
        json={
            "email": TEST_USER["email"],
            "password": TEST_PASSWORD,
        },
    )

    assert response.status_code == 200, response.text

    return anonymous_client


@pytest.fixture
def fundus():
    """Load a real sample fundus photograph."""

    path = ODIR / "2_right.jpg"

    if not path.is_file():
        pytest.skip(
            "ODIR sample image 2_right.jpg is unavailable."
        )

    return path.read_bytes()


def upload(
    client,
    data,
    patient_id,
    eye="right",
):
    """Send a multipart image upload."""

    return client.post(
        "/images",
        data={
            "patient_id": patient_id,
            "eye": eye,
        },
        files={
            "file": (
                "photo.jpg",
                data,
                "image/jpeg",
            )
        },
    )


def screen(
    client,
    patient_id,
    image_id,
    eye="right",
):
    """Create a screening through the API."""

    return client.post(
        "/screenings",
        json={
            "patient_id": patient_id,
            "eye": eye,
            "image_id": image_id,
        },
    )


# ---------- Authentication tests ----------

def test_login_required(anonymous_client):
    response = anonymous_client.get("/patients")

    assert response.status_code == 401

    response = anonymous_client.post(
        "/auth/login",
        json={
            "email": TEST_USER["email"],
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401


def test_login_and_current_user(client):
    response = client.get("/auth/me")

    assert response.status_code == 200
    assert response.json()["email"] == TEST_USER["email"]


def test_logout_ends_session(client):
    assert client.get("/auth/me").status_code == 200

    assert client.post(
        "/auth/logout"
    ).status_code == 204

    assert client.get(
        "/auth/me"
    ).status_code == 401


# ---------- Patient tests ----------

def test_create_patient(client):
    response = client.post(
        "/patients",
        json={
            "full_name": "Second Test Patient",
            "age": 42,
            "sex": "female",
        },
    )

    assert response.status_code == 201

    patient = response.json()

    assert patient["full_name"] == (
        "Second Test Patient"
    )

    assert patient["id"].startswith("P-")

    fetched = client.get(
        f"/patients/{patient['id']}"
    )

    assert fetched.status_code == 200


def test_invalid_patient_is_rejected(client):
    response = client.post(
        "/patients",
        json={
            "full_name": "",
            "age": 50,
            "sex": "other",
        },
    )

    assert response.status_code == 422


def test_patient_search(client, test_data):
    response = client.get(
        "/patients",
        params={"query": "Test Patient"},
    )

    assert response.status_code == 200

    ids = {
        patient["id"]
        for patient in response.json()
    }

    assert test_data["patient_id"] in ids


# ---------- Image upload tests ----------

def test_upload_image(
    client,
    test_data,
    fundus,
    mock_storage,
):
    response = upload(
        client,
        fundus,
        test_data["patient_id"],
    )

    assert response.status_code == 201, response.text

    image = response.json()

    assert image["quality_status"] == "passed"

    assert (
        "fundus-images",
        f"{image['id']}.jpg",
    ) in mock_storage

    assert (
        "processed-images",
        f"{image['id']}_512.jpg",
    ) in mock_storage

    original = client.get(
        image["original_url"]
    )

    processed = client.get(
        image["url"]
    )

    assert original.status_code == 200
    assert processed.status_code == 200

    assert original.content.startswith(b"\xff\xd8")
    assert processed.content.startswith(b"\xff\xd8")


def test_invalid_image_is_rejected_from_screening(
    client,
    test_data,
):
    data = b"not an image"

    response = upload(
        client,
        data,
        test_data["patient_id"],
    )

    assert response.status_code == 201

    image = response.json()

    assert image["quality_status"] == "failed"
    assert image["quality_reason"] == "unreadable"

    screening = screen(
        client,
        test_data["patient_id"],
        image["id"],
    )

    assert screening.status_code == 409


def test_upload_failure_cleans_original(
    client,
    test_data,
    fundus,
    mock_storage,
    monkeypatch,
):
    """A processed-image failure removes the original."""

    original_upload = service.storage_upload

    def failing_upload(bucket, path, content):
        if bucket == "processed-images":
            raise RuntimeError(
                "Simulated processed-image failure"
            )

        return original_upload(
            bucket,
            path,
            content,
        )

    monkeypatch.setattr(
        service,
        "storage_upload",
        failing_upload,
    )

    # TestClient normally raises uncaught server
    # exceptions into the test process.
    with pytest.raises(RuntimeError):
        upload(
            client,
            fundus,
            test_data["patient_id"],
        )

    assert mock_storage == {}

    with postgres_connection() as conn:
        count = conn.execute(
            "SELECT COUNT(*) AS count FROM images"
        ).fetchone()["count"]

    assert count == 0


def test_database_failure_cleans_uploaded_images(
    test_data,
    fundus,
    mock_storage,
    monkeypatch,
):
    """Failed metadata insertion cleans Storage objects."""

    original_get_image_row = service.get_image_row

    def failing_get_image_row(conn, image_id):
        raise RuntimeError(
            "Simulated metadata retrieval failure"
        )

    # A failure after an insert must still trigger cleanup.
    monkeypatch.setattr(
        service,
        "get_image_row",
        failing_get_image_row,
    )

    with postgres_connection() as conn:
        with pytest.raises(RuntimeError):
            service.save_image(
                conn,
                test_data["patient_id"],
                "right",
                fundus,
            )

        conn.rollback()

    assert mock_storage == {}

    monkeypatch.setattr(
        service,
        "get_image_row",
        original_get_image_row,
    )


def test_delete_unscreened_image(
    client,
    test_data,
    fundus,
    mock_storage,
):
    response = upload(
        client,
        fundus,
        test_data["patient_id"],
    )

    assert response.status_code == 201

    image_id = response.json()["id"]

    result = client.delete(
        f"/images/{image_id}"
    )

    assert result.status_code == 204

    assert (
        "fundus-images",
        f"{image_id}.jpg",
    ) not in mock_storage

    assert (
        "processed-images",
        f"{image_id}_512.jpg",
    ) not in mock_storage


# ---------- Screening tests ----------

def test_screen_photo(
    client,
    test_data,
    fundus,
):
    uploaded = upload(
        client,
        fundus,
        test_data["patient_id"],
    )

    assert uploaded.status_code == 201

    image_id = uploaded.json()["id"]

    response = screen(
        client,
        test_data["patient_id"],
        image_id,
    )

    assert response.status_code == 201, response.text

    screening = response.json()

    assert screening["image"]["id"] == image_id

    conditions = {
        item["condition"]
        for item in screening["conditions"]
    }

    assert conditions == {
        "cataract",
        "glaucoma",
    }

    assert screening["model_version"]["is_mock"] is True

    assert screening["overall_result"] in {
        "no_concern",
        "refer",
    }

    for condition in screening["conditions"]:
        response = client.get(
            condition["heatmap_url"]
        )

        assert response.status_code == 200


def test_same_image_cannot_be_screened_twice(
    client,
    test_data,
    fundus,
):
    uploaded = upload(
        client,
        fundus,
        test_data["patient_id"],
    )

    assert uploaded.status_code == 201

    image_id = uploaded.json()["id"]

    first = screen(
        client,
        test_data["patient_id"],
        image_id,
    )

    assert first.status_code == 201

    second = screen(
        client,
        test_data["patient_id"],
        image_id,
    )

    assert second.status_code == 409


def test_database_enforces_unique_screening_image(
    client,
    test_data,
    fundus,
):
    uploaded = upload(
        client,
        fundus,
        test_data["patient_id"],
    )

    assert uploaded.status_code == 201

    image_id = uploaded.json()["id"]

    first = screen(
        client,
        test_data["patient_id"],
        image_id,
    )

    assert first.status_code == 201

    with postgres_connection() as conn:
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
                VALUES (
                    %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    f"SCR-{uuid4().hex[:12]}",
                    test_data["patient_id"],
                    image_id,
                    "right",
                    db.now(),
                    test_data["user_id"],
                ),
            )

        conn.rollback()


def test_skip_screening(
    client,
    test_data,
):
    response = client.post(
        "/screenings",
        json={
            "patient_id": test_data["patient_id"],
            "eye": "left",
            "skipped": True,
        },
    )

    assert response.status_code == 422

    response = client.post(
        "/screenings",
        json={
            "patient_id": test_data["patient_id"],
            "eye": "left",
            "skipped": True,
            "skip_reason": "Patient declined",
        },
    )

    assert response.status_code == 201

    screening = response.json()

    assert screening["skipped"] is True
    assert screening["overall_result"] is None


def test_screening_history(
    client,
    test_data,
):
    response = client.post(
        "/screenings",
        json={
            "patient_id": test_data["patient_id"],
            "eye": "left",
            "skipped": True,
            "skip_reason": "Unable to complete",
        },
    )

    assert response.status_code == 201

    history = client.get(
        "/screenings",
        params={
            "patient": test_data["patient_id"],
        },
    )

    assert history.status_code == 200
    assert len(history.json()) == 1


# ---------- PDF export tests ----------

def test_screening_pdf_export(
    client,
    test_data,
    fundus,
):
    uploaded = upload(
        client,
        fundus,
        test_data["patient_id"],
    )

    assert uploaded.status_code == 201

    screening = screen(
        client,
        test_data["patient_id"],
        uploaded.json()["id"],
    )

    assert screening.status_code == 201

    screening_id = screening.json()["id"]

    response = client.get(
        f"/screenings/{screening_id}/export"
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")

    assert response.headers["content-type"].startswith(
        "application/pdf"
    )

    assert len(response.content) > 100


def test_patient_pdf_export(
    client,
    test_data,
):
    response = client.get(
        f"/patients/{test_data['patient_id']}/export"
    )

    assert response.status_code == 200
    assert response.content.startswith(b"%PDF")

    assert response.headers["content-type"].startswith(
        "application/pdf"
    )


# ---------- Error handling ----------

def test_unknown_ids_return_404(client):
    for url in (
        "/patients/P-999999",
        "/screenings/SCR-999999",
        "/heatmaps/HM-999999",
        "/images/IMG-999999",
    ):
        response = client.get(url)
        assert response.status_code == 404
