
"""Dual Eye Q FastAPI backend."""

import os
from contextlib import asynccontextmanager
from typing import Annotated, Literal, Optional

import psycopg
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Response,
    UploadFile,
)
from fastapi.middleware.cors import CORSMiddleware

from . import db, reports, service
from .auth import (
    COOKIE,
    SESSION_HOURS,
    PostgresCurrentUser,
    new_postgres_session,
    session_token,
    verify_password,
)
from .schemas import (
    Eye,
    Image,
    LoginIn,
    LoginOut,
    ModelVersion,
    NextId,
    Patient,
    PatientDetail,
    PatientIn,
    Screening,
    ScreeningIn,
    ScreeningSummary,
    User,
)


MAX_UPLOAD_MB = 20

ORIGINS = os.environ.get(
    "DUAL_CORS_ORIGINS",
    "http://localhost:5173,http://127.0.0.1:5173",
).split(",")


# Original SQLite dependency:
# Db = Annotated[
#     sqlite3.Connection,
#     Depends(db.get_db),
# ]

PgDb = Annotated[
    psycopg.Connection,
    Depends(db.get_postgres_db),
]


# Original SQLite startup:
#
# @asynccontextmanager
# async def lifespan(app):
#     init()
#     yield


@asynccontextmanager
async def lifespan(app):
    with db.connect_postgres() as conn:
        service.ensure_model_version(conn)
        conn.commit()

    yield


app = FastAPI(
    title="DUAL API",
    version="0.1.0",
    lifespan=lifespan,
    description=(
        "Back end for the DUAL screener. "
        "Triage, not diagnosis. "
        "Scores come from a MOCK model."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------- Authentication ----------

# Original SQLite login:
#
# @app.post("/auth/login", response_model=LoginOut, tags=["auth"])
# def login(body: LoginIn, response: Response, conn: Db):
#     row = conn.execute(
#         "SELECT * FROM users WHERE email = ?",
#         (body.email.strip().lower(),),
#     ).fetchone()
#
#     if row is None or not verify_password(
#         body.password, row["password_hash"]
#     ):
#         raise HTTPException(401, "Wrong email or password")
#
#     token = new_session(conn, row["id"])
#     conn.commit()
#     response.set_cookie(
#         COOKIE, token, httponly=True,
#         samesite="lax",
#         max_age=SESSION_HOURS * 3600,
#     )
#     return {
#         "user": {
#             key: row[key]
#             for key in ("id", "name", "role", "email")
#         },
#         "token": token,
#     }


@app.post(
    "/auth/login",
    response_model=LoginOut,
    tags=["auth"],
)
def login(
    body: LoginIn,
    response: Response,
    conn: PgDb,
):
    row = conn.execute(
        "SELECT * FROM users WHERE email = %s",
        (body.email.strip().lower(),),
    ).fetchone()

    if row is None or not verify_password(
        body.password,
        row["password_hash"],
    ):
        raise HTTPException(
            401,
            "Wrong email or password",
        )

    token = new_postgres_session(
        conn,
        row["id"],
    )
    conn.commit()

    cross_site = (
        os.environ.get("DUAL_CROSS_SITE_COOKIES")
        == "1"
    )

    response.set_cookie(
        COOKIE,
        token,
        httponly=True,
        samesite="none" if cross_site else "lax",
        secure=cross_site,
        max_age=SESSION_HOURS * 3600,
    )

    return {
        "user": {
            key: row[key]
            for key in (
                "id",
                "name",
                "role",
                "email",
            )
        },
        "token": token,
    }


# Original SQLite logout:
#
# @app.post("/auth/logout", status_code=204, tags=["auth"])
# def logout(response: Response, conn: Db,
#            user: CurrentUser,
#            token: Annotated[str, Depends(session_token)]):
#     conn.execute(
#         "DELETE FROM sessions WHERE token = ?",
#         (token,),
#     )
#     conn.commit()
#     response.delete_cookie(COOKIE)


@app.post(
    "/auth/logout",
    status_code=204,
    tags=["auth"],
)
def logout(
    response: Response,
    conn: PgDb,
    user: PostgresCurrentUser,
    token: Annotated[
        str,
        Depends(session_token),
    ],
):
    conn.execute(
        "DELETE FROM sessions WHERE token = %s",
        (token,),
    )
    conn.commit()
    response.delete_cookie(COOKIE)


# Original SQLite current user:
#
# @app.get("/auth/me", response_model=User, tags=["auth"])
# def me(user: CurrentUser):
#     return user


@app.get(
    "/auth/me",
    response_model=User,
    tags=["auth"],
)
def me(user: PostgresCurrentUser):
    return user


# ---------- Patients ----------

# Original SQLite patients:
#
# @app.get("/patients", response_model=list[Patient])
# def patients(conn: Db, user: CurrentUser,
#              query: Optional[str] = None):
#     return service.list_patients(conn, query)


@app.get(
    "/patients",
    response_model=list[Patient],
    tags=["patients"],
)
def patients(
    conn: PgDb,
    user: PostgresCurrentUser,
    query: Optional[str] = None,
):
    return service.list_patients(
        conn,
        query,
    )


# Original SQLite next ID:
#
# @app.get("/patients/next-id", response_model=NextId)
# def next_patient_id(conn: Db, user: CurrentUser):
#     return {
#         "id": db.next_id(conn, "patients", "P-", 3)
#     }


@app.get(
    "/patients/next-id",
    response_model=NextId,
    tags=["patients"],
)
def next_patient_id(
    conn: PgDb,
    user: PostgresCurrentUser,
):
    row = conn.execute(
        """
        SELECT COALESCE(
            MAX(
                CAST(
                    SUBSTRING(id FROM 3)
                    AS INTEGER
                )
            ),
            0
        ) + 1 AS next_number
        FROM patients
        WHERE id ~ '^P-[0-9]+$'
        """
    ).fetchone()

    return {
        "id": f"P-{row['next_number']:03d}"
    }


# Original SQLite create patient:
#
# @app.post("/patients", response_model=Patient, status_code=201)
# def add_patient(body: PatientIn, conn: Db,
#                 user: CurrentUser):
#     patient = service.create_patient(
#         conn, body.model_dump()
#     )
#     conn.commit()
#     return patient


@app.post(
    "/patients",
    response_model=Patient,
    status_code=201,
    tags=["patients"],
)
def add_patient(
    body: PatientIn,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    patient = service.create_patient(
        conn,
        body.model_dump(),
    )
    conn.commit()
    return patient


@app.get(
    "/patients/{patient_id}",
    response_model=PatientDetail,
    tags=["patients"],
)
def patient(
    patient_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    # Original SQLite:
    # return service.patient_detail(conn, patient_id)

    return service.patient_detail(
        conn,
        patient_id,
    )


@app.get(
    "/patients/{patient_id}/screenings",
    response_model=list[ScreeningSummary],
    tags=["patients"],
)
def patient_screenings(
    patient_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
    date: Optional[str] = None,
):
    service.get_patient(conn, patient_id)

    return service.list_screenings(
        conn,
        patient_id=patient_id,
        date=date,
    )


@app.get(
    "/patients/{patient_id}/export",
    tags=["patients"],
    response_class=Response,
    responses={
        200: {
            "content": {
                "application/pdf": {}
            }
        }
    },
)
def export_patient(
    patient_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    detail = service.patient_detail(
        conn,
        patient_id,
    )

    screenings = service.list_screenings(
        conn,
        patient_id=patient_id,
    )

    pdf = reports.patient_pdf(
        detail,
        screenings,
    )

    return _pdf_response(
        pdf,
        f"{patient_id}_dossier.pdf",
    )


# ---------- Images ----------

# Original SQLite upload logic used:
# service.save_image(conn, patient_id, eye, data)
# with a SQLite Db dependency and local file storage.
# The endpoint path and request format remain the same.


@app.post(
    "/images",
    response_model=Image,
    status_code=201,
    tags=["images"],
)
async def upload_image(
    conn: PgDb,
    user: PostgresCurrentUser,
    file: Annotated[UploadFile, File()],
    patient_id: Annotated[str, Form()],
    eye: Annotated[Eye, Form()],
):
    data = await file.read()

    if len(data) > MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(
            413,
            f"Photo is larger than {MAX_UPLOAD_MB} MB",
        )

    image = service.save_image(
        conn,
        patient_id,
        eye,
        data,
    )

    conn.commit()
    return image


# Original SQLite image endpoint used FileResponse
# and service.image_file() returned a local Path.


@app.get(
    "/images/{image_id}",
    tags=["images"],
    response_class=Response,
)
def image_512(
    image_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    return Response(
        service.image_file(conn, image_id),
        media_type="image/jpeg",
    )


@app.get(
    "/images/{image_id}/original",
    tags=["images"],
    response_class=Response,
)
def image_original(
    image_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    return Response(
        service.image_file(
            conn,
            image_id,
            original=True,
        ),
        media_type="image/jpeg",
    )


@app.delete(
    "/images/{image_id}",
    status_code=204,
    tags=["images"],
)
def discard_image(
    image_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    service.delete_image(
        conn,
        image_id,
    )
    conn.commit()


@app.get(
    "/heatmaps/{heatmap_id}",
    tags=["images"],
    response_class=Response,
)
def heatmap(
    heatmap_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    return Response(
        service.heatmap_file(
            conn,
            heatmap_id,
        ),
        media_type="image/jpeg",
    )


# ---------- Screenings ----------

# Original SQLite screening routes used:
# conn: Db
# user: CurrentUser
# and the SQLite service implementations.


@app.post(
    "/screenings",
    response_model=Screening,
    status_code=201,
    tags=["screenings"],
)
def screen(
    body: ScreeningIn,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    screening_id = service.create_screening(
        conn,
        user["id"],
        body.patient_id,
        body.eye,
        body.image_id,
        body.skipped,
        body.skip_reason,
    )

    conn.commit()

    return service.screening_detail(
        conn,
        screening_id,
    )


@app.get(
    "/screenings",
    response_model=list[ScreeningSummary],
    tags=["screenings"],
)
def history(
    conn: PgDb,
    user: PostgresCurrentUser,
    query: Optional[str] = None,
    patient: Optional[str] = None,
    date: Optional[str] = None,
    eye: Optional[Eye] = None,
    result: Optional[
        Literal["no_concern", "refer"]
    ] = None,
):
    return service.list_screenings(
        conn,
        query,
        patient,
        date,
        eye,
        result,
    )


@app.get(
    "/screenings/{screening_id}",
    response_model=Screening,
    tags=["screenings"],
)
def screening(
    screening_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    return service.screening_detail(
        conn,
        screening_id,
    )


@app.get(
    "/screenings/{screening_id}/export",
    tags=["screenings"],
    response_class=Response,
    responses={
        200: {
            "content": {
                "application/pdf": {}
            }
        }
    },
)
def export_screening(
    screening_id: str,
    conn: PgDb,
    user: PostgresCurrentUser,
):
    detail = service.screening_detail(
        conn,
        screening_id,
    )

    pdf = reports.screening_pdf(detail)

    return _pdf_response(
        pdf,
        f"{screening_id}_summary.pdf",
    )


# ---------- Model ----------

@app.get(
    "/model",
    response_model=ModelVersion,
    tags=["model"],
)
def current_model(
    conn: PgDb,
    user: PostgresCurrentUser,
):
    return service.model_version(conn)


# ---------- System ----------

@app.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


def _pdf_response(pdf, filename):
    return Response(
        pdf,
        media_type="application/pdf",
        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )
