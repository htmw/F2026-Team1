"""Tests for the DUAL API (backend/). Each test gets its own empty storage folder.

Run from the repo folder:  python -m pytest tests/test_api.py
"""
import sqlite3
from pathlib import Path

import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend import db
from backend.main import app
from backend.seed import DEMO_USER

REPO = Path(__file__).resolve().parents[1]
ODIR = REPO / "data/Internal/ODIR-5K/Training Images"


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "STORAGE", tmp_path)
    with TestClient(app) as c:
        r = c.post("/auth/login", json={"email": DEMO_USER["email"], "password": DEMO_USER["password"]})
        assert r.status_code == 200
        yield c


def upload(client, data, patient_id="P-004", eye="right"):
    return client.post("/images", data={"patient_id": patient_id, "eye": eye},
                       files={"file": ("photo.jpg", data, "image/jpeg")})


def fundus():
    return (ODIR / "2_right.jpg").read_bytes()


def test_login_required(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "STORAGE", tmp_path)
    with TestClient(app) as c:
        assert c.get("/patients").status_code == 401
        assert c.post("/auth/login", json={"email": DEMO_USER["email"], "password": "wrong"}).status_code == 401


def test_logout_ends_session(client):
    assert client.get("/auth/me").json()["name"] == DEMO_USER["name"]
    assert client.post("/auth/logout").status_code == 204
    assert client.get("/auth/me").status_code == 401


def test_demo_data(client):
    names = [p["full_name"] for p in client.get("/patients").json()]
    assert names == ["David Brown", "James Chen", "Maria Lopez", "Aisha Patel"]  # by last name
    history = client.get("/screenings").json()
    assert len(history) == 5
    dates = [s["created_at"] for s in history]
    assert dates == sorted(dates, reverse=True)


def test_add_patient_gets_next_id(client):
    assert client.get("/patients/next-id").json() == {"id": "P-005"}
    r = client.post("/patients", json={"full_name": "Test Person", "age": 50, "sex": "other"})
    assert r.status_code == 201 and r.json()["id"] == "P-005"
    assert client.post("/patients", json={"full_name": "", "age": 50, "sex": "other"}).status_code == 422


def test_screen_a_photo(client):
    image = upload(client, fundus()).json()
    assert image["quality_status"] == "passed" and image["file_name"] == "P-004_right.jpg"
    assert client.get(image["url"]).headers["content-type"] == "image/jpeg"
    r = client.post("/screenings", json={"patient_id": "P-004", "eye": "right", "image_id": image["id"]})
    assert r.status_code == 201
    s = r.json()
    assert [c["condition"] for c in s["conditions"]] == ["cataract", "glaucoma"]
    results = [c["result"] for c in s["conditions"]]
    expected = "refer" if {"refer", "uncertain"} & set(results) else "no_concern"
    assert s["overall_result"] == expected
    assert s["model_version"]["is_mock"] is True
    for c in s["conditions"]:
        assert client.get(c["heatmap_url"]).status_code == 200
    # the same photo cannot be screened twice
    again = client.post("/screenings", json={"patient_id": "P-004", "eye": "right", "image_id": image["id"]})
    assert again.status_code == 409


def test_failed_photo_is_never_screened(client):
    screenshot = cv2.imencode(".png", np.full((400, 600, 3), 200, np.uint8))[1].tobytes()
    image = upload(client, screenshot).json()
    assert image["quality_status"] == "failed" and image["quality_reason"] == "not_fundus"
    r = client.post("/screenings", json={"patient_id": "P-004", "eye": "right", "image_id": image["id"]})
    assert r.status_code == 409
    assert client.delete(f"/images/{image['id']}").status_code == 204
    assert upload(client, b"not a photo").json()["quality_reason"] == "unreadable"


def test_photo_must_match_patient_and_eye(client):
    image = upload(client, fundus(), eye="right").json()
    r = client.post("/screenings", json={"patient_id": "P-004", "eye": "left", "image_id": image["id"]})
    assert r.status_code == 409


def test_same_eye_can_be_screened_again(client):
    # follow-up visits and retakes: every screening is kept and the newest one counts
    # (P-001's right eye is already screened in the demo data)
    ids = []
    for photo in ("2_right.jpg", "15_right.jpg"):
        image = upload(client, (ODIR / photo).read_bytes(), patient_id="P-001", eye="right").json()
        r = client.post("/screenings", json={"patient_id": "P-001", "eye": "right", "image_id": image["id"]})
        assert r.status_code == 201
        ids.append(r.json()["id"])
    history = client.get("/screenings", params={"patient": "P-001", "eye": "right"}).json()
    assert len(history) == 3
    assert client.get("/patients/P-001").json()["latest"]["right"]["id"] == ids[-1]


def test_same_photo_uploaded_twice_is_not_screened_twice(client):
    first = upload(client, fundus()).json()
    r = client.post("/screenings", json={"patient_id": "P-004", "eye": "right", "image_id": first["id"]})
    assert r.status_code == 201
    again = upload(client, fundus()).json()
    r2 = client.post("/screenings", json={"patient_id": "P-004", "eye": "right", "image_id": again["id"]})
    assert r2.status_code == 409 and r.json()["id"] in r2.json()["detail"]


def test_database_allows_one_screening_per_photo(client):
    # backs up the check above when two clicks arrive at the same moment
    image = upload(client, fundus()).json()
    assert client.post("/screenings", json={"patient_id": "P-004", "eye": "right", "image_id": image["id"]}).status_code == 201
    conn = db.connect()
    with pytest.raises(sqlite3.IntegrityError):
        conn.execute(
            "INSERT INTO screenings (id, patient_id, image_id, eye, created_at, created_by) "
            "VALUES ('SCR-9999', 'P-004', ?, 'right', '2026-10-10T10:00:00-04:00', 1)",
            (image["id"],),
        )
    conn.close()


def test_skip_eye_and_todays_visit(client):
    assert client.post("/screenings", json={"patient_id": "P-004", "eye": "left", "skipped": True}).status_code == 422
    r = client.post("/screenings", json={"patient_id": "P-004", "eye": "left", "skipped": True,
                                         "skip_reason": "Patient declined"})
    assert r.status_code == 201 and r.json()["overall_result"] is None
    today = client.get("/patients/P-004/screenings", params={"date": "today"}).json()
    assert [(s["eye"], s["skipped"]) for s in today] == [("left", True)]
    detail = client.get("/patients/P-004").json()
    assert detail["latest"]["left"]["skip_reason"] == "Patient declined" and detail["latest"]["right"] is None


def test_history_search(client):
    rows = client.get("/screenings", params={"query": "lopez"}).json()
    assert rows and {r["patient_id"] for r in rows} == {"P-001"}
    assert client.get("/screenings", params={"patient": "P-003"}).json()[0]["eye"] == "right"


def test_exports_are_pdfs(client):
    screening_id = client.get("/screenings", params={"patient": "P-001"}).json()[0]["id"]
    for url in (f"/screenings/{screening_id}/export", "/patients/P-001/export", "/patients/P-004/export"):
        r = client.get(url)
        assert r.status_code == 200 and r.content.startswith(b"%PDF")


def test_unknown_ids_are_404(client):
    for url in ("/patients/P-999", "/screenings/SCR-9999", "/heatmaps/HM-9999", "/images/IMG-9999"):
        assert client.get(url).status_code == 404
