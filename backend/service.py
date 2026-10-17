
"""Business logic for the Dual Eye Q API."""

import os
import sys
import json
import hashlib

from pathlib import Path
from urllib.parse import quote

import cv2
import httpx
import numpy as np
import psycopg

from fastapi import HTTPException

from . import db
from . import mock_model as model
from .results import (
    condition_result,
    flag_reason,
    overall_result,
)


REPO = Path(__file__).resolve().parents[1]

sys.path.insert(
    0,
    str(REPO / "scripts"),
)

import quality_check as qc
from preprocess_images import TARGET_SIZE, crop_fundus


EYES = ("right", "left")


# ---------- Original SQLite implementation ----------

# Keep your existing SQLite service functions in this
# section as comments. Their replacements appear below.
#
# Original SQLite queries used:
#
# SELECT ... WHERE id = ?
# INSERT INTO ... VALUES (?, ?, ...)
# INSERT OR IGNORE INTO ...
#
# Original local image storage used:
#
# db.STORAGE / "images"
# db.STORAGE / "heatmaps"
#
# The PostgreSQL implementation uses %s parameters
# and Supabase Storage instead of local files.


# ---------- Supabase Storage ----------

STORAGE_BUCKETS = {
    "fundus-images",
    "processed-images",
    "heatmaps",
}


def storage_request(
    method,
    bucket,
    path=None,
    *,
    content=None,
    paths=None,
):
    """Make a server-side Supabase Storage request."""

    if bucket not in STORAGE_BUCKETS:
        raise ValueError("Unknown Storage bucket")

    base_url = os.environ.get(
        "SUPABASE_URL", ""
    ).rstrip("/")

    service_key = os.environ.get(
        "SUPABASE_SERVICE_ROLE_KEY", ""
    )

    if not base_url or not service_key:
        raise RuntimeError(
            "Missing Supabase Storage configuration"
        )

    url = (
        base_url
        + "/storage/v1/object/"
        + quote(bucket, safe="")
    )

    if path is not None:
        url += "/" + quote(path, safe="/")

    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
    }

    with httpx.Client(timeout=45) as client:
        if method == "POST":
            response = client.post(
                url,
                headers={
                    **headers,
                    "Content-Type": "image/jpeg",
                    "x-upsert": "false",
                },
                content=content,
            )

        elif method == "GET":
            response = client.get(
                url,
                headers=headers,
            )

        elif method == "DELETE":
            response = client.request(
                "DELETE",
                url,
                headers=headers,
                json={
                    "prefixes": paths or []
                },
            )

        else:
            raise ValueError(
                "Unsupported storage operation"
            )

    if response.status_code == 404:
        raise HTTPException(
            404,
            "Stored image not found",
        )

    if response.is_error:
        raise HTTPException(
            502,
            "Supabase Storage request failed",
        )

    return response.content


def storage_upload(bucket, path, content):
    storage_request(
        "POST",
        bucket,
        path,
        content=content,
    )


def storage_download(bucket, path):
    return storage_request(
        "GET",
        bucket,
        path,
    )


def storage_delete(bucket, paths):
    storage_request(
        "DELETE",
        bucket,
        paths=paths,
    )


# ---------- Model versions ----------

# Original SQLite:
#
# conn.execute(
#     "INSERT OR IGNORE INTO model_versions "
#     "VALUES (?, ?, ?, ?, ?, ?)",
#     (...)
# )


def ensure_model_version(conn):
    conn.execute(
        """
        INSERT INTO model_versions (
            id,
            thresholds,
            uncertain_margin,
            commit_hash,
            is_mock,
            released_at
        )
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (id) DO NOTHING
        """,
        (
            model.VERSION,
            json.dumps(model.THRESHOLDS),
            model.UNCERTAIN_MARGIN,
            None,
            1,
            db.now(),
        ),
    )


def model_version(conn, version_id=model.VERSION):
    row = conn.execute(
        """
        SELECT *
        FROM model_versions
        WHERE id = %s
        """,
        (version_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(
            404,
            "Model version not found",
        )

    return {
        "id": row["id"],
        "thresholds": json.loads(
            row["thresholds"]
        ),
        "uncertain_margin": row["uncertain_margin"],
        "commit": row["commit_hash"],
        "is_mock": bool(row["is_mock"]),
        "released_at": row["released_at"],
    }


# ---------- Patients ----------

def get_patient(conn, patient_id):
    row = conn.execute(
        """
        SELECT *
        FROM patients
        WHERE id = %s
        """,
        (patient_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(
            404,
            f"Patient {patient_id} not found",
        )

    return dict(row)


def list_patients(conn, query=None):
    sql = "SELECT * FROM patients"
    params = ()

    if query:
        sql += (
            " WHERE full_name ILIKE %s"
            " OR id ILIKE %s"
        )
        params = (
            f"%{query}%",
            f"%{query}%",
        )

    rows = [
        dict(row)
        for row in conn.execute(sql, params)
    ]

    return sorted(
        rows,
        key=lambda patient: (
            patient["full_name"]
            .split()[-1].lower(),
            patient["full_name"].lower(),
        ),
    )


# Original SQLite create_patient() used:
#
# patient_id = db.next_id(
#     conn, "patients", "P-", 3
# )
# conn.execute(
#     "INSERT INTO patients VALUES (?, ?, ?, ?, ?, ?, ?)",
#     (...)
# )


def create_patient(conn, data, created_at=None):
    patient_id = db.next_id_postgres(
        conn,
        "patients",
        "P-",
        3,
    )

    conn.execute(
        """
        INSERT INTO patients (
            id,
            full_name,
            age,
            sex,
            phone,
            email,
            created_at
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            patient_id,
            data["full_name"].strip(),
            data["age"],
            data["sex"],
            data.get("phone"),
            data.get("email"),
            created_at or db.now(),
        ),
    )

    return get_patient(
        conn,
        patient_id,
    )


def patient_detail(conn, patient_id):
    patient = get_patient(
        conn,
        patient_id,
    )

    screenings = list_screenings(
        conn,
        patient_id=patient_id,
    )

    latest = {}

    for eye in EYES:
        newest = next(
            (
                item
                for item in screenings
                if item["eye"] == eye
            ),
            None,
        )

        latest[eye] = (
            screening_detail(conn, newest["id"])
            if newest
            else None
        )

    return {
        "patient": patient,
        "last_encounter": (
            screenings[0]["created_at"]
            if screenings
            else None
        ),
        "latest": latest,
    }


# ---------- Images ----------

def image_out(row):
    has_file = (
        row["stored_path"] is not None
    )

    return {
        "id": row["id"],
        "patient_id": row["patient_id"],
        "eye": row["eye"],
        "file_name": row["file_name"],
        "width": row["width"],
        "height": row["height"],
        "quality_status": row["quality_status"],
        "quality_reason": row["quality_reason"],
        "quality_message": qc.REASONS.get(
            row["quality_reason"]
        ),
        "uploaded_at": row["uploaded_at"],
        "url": (
            f"/images/{row['id']}"
            if has_file
            else None
        ),
        "original_url": (
            f"/images/{row['id']}/original"
            if has_file
            else None
        ),
    }


def get_image_row(conn, image_id):
    row = conn.execute(
        """
        SELECT *
        FROM images
        WHERE id = %s
        """,
        (image_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(
            404,
            f"Image {image_id} not found",
        )

    return row


# Original SQLite save_image() stored JPEG files at:
#
# db.STORAGE / "images" / f"{image_id}.jpg"
# db.STORAGE / "images" / f"{image_id}_512.jpg"
#
# The PostgreSQL version uploads them to Supabase.


def save_image(
    conn,
    patient_id,
    eye,
    data,
    uploaded_at=None,
):
    get_patient(conn, patient_id)

    status, reason = qc.check(data)

    image_id = db.next_id_postgres(
        conn,
        "images",
        "IMG-",
        4,
    )

    stored_path = None
    width = None
    height = None

    if reason != "unreadable":
        image = cv2.imdecode(
            np.frombuffer(
                data,
                dtype=np.uint8,
            ),
            cv2.IMREAD_COLOR,
        )

        if image is None:
            raise HTTPException(
                422,
                "Unable to decode uploaded image",
            )

        height, width = image.shape[:2]

        original_encoded = cv2.imencode(
            ".jpg",
            image,
        )

        if not original_encoded[0]:
            raise HTTPException(
                422,
                "Unable to encode uploaded image",
            )

        original_bytes = (
            original_encoded[1].tobytes()
        )

        processed = cv2.resize(
            crop_fundus(image),
            (TARGET_SIZE, TARGET_SIZE),
            interpolation=cv2.INTER_AREA,
        )

        processed_encoded = cv2.imencode(
            ".jpg",
            processed,
        )

        if not processed_encoded[0]:
            raise HTTPException(
                422,
                "Unable to encode processed image",
            )

        processed_bytes = (
            processed_encoded[1].tobytes()
        )

        storage_upload(
            "fundus-images",
            f"{image_id}.jpg",
            original_bytes,
        )

        storage_upload(
            "processed-images",
            f"{image_id}_512.jpg",
            processed_bytes,
        )

        stored_path = f"{image_id}.jpg"

    conn.execute(
        """
        INSERT INTO images (
            id,
            patient_id,
            eye,
            file_name,
            stored_path,
            width,
            height,
            quality_status,
            quality_reason,
            uploaded_at,
            sha256
        )
        VALUES (
            %s, %s, %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        """,
        (
            image_id,
            patient_id,
            eye,
            f"{patient_id}_{eye}.jpg",
            stored_path,
            width,
            height,
            status,
            reason,
            uploaded_at or db.now(),
            hashlib.sha256(data).hexdigest(),
        ),
    )

    return image_out(
        get_image_row(conn, image_id)
    )


def image_file(conn, image_id, original=False):
    row = get_image_row(
        conn,
        image_id,
    )

    if row["stored_path"] is None:
        raise HTTPException(
            404,
            "No readable photograph",
        )

    if original:
        return storage_download(
            "fundus-images",
            f"{image_id}.jpg",
        )

    return storage_download(
        "processed-images",
        f"{image_id}_512.jpg",
    )


def delete_image(conn, image_id):
    get_image_row(conn, image_id)

    existing = conn.execute(
        """
        SELECT 1
        FROM screenings
        WHERE image_id = %s
        """,
        (image_id,),
    ).fetchone()

    if existing:
        raise HTTPException(
            409,
            "Photo has already been screened",
        )

    conn.execute(
        """
        DELETE FROM images
        WHERE id = %s
        """,
        (image_id,),
    )

    storage_delete(
        "fundus-images",
        [f"{image_id}.jpg"],
    )

    storage_delete(
        "processed-images",
        [f"{image_id}_512.jpg"],
    )


def heatmap_file(conn, heatmap_id):
    row = conn.execute(
        """
        SELECT stored_path
        FROM heatmaps
        WHERE id = %s
        """,
        (heatmap_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(
            404,
            f"Heatmap {heatmap_id} not found",
        )

    return storage_download(
        "heatmaps",
        row["stored_path"],
    )


# ---------- Screenings ----------

def create_screening(
    conn,
    user_id,
    patient_id,
    eye,
    image_id=None,
    skipped=False,
    skip_reason=None,
    created_at=None,
):
    get_patient(
        conn,
        patient_id,
    )

    screening_id = db.next_id_postgres(
        conn,
        "screenings",
        "SCR-",
        4,
    )

    created_at = created_at or db.now()

    if skipped:
        if not skip_reason or not skip_reason.strip():
            raise HTTPException(
                422,
                "A skipped eye needs a reason",
            )

        conn.execute(
            """
            INSERT INTO screenings (
                id,
                patient_id,
                eye,
                created_at,
                created_by,
                skipped,
                skip_reason
            )
            VALUES (%s, %s, %s, %s, %s, 1, %s)
            """,
            (
                screening_id,
                patient_id,
                eye,
                created_at,
                user_id,
                skip_reason.strip(),
            ),
        )

        return screening_id

    if image_id is None:
        raise HTTPException(
            422,
            "image_id is required",
        )

    image = get_image_row(
        conn,
        image_id,
    )

    if (
        image["patient_id"] != patient_id
        or image["eye"] != eye
    ):
        raise HTTPException(
            409,
            "Image belongs to another patient or eye",
        )

    if image["quality_status"] != "passed":
        raise HTTPException(
            409,
            "Photo failed quality check",
        )

    existing = conn.execute(
        """
        SELECT 1
        FROM screenings
        WHERE image_id = %s
        """,
        (image_id,),
    ).fetchone()

    if existing:
        raise HTTPException(
            409,
            "Photo has already been screened",
        )

    if image["sha256"]:
        duplicate = conn.execute(
            """
            SELECT s.id
            FROM screenings s
            JOIN images i
                ON i.id = s.image_id
            WHERE
                s.patient_id = %s
                AND s.eye = %s
                AND i.sha256 = %s
            """,
            (
                patient_id,
                eye,
                image["sha256"],
            ),
        ).fetchone()

        if duplicate:
            raise HTTPException(
                409,
                "Duplicate screening",
            )

    version = model_version(conn)

    original_bytes = storage_download(
        "fundus-images",
        image["stored_path"],
    )

    photo = cv2.imdecode(
        np.frombuffer(
            original_bytes,
            dtype=np.uint8,
        ),
        cv2.IMREAD_COLOR,
    )

    if photo is None:
        raise HTTPException(
            422,
            "Stored image could not be decoded",
        )

    photo = cv2.resize(
        crop_fundus(photo),
        (TARGET_SIZE, TARGET_SIZE),
        interpolation=cv2.INTER_AREA,
    )

    raw_scores = model.predict(photo)
    scored = []

    for condition in model.CONDITIONS:
        calibrated = round(
            model.calibrate(
                condition,
                raw_scores[condition],
            ),
            3,
        )

        result = condition_result(
            calibrated,
            version["thresholds"][condition],
            version["uncertain_margin"],
        )

        scored.append(
            (
                condition,
                raw_scores[condition],
                calibrated,
                result,
            )
        )

    conn.execute(
        """
        INSERT INTO screenings (
            id,
            patient_id,
            image_id,
            eye,
            created_at,
            created_by,
            model_version_id,
            overall_result
        )
        VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s
        )
        """,
        (
            screening_id,
            patient_id,
            image_id,
            eye,
            created_at,
            user_id,
            version["id"],
            overall_result(
                [item[3] for item in scored]
            ),
        ),
    )

    for condition, raw_score, calibrated, result in scored:
        row = conn.execute(
            """
            INSERT INTO condition_results (
                screening_id,
                condition,
                raw_score,
                calibrated_score,
                result
            )
            VALUES (%s, %s, %s, %s, %s)
            RETURNING id
            """,
            (
                screening_id,
                condition,
                raw_score,
                calibrated,
                result,
            ),
        ).fetchone()

        heatmap_id = db.next_id_postgres(
            conn,
            "heatmaps",
            "HM-",
            4,
        )

        heatmap_encoded = cv2.imencode(
            ".jpg",
            model.heatmap(
                photo,
                condition,
            ),
        )

        if not heatmap_encoded[0]:
            raise HTTPException(
                500,
                "Unable to generate heatmap",
            )

        heatmap_bytes = (
            heatmap_encoded[1].tobytes()
        )

        storage_upload(
            "heatmaps",
            f"{heatmap_id}.jpg",
            heatmap_bytes,
        )

        conn.execute(
            """
            INSERT INTO heatmaps (
                id,
                condition_result_id,
                stored_path
            )
            VALUES (%s, %s, %s)
            """,
            (
                heatmap_id,
                row["id"],
                f"{heatmap_id}.jpg",
            ),
        )

    return screening_id


def screening_detail(conn, screening_id):
    row = conn.execute(
        """
        SELECT
            s.*,
            u.name AS created_by_name
        FROM screenings s
        JOIN users u
            ON u.id = s.created_by
        WHERE s.id = %s
        """,
        (screening_id,),
    ).fetchone()

    if row is None:
        raise HTTPException(
            404,
            f"Screening {screening_id} not found",
        )

    version = (
        model_version(
            conn,
            row["model_version_id"],
        )
        if row["model_version_id"]
        else None
    )

    conditions = []

    if version is not None:
        rows = conn.execute(
            """
            SELECT
                cr.*,
                h.id AS heatmap_id
            FROM condition_results cr
            LEFT JOIN heatmaps h
                ON h.condition_result_id = cr.id
            WHERE cr.screening_id = %s
            ORDER BY cr.condition
            """,
            (screening_id,),
        )

        for item in rows:
            threshold = version["thresholds"][
                item["condition"]
            ]

            conditions.append({
                "condition": item["condition"],
                "raw_score": item["raw_score"],
                "calibrated_score":
                    item["calibrated_score"],
                "threshold": threshold,
                "result": item["result"],
                "flag_reason": flag_reason(
                    item["calibrated_score"],
                    threshold,
                    item["result"],
                ),
                "heatmap_id": item["heatmap_id"],
                "heatmap_url": (
                    f"/heatmaps/{item['heatmap_id']}"
                    if item["heatmap_id"]
                    else None
                ),
            })

    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "created_by": row["created_by_name"],
        "patient": get_patient(
            conn,
            row["patient_id"],
        ),
        "eye": row["eye"],
        "skipped": bool(row["skipped"]),
        "skip_reason": row["skip_reason"],
        "overall_result": row["overall_result"],
        "image": (
            image_out(
                get_image_row(
                    conn,
                    row["image_id"],
                )
            )
            if row["image_id"]
            else None
        ),
        "conditions": conditions,
        "model_version": version,
    }


SUMMARY_SQL = """
SELECT
    s.id,
    s.created_at,
    s.patient_id,
    p.full_name AS patient_name,
    s.eye,
    s.skipped,
    s.skip_reason,
    s.overall_result,
    (
        SELECT result
        FROM condition_results
        WHERE
            screening_id = s.id
            AND condition = 'cataract'
    ) AS cataract,
    (
        SELECT result
        FROM condition_results
        WHERE
            screening_id = s.id
            AND condition = 'glaucoma'
    ) AS glaucoma
FROM screenings s
JOIN patients p
    ON p.id = s.patient_id
"""


def list_screenings(
    conn,
    query=None,
    patient_id=None,
    date=None,
    eye=None,
    result=None,
):
    filters = []
    params = []

    if query:
        filters.append(
            """
            (
                p.full_name ILIKE %s
                OR p.id ILIKE %s
                OR s.id ILIKE %s
            )
            """
        )
        params.extend([f"%{query}%"] * 3)

    if patient_id:
        filters.append(
            "s.patient_id = %s"
        )
        params.append(patient_id)

    if date:
        filters.append(
            "LEFT(s.created_at, 10) = %s"
        )
        params.append(
            db.today()
            if date == "today"
            else date
        )

    if eye:
        filters.append(
            "s.eye = %s"
        )
        params.append(eye)

    if result:
        filters.append(
            "s.overall_result = %s"
        )
        params.append(result)

    sql = SUMMARY_SQL

    if filters:
        sql += (
            " WHERE "
            + " AND ".join(filters)
        )

    sql += (
        " ORDER BY "
        "s.created_at DESC, s.id DESC"
    )

    rows = [
        dict(row)
        for row in conn.execute(
            sql,
            params,
        )
    ]

    for row in rows:
        row["skipped"] = bool(
            row["skipped"]
        )

    return rows
