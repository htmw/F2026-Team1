# DUAL: Dual Ocular Screener (Team EyeQ, CS691, Pace University)

One shared ResNet backbone with two binary heads (cataract, glaucoma) on single
fundus photographs. This is a triage tool, not a diagnostic one.

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
ACRIMA, retina_dataset_2016) are used for testing only.

## Data decisions (Task 4)
- Media opacity: all 63 media-opacity eyes are held out of train, validation and test (split = holdout). They are used later as the check for the cataract "haze shortcut".
- Low image quality: the 21 low-quality eyes are held out (split = holdout)  and used later to test the "uncertain, refer" result.
- Suspected glaucoma: all 44 suspected-glaucoma eyes are held out. This includes 2 eyes that also have cataract (625_left, 1415_right), so they are not used as cataract examples either.
- Fellow eyes: when one eye is held out, the patient's other eye can still be in train, validation or test. For 28 media-opacity patients the other eye is in training, so the haze check is reported twice: on all 63 eyes, and only on eyes whose other eye was not in training.

## Dataset approvals
All datasets are used with Professor Wong's approval for non-commercial
academic research only (September 2026). He confirmed that keeping the
datasets in this repo is fine, since the project is not commercial.

## Limitation
Glaucoma has three external test sets. External cataract testing relies on
retina_dataset_2016 alone.

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

## Random seed
The whole project uses one seed, `SEED = 42`, defined in `src/dual/config.py`.
It was fixed before any results. Do not change it after the Task 7 split.
Every script starts with:

    from dual.config import set_seed
    set_seed()

## Branches
- `main`: stable version, updated only at the end of each sprint.
- `develop`: everyday work is merged here through pull requests.
- Task branches: create from `develop`, name after the task
  (for example `task-3-verification-script`), open the pull request into `develop`.

## Repo layout
- `data/` the datasets (see Data above)
- `src/dual/` project code (preprocessing, model, training, evaluation)
- `scripts/` tools such as the ODIR label builder
- `labels/` derived per-eye label file
- `tests/` automatic checks
- `notebooks/` exploration
- `documents/` course material and sprint files
