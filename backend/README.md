# Back end (API)

The API the frontend calls, built with FastAPI.

The model is a stand-in until Sprint 3. `mock_model.py` returns made-up scores
(the same photo always gets the same scores) and heatmaps marked "MOCK".
Login, patients, uploads, the photo quality check, screenings, history and the
PDF exports are real. When the trained model is ready, only `mock_model.py`
changes; the endpoints and the JSON stay the same.

## Run it
From the repo folder, with the virtual environment active (see Setup in the
main README):

    uvicorn backend.main:app --reload

The API runs at http://localhost:8000. Every endpoint is listed at
http://localhost:8000/docs, where you can also try each one.

The first start creates `backend/storage/` with demo data: one user, four
made-up patients and five screenings. The database, photos and heatmaps all
live there, and git ignores the folder. To start over, stop the server and
delete `backend/storage/`. Do this before running a demo again with the same
photos, since a photo can only be screened once per eye.

Demo login: `emily.geller@example.com` / `dual-demo`. This account only exists
on your own computer.

## Calling it from the frontend
- Add `credentials: "include"` to every fetch. Login sets a session cookie, and
  the browser then sends it with every request, including `<img>` tags for
  photos and heatmaps.
- The Vite dev server (http://localhost:5173) is allowed. Add other addresses
  with `DUAL_CORS_ORIGINS`, separated by commas.
- Photo and heatmap URLs come back as paths, for example `/heatmaps/HM-0001`.
  Put `http://localhost:8000` in front.
- Errors come back as `{"detail": "..."}`: 401 not signed in, 404 not found,
  409 not allowed (for example screening a photo that failed the check),
  422 a missing or wrong field.
- Thresholds are placeholders until Task 12. Read them from `GET /model` or
  from each condition in a screening; don't hard-code them.
- When a condition is `uncertain`, Results shows no score. The Screening
  record still shows both scores.

## Endpoints

| Method and path | Screen | Returns or does |
|---|---|---|
| POST /auth/login | Login | The user; sets the session cookie |
| POST /auth/logout | Sign out | Ends the session |
| GET /auth/me | Header | The signed-in user |
| GET /patients?query= | New screening, History filter | Patients, sorted by last name |
| GET /patients/next-id | Add patient | The ID the next patient will get |
| POST /patients | Add patient | The new patient |
| GET /patients/{id} | Patient page | Patient, last encounter, latest screening per eye |
| GET /patients/{id}/screenings?date=today | Upload (today's visit), Patient page | Screenings, newest first |
| GET /patients/{id}/export | Patient page: Export Dossier | PDF |
| POST /images (form: file, patient_id, eye) | New screening | The image with quality_status and quality_reason |
| GET /images/{id} | Results | 512 x 512 preprocessed photo |
| GET /images/{id}/original | Screening record | Photo as uploaded |
| DELETE /images/{id} | Photo quality failed: Retake | Discards the photo |
| POST /screenings | Screen this photo, Skip eye | Screening with both results and heatmaps |
| GET /screenings?query=&patient=&date=&eye=&result= | History | Screenings, newest first |
| GET /screenings/{id} | Results, Screening record | Screening, patient, image, results, heatmaps, model version |
| GET /screenings/{id}/export | Screening record: Export summary | PDF |
| GET /heatmaps/{id} | Results, Screening record | Heatmap image |
| GET /model | About, Screening record | Model version and thresholds |

To skip an eye, send `POST /screenings` with
`{"patient_id": "P-001", "eye": "left", "skipped": true, "skip_reason": "..."}`.

## Rules the server enforces
- The model only runs on a photo that passed the quality check, was uploaded
  for the same patient and eye, and has not been screened before.
- Per condition: a score at or above the threshold is `refer`, below it is
  `no_concern`. For now a score within 0.05 of the threshold is `uncertain`;
  Task 12 sets the real rule.
- Per eye: `refer` if either condition is `refer` or `uncertain`, otherwise
  `no_concern`.
- The same eye can be screened again with a new photo, for a follow-up visit
  or a retake. Every screening is kept; the newest one per eye is shown on the
  patient page.
- The same photo is never screened twice for the same eye, even if it is
  uploaded again or "Screen this photo" is clicked twice. The second try gets
  409 with the ID of the earlier screening.
- Every endpoint except login needs a session. Passwords are stored hashed.
- Only clinic staff have accounts; patients never log in. Every signed-in user
  can see every patient.

## Files
- `main.py` the endpoints
- `service.py` what each endpoint does (database, files, quality check, model)
- `mock_model.py` made-up scores, calibration and heatmaps, replaced in Sprint 3
- `results.py` turns scores into No concern, Refer or Uncertain
- `auth.py` login, password hashing and sessions
- `reports.py` the PDF exports
- `seed.py` the demo user, patients and screenings
- `db.py` the SQLite tables
- `schemas.py` request and response shapes (shown on /docs)

## Tests

    python -m pytest tests/test_api.py
