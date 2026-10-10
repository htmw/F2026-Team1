"""What the API does, kept apart from HTTP so seed.py and the tests can reuse it.

Every function takes an open SQLite connection and returns plain dicts shaped
like the models in schemas.py.
"""
import json
import sys
from pathlib import Path

import cv2
import numpy as np
from fastapi import HTTPException

from . import db
from . import mock_model as model
from .results import condition_result, flag_reason, overall_result

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import quality_check as qc  # noqa: E402
from preprocess_images import TARGET_SIZE, crop_fundus  # noqa: E402

EYES = ("right", "left")


# ---------- model version ----------

def ensure_model_version(conn):
    conn.execute(
        "INSERT OR IGNORE INTO model_versions VALUES (?, ?, ?, ?, ?, ?)",
        (model.VERSION, json.dumps(model.THRESHOLDS), model.UNCERTAIN_MARGIN, None, 1, db.now()),
    )


def model_version(conn, version_id=model.VERSION):
    row = conn.execute("SELECT * FROM model_versions WHERE id = ?", (version_id,)).fetchone()
    return {
        "id": row["id"],
        "thresholds": json.loads(row["thresholds"]),
        "uncertain_margin": row["uncertain_margin"],
        "commit": row["commit_hash"],
        "is_mock": bool(row["is_mock"]),
        "released_at": row["released_at"],
    }


# ---------- patients ----------

def get_patient(conn, patient_id):
    row = conn.execute("SELECT * FROM patients WHERE id = ?", (patient_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"Patient {patient_id} not found")
    return dict(row)


def list_patients(conn, query=None):
    sql, args = "SELECT * FROM patients", ()
    if query:
        sql += " WHERE full_name LIKE ? OR id LIKE ?"
        args = (f"%{query}%", f"%{query}%")
    rows = [dict(r) for r in conn.execute(sql, args)]
    # sorted by last name, as on the Upload search
    return sorted(rows, key=lambda p: (p["full_name"].split()[-1].lower(), p["full_name"].lower()))


def create_patient(conn, data, created_at=None):
    patient_id = db.next_id(conn, "patients", "P-", 3)
    conn.execute(
        "INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?)",
        (patient_id, data["full_name"].strip(), data["age"], data["sex"],
         data.get("phone"), data.get("email"), created_at or db.now()),
    )
    return get_patient(conn, patient_id)


# ---------- images ----------

def image_out(row):
    has_file = row["stored_path"] is not None
    return {
        "id": row["id"],
        "patient_id": row["patient_id"],
        "eye": row["eye"],
        "file_name": row["file_name"],
        "width": row["width"],
        "height": row["height"],
        "quality_status": row["quality_status"],
        "quality_reason": row["quality_reason"],
        "quality_message": qc.REASONS.get(row["quality_reason"]),
        "uploaded_at": row["uploaded_at"],
        "url": f"/images/{row['id']}" if has_file else None,
        "original_url": f"/images/{row['id']}/original" if has_file else None,
    }


def get_image_row(conn, image_id):
    row = conn.execute("SELECT * FROM images WHERE id = ?", (image_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"Image {image_id} not found")
    return row


def save_image(conn, patient_id, eye, data, uploaded_at=None):
    """Store an upload and run the quality check on it straight away."""
    get_patient(conn, patient_id)
    status, reason = qc.check(data)
    image_id = db.next_id(conn, "images", "IMG-", 4)
    stored_path = width = height = None
    if reason != "unreadable":
        img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
        height, width = img.shape[:2]
        folder = db.STORAGE / "images"
        folder.mkdir(parents=True, exist_ok=True)
        cv2.imwrite(str(folder / f"{image_id}.jpg"), img)
        # the 512 x 512 copy shown on Results, made by the same shared preprocessing as training
        small = cv2.resize(crop_fundus(img), (TARGET_SIZE, TARGET_SIZE), interpolation=cv2.INTER_AREA)
        cv2.imwrite(str(folder / f"{image_id}_512.jpg"), small)
        stored_path = f"images/{image_id}.jpg"
    conn.execute(
        "INSERT INTO images VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (image_id, patient_id, eye, f"{patient_id}_{eye}.jpg", stored_path, width, height,
         status, reason, uploaded_at or db.now()),
    )
    return image_out(get_image_row(conn, image_id))


def image_file(conn, image_id, original=False):
    row = get_image_row(conn, image_id)
    if row["stored_path"] is None:
        raise HTTPException(404, "This upload could not be read, so there is no photo to show")
    return db.STORAGE / "images" / (f"{image_id}.jpg" if original else f"{image_id}_512.jpg")


def delete_image(conn, image_id):
    """Retake / Upload different photo: discard an image that was never screened."""
    get_image_row(conn, image_id)
    if conn.execute("SELECT 1 FROM screenings WHERE image_id = ?", (image_id,)).fetchone():
        raise HTTPException(409, "This photo has been screened and is part of the record")
    conn.execute("DELETE FROM images WHERE id = ?", (image_id,))
    for name in (f"{image_id}.jpg", f"{image_id}_512.jpg"):
        (db.STORAGE / "images" / name).unlink(missing_ok=True)


def heatmap_file(conn, heatmap_id):
    row = conn.execute("SELECT stored_path FROM heatmaps WHERE id = ?", (heatmap_id,)).fetchone()
    if row is None:
        raise HTTPException(404, f"Heatmap {heatmap_id} not found")
    return db.STORAGE / row["stored_path"]


# ---------- screenings ----------

def create_screening(conn, user_id, patient_id, eye, image_id=None, skipped=False,
                     skip_reason=None, created_at=None):
    """Run the model on one passed photo, or record a skipped eye. Returns the new screening ID."""
    get_patient(conn, patient_id)
    created_at = created_at or db.now()
    screening_id = db.next_id(conn, "screenings", "SCR-", 4)

    if skipped:
        if not skip_reason or not skip_reason.strip():
            raise HTTPException(422, "A skipped eye needs a reason")
        conn.execute(
            "INSERT INTO screenings (id, patient_id, eye, created_at, created_by, skipped, skip_reason) "
            "VALUES (?, ?, ?, ?, ?, 1, ?)",
            (screening_id, patient_id, eye, created_at, user_id, skip_reason.strip()),
        )
        return screening_id

    if image_id is None:
        raise HTTPException(422, "image_id is required unless the eye is skipped")
    image = get_image_row(conn, image_id)
    if image["patient_id"] != patient_id or image["eye"] != eye:
        raise HTTPException(409, "This photo was uploaded for a different patient or eye")
    # the model only ever runs on a photo that passed the check; the server enforces it
    if image["quality_status"] != "passed":
        raise HTTPException(409, f"Photo failed the quality check ({image['quality_reason']})")
    if conn.execute("SELECT 1 FROM screenings WHERE image_id = ?", (image_id,)).fetchone():
        raise HTTPException(409, "This photo has already been screened")

    version = model_version(conn)
    photo = cv2.imread(str(db.STORAGE / image["stored_path"]))
    photo = cv2.resize(crop_fundus(photo), (TARGET_SIZE, TARGET_SIZE), interpolation=cv2.INTER_AREA)
    raw = model.predict(photo)
    scored = []
    for condition in model.CONDITIONS:
        calibrated = round(model.calibrate(condition, raw[condition]), 3)
        result = condition_result(calibrated, version["thresholds"][condition], version["uncertain_margin"])
        scored.append((condition, raw[condition], calibrated, result))

    conn.execute(
        "INSERT INTO screenings (id, patient_id, image_id, eye, created_at, created_by, "
        "model_version_id, overall_result) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (screening_id, patient_id, image_id, eye, created_at, user_id, version["id"],
         overall_result([s[3] for s in scored])),
    )
    folder = db.STORAGE / "heatmaps"
    folder.mkdir(parents=True, exist_ok=True)
    for condition, raw_score, calibrated, result in scored:
        cur = conn.execute(
            "INSERT INTO condition_results (screening_id, condition, raw_score, calibrated_score, result) "
            "VALUES (?, ?, ?, ?, ?)",
            (screening_id, condition, raw_score, calibrated, result),
        )
        heatmap_id = db.next_id(conn, "heatmaps", "HM-", 4)
        cv2.imwrite(str(folder / f"{heatmap_id}.jpg"), model.heatmap(photo, condition))
        conn.execute("INSERT INTO heatmaps VALUES (?, ?, ?)", (heatmap_id, cur.lastrowid, f"heatmaps/{heatmap_id}.jpg"))
    return screening_id


def screening_detail(conn, screening_id):
    """Everything Results and the Screening record show for one screening."""
    s = conn.execute(
        "SELECT s.*, u.name AS created_by_name FROM screenings s JOIN users u ON u.id = s.created_by "
        "WHERE s.id = ?",
        (screening_id,),
    ).fetchone()
    if s is None:
        raise HTTPException(404, f"Screening {screening_id} not found")
    version = model_version(conn, s["model_version_id"]) if s["model_version_id"] else None
    conditions = []
    rows = conn.execute(
        "SELECT cr.*, h.id AS heatmap_id FROM condition_results cr "
        "LEFT JOIN heatmaps h ON h.condition_result_id = cr.id WHERE cr.screening_id = ? ORDER BY cr.condition",
        (screening_id,),
    )
    for r in rows:
        threshold = version["thresholds"][r["condition"]]
        conditions.append({
            "condition": r["condition"],
            "raw_score": r["raw_score"],
            "calibrated_score": r["calibrated_score"],
            "threshold": threshold,
            "result": r["result"],
            "flag_reason": flag_reason(r["calibrated_score"], threshold, r["result"]),
            "heatmap_id": r["heatmap_id"],
            "heatmap_url": f"/heatmaps/{r['heatmap_id']}" if r["heatmap_id"] else None,
        })
    return {
        "id": s["id"],
        "created_at": s["created_at"],
        "created_by": s["created_by_name"],
        "patient": get_patient(conn, s["patient_id"]),
        "eye": s["eye"],
        "skipped": bool(s["skipped"]),
        "skip_reason": s["skip_reason"],
        "overall_result": s["overall_result"],
        "image": image_out(get_image_row(conn, s["image_id"])) if s["image_id"] else None,
        "conditions": conditions,
        "model_version": version,
    }


SUMMARY_SQL = """
SELECT s.id, s.created_at, s.patient_id, p.full_name AS patient_name, s.eye,
       s.skipped, s.skip_reason, s.overall_result,
       (SELECT result FROM condition_results WHERE screening_id = s.id AND condition = 'cataract') AS cataract,
       (SELECT result FROM condition_results WHERE screening_id = s.id AND condition = 'glaucoma') AS glaucoma
FROM screenings s JOIN patients p ON p.id = s.patient_id
"""


def list_screenings(conn, query=None, patient_id=None, date=None, eye=None, result=None):
    """History rows, newest first. date is YYYY-MM-DD or "today"."""
    where, args = [], []
    if query:
        where.append("(p.full_name LIKE ? OR p.id LIKE ? OR s.id LIKE ?)")
        args += [f"%{query}%"] * 3
    if patient_id:
        where.append("s.patient_id = ?")
        args.append(patient_id)
    if date:
        where.append("SUBSTR(s.created_at, 1, 10) = ?")
        args.append(db.today() if date == "today" else date)
    if eye:
        where.append("s.eye = ?")
        args.append(eye)
    if result:
        where.append("s.overall_result = ?")
        args.append(result)
    sql = SUMMARY_SQL + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY s.created_at DESC, s.id DESC"
    rows = [dict(r) for r in conn.execute(sql, args)]
    for r in rows:
        r["skipped"] = bool(r["skipped"])
    return rows


def patient_detail(conn, patient_id):
    """Patient page: the patient, their last encounter and the latest screening of each eye."""
    patient = get_patient(conn, patient_id)
    screenings = list_screenings(conn, patient_id=patient_id)
    latest = {}
    for eye in EYES:
        newest = next((s for s in screenings if s["eye"] == eye), None)
        latest[eye] = screening_detail(conn, newest["id"]) if newest else None
    return {
        "patient": patient,
        "last_encounter": screenings[0]["created_at"] if screenings else None,
        "latest": latest,
    }
