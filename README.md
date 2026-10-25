# DUAL: Dual Ocular Screener (Team EyeQ, CS691, Pace University)

One shared ResNet-50 backbone with two binary heads (cataract, glaucoma) on single
fundus photographs. This is a triage tool, not a diagnostic one.

The main result is external validation, plus a multi-task ablation (single-disease
vs shared models), calibration with an "Uncertain, refer" result, and Grad-CAM
safety checks. The app lets clinic staff upload a photo and see the result.

## Live prototype
- App: https://dual-eyeq-frontend.vercel.app/
- Back end API docs: https://dual-eyeq-backend.onrender.com/docs

To sign in (temporary, until the in-app login screen is added in Sprint 2):

1. Open the back end API docs. The first load can take up to a minute while
   the server wakes up.
2. Open `POST /auth/login`, click Try it out, use the body below, then click Execute:

       {"email": "demo.clinician@example.com", "password": "demo"}

3. In the same browser, open the app and use the menu to go to Upload or History.

Known limitations: reloading any page other than Home shows a 404, the doctor
name and Sign Out in the top bar are placeholders, and Safari may block the
sign-in, so use Chrome. The demo account and all patients are made up, and the
scores come from a mock model.

## Data
All datasets are in this repo under `data/`, so everyone has the same paths after cloning:

    data/Internal/ODIR-5K/Training Images/     training data (ODIR-5K)
    data/External/ORIGA/                        test only
    data/External/DRISHTI-GS/                   test only
    data/External/ACRIMA/                       test only
    data/External/retina_dataset_2016/          test only

Code should use paths starting with `data/`, for example
`Path("data/Internal/ODIR-5K/Training Images")`, and be run from the repo folder.
Preprocessed copies go in `Preprocessed/`, which git ignores, since they can be rebuilt.

To check your copy of the data is complete and unchanged, run this from inside `data/`:

    shasum -a 256 -c MANIFEST.sha256

Rule: ODIR-5K is the only training data. External sets (ORIGA, DRISHTI-GS,
ACRIMA, retina_dataset_2016) are used for testing only. Calibration, thresholds
and the uncertain cutoff are fitted on the ODIR validation split only.

## Splits
One row per eye in `labels/eye_labels_task7.csv`. Split by patient, 70/15/15,
so both eyes of a patient are in the same split.

| Split | Eyes | Patients | Cataract | Glaucoma |
|---|---:|---:|---:|---:|
| train | 4,807 | 2,437 | 225 | 198 |
| validation | 1,024 | 522 | 46 | 39 |
| test | 1,036 | 522 | 40 | 45 |

124 eyes are `holdout` and 9 are `excluded` (see Data decisions).

External labels are in `labels/external/` (one CSV per dataset).

## Data decisions
- Media opacity: all 63 media-opacity eyes are held out of train, validation and test (split = holdout). They are used later as the check for the cataract "haze shortcut".
- Low image quality: the 21 low-quality eyes are held out (split = holdout) and used later to test the "uncertain, refer" result.
- Suspected glaucoma: all 44 suspected-glaucoma eyes are held out. This includes 2 eyes that also have cataract (625_left, 1415_right), so they are not used as cataract examples either.
- Fellow eyes: when one eye is held out, the patient's other eye can still be in train, validation or test. For 28 media-opacity patients the other eye is in training, so the haze check is reported twice: on all 63 eyes, and only on eyes whose other eye was not in training.

## Dataset approvals
All datasets are used with Professor Wong's approval for non-commercial
academic research only (September 2026). He confirmed that keeping the
datasets in this repo is fine, since the project is not commercial.

## Limitation
Glaucoma has three external test sets. External cataract testing relies on
retina_dataset_2016 alone.

## External evaluation protocol

The [external evaluation protocol](documents/evaluation/external_validation_protocol.md)
defines the test-only datasets, metrics, confidence intervals and referral reporting
for SCRUM-44. It is a draft for team review. Final external testing starts only
after the calibration and decision settings are reviewed, frozen and committed.

## Setup (one time)
Use Python 3.14. The package versions in requirements.txt were pinned on 3.14,
and older Python versions may fail to install them.

    git clone https://github.com/htmw/F2026-Team1.git
    cd F2026-Team1
    python3 -m venv .venv
    source .venv/bin/activate        # Windows: .venv\Scripts\activate
    pip install -r requirements.txt

Every time you open a new terminal to work on the project, activate again:

    source .venv/bin/activate        # Windows: .venv\Scripts\activate

The frontend also needs Node.js with npm:

    cd frontend
    npm install

## Run the app
Back end (FastAPI), from the repo folder:

    uvicorn backend.main:app --reload

The back end uses Supabase (PostgreSQL for the data, Storage for photos and
heatmaps). It reads these settings from a `.env` file in the repo folder:

    DATABASE_URL=...
    SUPABASE_URL=...
    SUPABASE_SERVICE_ROLE_KEY=...

Ask the team for the values. Never commit `.env` (git ignores it). Your local
back end uses the same shared database as the live prototype, so sign in with
the demo account above and only add made-up patients.

It runs at http://localhost:8000, with every endpoint listed at
http://localhost:8000/docs. Endpoint details: `backend/README.md`.

Frontend (React + Vite), in a second terminal:

    cd frontend
    npm run dev

It runs at http://localhost:5173.

The model in the app is still a mock (`backend/mock_model.py`): made-up scores,
heatmaps marked "MOCK" and placeholder thresholds. The trained model and the
approved calibration settings replace it later. Only made-up patients are used.

## Pipeline
Run from the repo folder, in this order. Each step writes the file the next one reads.

| Step | Command | Output |
|---|---|---|
| Per-eye labels | `python scripts/build_eye_labels.py` | labels/eye_labels_task6.csv |
| Split | `python scripts/split_dataset.py` | labels/eye_labels_task7.csv |
| Check labels | `python scripts/verify_labels.py labels/eye_labels_task7.csv` | pass or fail |
| External labels | `python scripts/build_external_labels.py` | labels/external/ |
| Overlap check | `python scripts/check_dataset_overlap.py` | ODIR vs retina_dataset_2016 duplicates |
| Preprocess | `python scripts/preprocess_images.py` | Preprocessed/ (512 x 512) |
| Check preprocessing | `python scripts/verify_preprocessing.py` | preprocessing_check.jpg |
| Train cataract-only | `python scripts/train_cataract.py` | 3 seeds, results/task11/ |
| Train glaucoma-only | `python scripts/train_glaucoma.py` | 3 seeds, results/task11/ |
| Train shared model | `python scripts/train_dual_task11.py --seed 42` (then 43, 44) | results/task11/ |
| Calibration | see `results/calibration/README.md` | results/calibration/ |

Preprocessing is one function for ODIR and all external sets. When the fundus
circle is not found, it falls back to the largest centered square.

## Models and checkpoints
Nine models: cataract-only, glaucoma-only and shared two-head, seeds 42, 43
and 44, all with the same settings. Checkpoints are not in git; they are in
GitHub releases. The settings, validation AUROCs, checkpoint hashes and release
links for all nine runs are in `results/task11/README.md`.

## Calibration and thresholds
Platt calibration, a decision threshold and an "Uncertain, refer" margin for
each model, head and seed, fitted on the validation split only. Frozen on
17 October 2026 in `results/calibration/frozen_settings.json`; the app will use
the shared model, seed 42. Details: `results/calibration/README.md`.

## Tests

    python -m pytest tests

The API tests (`tests/test_api.py`) write to a database, so they are skipped
unless `TEST_DATABASE_URL` points to a separate test database, and they refuse
to run against the `DATABASE_URL` in `.env` (the shared database the live app
uses). They were written for the old SQLite back end and are being updated for
Supabase. Each model also has a smoke
test in `scripts/` (for example `python scripts/test_train_dual_task11.py`),
which needs that model's checkpoints downloaded.

## Random seeds
`SEED = 42` in `src/dual/config.py` is the project seed. It made the
train/validation/test split and must not change. Training uses seeds 42, 43 and 44 for every model
type, so results can be reported as a mean over seeds. Every script starts with:

    from dual.config import set_seed
    set_seed()

Training scripts call `set_seed(seed)` for each run.

## Branches
- `develop`: everyday work goes here. All new code is reviewed on `develop` first.
- `main`: the reviewed version. Changes move from `develop` to `main` through a
  pull request once they are reviewed, as often as needed (not only at the end of a sprint).
  Never push to `main` directly.
- Task branches: create from `develop`, name after the task
  (for example `task-3-verification-script`), open the pull request into `develop`.
  Do not push to `develop` directly either.
- When opening a pull request, check the base branch before creating it.
- Wait for an approving review before merging.

## Repo layout
- `data/` the datasets (see Data above)
- `labels/` per-eye ODIR labels, the split file and external labels
- `src/dual/` shared settings (the random seed in config.py)
- `scripts/` project code: labels, split, preprocessing, models, training, calibration
- `results/` training results (`task11/`) and calibration results (`calibration/`)
- `backend/` the API (FastAPI, Supabase PostgreSQL and Storage) with the mock model
- `frontend/` the app (React + Vite)
- `tests/` automatic checks
- `notebooks/` exploration
- `documents/` course material and sprint files
