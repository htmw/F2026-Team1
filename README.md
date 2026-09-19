# DUAL: Dual Ocular Screener (Team EyeQ, CS691, Pace University)

One shared ResNet backbone with two binary heads (cataract, glaucoma) on single
fundus photographs. This is a triage tool, not a diagnostic one.

## Data
Datasets are NOT stored in this repo. Get them from the team Google Drive,
unzip, and verify from inside the data folder with:

    shasum -a 256 -c MANIFEST.sha256

Rule: ODIR-5K is the only training data. External sets (ORIGA, DRISHTI-GS,
ACRIMA, retina_dataset_2016) are used for testing only.

## Dataset approvals
All datasets are used with Professor Wong's approval for non-commercial
academic research only (September 2026). No images are redistributed.

## Limitation
Glaucoma has three external test sets. External cataract testing relies on
retina_dataset_2016 alone.

## Setup

    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt

## Repo layout
- `src/dual/` project code (preprocessing, model, training, evaluation)
- `scripts/` tools such as the ODIR label builder
- `labels/` derived per-eye label file
- `tests/` automatic checks
- `notebooks/` exploration
- `documents/` course material and sprint files
