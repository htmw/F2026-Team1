"""DUAL API for the frontend.

Run from the repo folder:  uvicorn backend.main:app --reload
Then open http://localhost:8000/docs to see and try every endpoint.

The model is a MOCK until Sprint 3 (see mock_model.py). Everything else
(login, patients, uploads, quality check, history, exports) is the real thing.
"""
import os
import sqlite3
from contextlib import asynccontextmanager
from typing import Annotated, Literal, Optional

from fastapi import Depends, FastAPI, File, Form, HTTPException, Response, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from . import db, reports, service
from .auth import COOKIE, SESSION_HOURS, CurrentUser, new_session, session_token, verify_password
from .schemas import (Eye, Image, LoginIn, LoginOut, ModelVersion, NextId, Patient, PatientDetail,
                      PatientIn, Screening, ScreeningIn, ScreeningSummary, User)
from .seed import init

MAX_UPLOAD_MB = 20
# the Vite dev server; add more with DUAL_CORS_ORIGINS="http://a,http://b"
ORIGINS = os.environ.get("DUAL_CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

Db = Annotated[sqlite3.Connection, Depends(db.get_db)]


@asynccontextmanager
async def lifespan(app):
    init()
    yield


app = FastAPI(title="DUAL API", version="0.1.0", lifespan=lifespan,
              description="Back end for the DUAL screener. Triage, not diagnosis. Scores come from a MOCK model.")
app.add_middleware(CORSMiddleware, allow_origins=ORIGINS, allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


# ---------- login ----------

@app.post("/auth/login", response_model=LoginOut, tags=["auth"])
def login(body: LoginIn, response: Response, conn: Db):
    row = conn.execute("SELECT * FROM users WHERE email = ?", (body.email.strip().lower(),)).fetchone()
    if row is None or not verify_password(body.password, row["password_hash"]):
        raise HTTPException(401, "Wrong email or password")
    token = new_session(conn, row["id"])
    conn.commit()
    response.set_cookie(COOKIE, token, httponly=True, samesite="lax", max_age=SESSION_HOURS * 3600)
    return {"user": {k: row[k] for k in ("id", "name", "role", "email")}, "token": token}


@app.post("/auth/logout", status_code=204, tags=["auth"])
def logout(response: Response, conn: Db, user: CurrentUser, token: Annotated[str, Depends(session_token)]):
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    response.delete_cookie(COOKIE)


@app.get("/auth/me", response_model=User, tags=["auth"], summary="Signed-in user (header name)")
def me(user: CurrentUser):
    return user


# ---------- patients ----------

@app.get("/patients", response_model=list[Patient], tags=["patients"], summary="Patients, sorted by last name")
def patients(conn: Db, user: CurrentUser, query: Optional[str] = None):
    return service.list_patients(conn, query)


@app.get("/patients/next-id", response_model=NextId, tags=["patients"], summary="ID the next new patient will get")
def next_patient_id(conn: Db, user: CurrentUser):
    return {"id": db.next_id(conn, "patients", "P-", 3)}


@app.post("/patients", response_model=Patient, status_code=201, tags=["patients"])
def add_patient(body: PatientIn, conn: Db, user: CurrentUser):
    patient = service.create_patient(conn, body.model_dump())
    conn.commit()
    return patient


@app.get("/patients/{patient_id}", response_model=PatientDetail, tags=["patients"],
         summary="Patient page: patient, last encounter, latest screening per eye")
def patient(patient_id: str, conn: Db, user: CurrentUser):
    return service.patient_detail(conn, patient_id)


@app.get("/patients/{patient_id}/screenings", response_model=list[ScreeningSummary], tags=["patients"],
         summary="A patient's screenings, newest first (date=today for today's visit)")
def patient_screenings(patient_id: str, conn: Db, user: CurrentUser, date: Optional[str] = None):
    service.get_patient(conn, patient_id)
    return service.list_screenings(conn, patient_id=patient_id, date=date)


@app.get("/patients/{patient_id}/export", tags=["patients"], summary="Export Dossier (PDF)",
         response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def export_patient(patient_id: str, conn: Db, user: CurrentUser):
    detail = service.patient_detail(conn, patient_id)
    pdf = reports.patient_pdf(detail, service.list_screenings(conn, patient_id=patient_id))
    return _pdf_response(pdf, f"{patient_id}_dossier.pdf")


# ---------- images ----------

@app.post("/images", response_model=Image, status_code=201, tags=["images"],
          summary="Upload a photo; the quality check runs straight away")
async def upload_image(conn: Db, user: CurrentUser, file: Annotated[UploadFile, File()],
                       patient_id: Annotated[str, Form()], eye: Annotated[Eye, Form()]):
    data = await file.read()
    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"Photo is larger than {MAX_UPLOAD_MB} MB")
    image = service.save_image(conn, patient_id, eye, data)
    conn.commit()
    return image


@app.get("/images/{image_id}", tags=["images"], summary="512 x 512 preprocessed photo (JPEG)",
         response_class=FileResponse)
def image_512(image_id: str, conn: Db, user: CurrentUser):
    return FileResponse(service.image_file(conn, image_id), media_type="image/jpeg")


@app.get("/images/{image_id}/original", tags=["images"], summary="Photo as uploaded (JPEG)",
         response_class=FileResponse)
def image_original(image_id: str, conn: Db, user: CurrentUser):
    return FileResponse(service.image_file(conn, image_id, original=True), media_type="image/jpeg")


@app.delete("/images/{image_id}", status_code=204, tags=["images"],
            summary="Retake / Upload different photo: discard an unscreened photo")
def discard_image(image_id: str, conn: Db, user: CurrentUser):
    service.delete_image(conn, image_id)
    conn.commit()


@app.get("/heatmaps/{heatmap_id}", tags=["images"], summary="Heatmap image (JPEG, MOCK for now)",
         response_class=FileResponse)
def heatmap(heatmap_id: str, conn: Db, user: CurrentUser):
    return FileResponse(service.heatmap_file(conn, heatmap_id), media_type="image/jpeg")


# ---------- screenings ----------

@app.post("/screenings", response_model=Screening, status_code=201, tags=["screenings"],
          summary="Screen this photo, or skip an eye (skipped=true with a skip_reason)")
def screen(body: ScreeningIn, conn: Db, user: CurrentUser):
    screening_id = service.create_screening(conn, user["id"], body.patient_id, body.eye, body.image_id,
                                            body.skipped, body.skip_reason)
    conn.commit()
    return service.screening_detail(conn, screening_id)


@app.get("/screenings", response_model=list[ScreeningSummary], tags=["screenings"],
         summary="History, newest first")
def history(conn: Db, user: CurrentUser, query: Optional[str] = None, patient: Optional[str] = None,
            date: Optional[str] = None, eye: Optional[Eye] = None,
            result: Optional[Literal["no_concern", "refer"]] = None):
    return service.list_screenings(conn, query, patient, date, eye, result)


@app.get("/screenings/{screening_id}", response_model=Screening, tags=["screenings"],
         summary="Results and Screening record")
def screening(screening_id: str, conn: Db, user: CurrentUser):
    return service.screening_detail(conn, screening_id)


@app.get("/screenings/{screening_id}/export", tags=["screenings"], summary="Export summary (PDF)",
         response_class=Response, responses={200: {"content": {"application/pdf": {}}}})
def export_screening(screening_id: str, conn: Db, user: CurrentUser):
    pdf = reports.screening_pdf(service.screening_detail(conn, screening_id))
    return _pdf_response(pdf, f"{screening_id}_summary.pdf")


# ---------- model ----------

@app.get("/model", response_model=ModelVersion, tags=["model"], summary="Current model version and thresholds")
def current_model(conn: Db, user: CurrentUser):
    return service.model_version(conn)


def _pdf_response(pdf, filename):
    return Response(pdf, media_type="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{filename}"'})
