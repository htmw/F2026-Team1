
-- DUAL EyeQ PostgreSQL database schema
-- For initializing a NEW, EMPTY database only.
-- Do not run against the existing production database.

BEGIN;

CREATE TABLE public.users (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name TEXT NOT NULL,
    role TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL
);

CREATE TABLE public.sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL
        REFERENCES public.users(id),
    expires_at TEXT NOT NULL
);

CREATE TABLE public.patients (
    id TEXT PRIMARY KEY,
    full_name TEXT NOT NULL,
    age INTEGER NOT NULL,
    sex TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE public.images (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL
        REFERENCES public.patients(id),
    eye TEXT NOT NULL,
    file_name TEXT NOT NULL,
    stored_path TEXT,
    width INTEGER,
    height INTEGER,
    quality_status TEXT NOT NULL,
    quality_reason TEXT,
    uploaded_at TEXT NOT NULL,
    sha256 TEXT
);

CREATE TABLE public.model_versions (
    id TEXT PRIMARY KEY,
    thresholds TEXT NOT NULL,
    uncertain_margin DOUBLE PRECISION NOT NULL,
    commit_hash TEXT,
    is_mock INTEGER NOT NULL,
    released_at TEXT NOT NULL
);

CREATE TABLE public.screenings (
    id TEXT PRIMARY KEY,
    patient_id TEXT NOT NULL
        REFERENCES public.patients(id),
    image_id TEXT UNIQUE
        REFERENCES public.images(id),
    eye TEXT NOT NULL,
    created_at TEXT NOT NULL,
    created_by INTEGER NOT NULL
        REFERENCES public.users(id),
    model_version_id TEXT
        REFERENCES public.model_versions(id),
    overall_result TEXT,
    skipped INTEGER NOT NULL DEFAULT 0,
    skip_reason TEXT
);

CREATE TABLE public.condition_results (
    id INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    screening_id TEXT NOT NULL
        REFERENCES public.screenings(id),
    condition TEXT NOT NULL,
    raw_score DOUBLE PRECISION NOT NULL,
    calibrated_score DOUBLE PRECISION NOT NULL,
    result TEXT NOT NULL
);

CREATE TABLE public.heatmaps (
    id TEXT PRIMARY KEY,
    condition_result_id INTEGER NOT NULL
        REFERENCES public.condition_results(id),
    stored_path TEXT NOT NULL
);

COMMIT;
