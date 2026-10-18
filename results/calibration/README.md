# Validation calibration work

## Approved freeze: 17 October 2026

The final settings are in `frozen_settings.json`, using the reviewed values in
`approved_settings_90pct_floor.csv`. Review: https://github.com/htmw/F2026-Team1/pull/43.
The user relayed the reviewer's approval and authorized the freeze. All twelve
head/seed combinations were independently reproduced from validation predictions.

The agreed rule replaces the earlier weighted Youden proposal: require at least
90% sensitivity **before uncertainty**, then choose the fewest false positives
(highest specificity). Ties prefer the highest threshold. Calculate the 5%
distance margin around that cutoff; it includes 52/1,024 validation eyes here.
The uncertainty band may add referrals beyond the threshold-only result.

### Tradeoff compared with the earlier weighted rule

We chose the 90% sensitivity rule to limit missed cases while reducing false
referrals. Compared with the earlier weighted rule, a few models detect one or
two fewer positive eyes, but they still meet the target and refer fewer eyes
overall. This is the tradeoff we agreed to keep in the final settings.

The following validation counts include uncertain referrals under each rule:

| Model | Seed | Positive eyes found: weighted rule | Positive eyes found: approved rule | Total referrals: weighted rule | Total referrals: approved rule |
|---|---|---|---|---|---|
| Cataract-only | 42 | 45/46 | 44/46 | 160/1,024 | 122/1,024 |
| Cataract-only | 43 | 45/46 | 44/46 | 168/1,024 | 125/1,024 |
| Cataract-only | 44 | 45/46 | 43/46 | 171/1,024 | 114/1,024 |
| Shared glaucoma head | 44 | 37/39 | 36/39 | 350/1,024 | 318/1,024 |

For example, the shared glaucoma model with seed 44 now detects 36 of 39 positive
eyes instead of 37, while total referrals decrease from 350 to 318. All four
models shown above still meet the 90% target on validation data. We will report
external performance separately after testing.

These counts were checked against `settings_review.json` and
`frozen_settings.json`, using `including_uncertainty` in both files. No frozen
settings were changed for this update.

### App model and frozen artifacts

**Shared seed 42 is selected for the app**, before external testing. With uncertain
referrals included it finds 38/39 glaucoma and 45/46 cataract validation eyes.
All three seeds remain in the paper. These results are not a guarantee of external
performance. This selection records the app model; connecting real inference to
the app remains the integration task.

The approved CSV coefficients are retained at full precision. Tiny optimizer
rounding differences from earlier trial coefficients were checked for equivalence;
the approved thresholds, margins, counts and rates reproduce exactly to the
recorded comparison tolerances. The freeze script refuses to overwrite a frozen
file. Do not refit after viewing holdout or test outcomes.

The frozen file was committed in `2920a71` before the 21-eye check on 17 October
2026. Results are in `final_holdout_report.json` and `final_holdout_report.md`.
For shared seed 42, 8/21 eyes were uncertain and 15/21 were referred in total
(7 ordinary referrals). The counts were independently checked against per-eye
records; no settings were changed after observing the holdout outcomes. Old `settings_review.*` files describe the superseded
weighted-rule proposal, not the settings used by that report.

## Reproduce the comparisons

From the repository root with the project environment active:

```bash
python scripts/calibrate_models.py --disease cataract
python scripts/check_calibration_cv.py --disease cataract
python scripts/compare_glaucoma_thresholds.py --disease cataract
python scripts/compare_glaucoma_abstention.py --disease cataract
```

Use `--disease glaucoma` in the same commands for glaucoma. The two comparison
scripts retain their historical filenames but support both diseases.
These commands use saved validation scores, without opening test or holdout photos.

If a checkpoint changes, regenerate the affected predictions first, for example:

```bash
python scripts/calibrate_models.py --disease cataract --collect-predictions --collect-seeds 42
```

Then rerun the other three commands above. Omitting `--collect-seeds` refreshes
all three seeds. Calibration still compares all three seeds after collection.

## Checkpoint update on 13 October 2026

- The final cataract and glaucoma training PRs are merged into `develop`.
- Final release files were checked against GitHub's SHA-256 digests.
- Cataract seed 42 was rerun by its author: its best epoch is now 1, replacing
  the earlier epoch-11 checkpoint. Its 1,024 validation predictions and all downstream trial reports were regenerated.
- All three glaucoma checkpoint tensors are exactly equal to the earlier
  versions; their checkpoint metadata changed. Cataract seeds 43 and 44 are unchanged.
- `checkpoint_release_audit.json` records original and final checkpoint hashes
  and the outcome of the tensor-by-tensor comparison.
- `*.meta.json` records checkpoint, label/source and prediction hashes. Existing
  compatible scores have an explicit migration note; this does not claim their
  provenance was recorded at their original collection time.
- Comparison runs check these records. A different local checkpoint or input
  requires regeneration. If checkpoints are absent, saved-score analysis can
  still run; it checks recorded inputs and scores but cannot verify a local model.

## Evaluation settings

All six single-disease comparisons use the same 1,024 validation images,
batch size 8, no shuffling, evaluation mode, the shared validation transform,
and preprocessed ODIR images. These match the training validation setup.
Inference here uses CPU. Small glaucoma seed-43 and refreshed cataract seed-42 AUROC differences
are recorded in `validation_reproduction_check.json`; CPU/GPU precision is a possible,
unconfirmed explanation. Original training predictions were not retained by
the model author.

Calibration cross-validation holds out whole patients. Base-model checkpoint
selection already used validation, so these results are not independent tests.
Referral and uncertainty comparisons are descriptive choices on validation,
not guarantees about future patients. The Platt tolerance accepts fitting-loss
increases up to 0.0001 with a warning and stops for larger increases; a warning
still needs inspection and does not prove the cause is rounding.

## Shared models and reproducible threshold selection

Run from the repository root:

```bash
python scripts/calibrate_shared_models.py
python scripts/select_calibration_settings.py
```

The first command collects both shared heads in one pass per seed. It verifies
release hashes, model identity, validation filenames/labels, and AUROC reproduction
within 0.0001 of checkpoint metadata. Predictions and hashes are stored under
`results/calibration/shared/`. Existing valid scores are reused.

The second command compares uncalibrated, temperature and Platt probabilities
using five patient-grouped folds, then fits Platt on the full validation split.
It calculates separate settings for all twelve head/seed pairs from nine models.
It requires at least 90% sensitivity before uncertainty, then maximizes
specificity. Ties prefer a higher threshold. The uncertainty margin includes the
nearest `ceil(0.05*n)` probabilities to the cutoff, including boundary ties.
For 1,024 images this means at least 52 uncertain eyes per head. Total referrals
include both ordinary referrals and uncertain referrals. No averaging of seeds
or rounded cutoffs is used. These policy choices were approved in the review relayed on 17 October 2026.

`settings_review.json` contains full precision parameters and provenance.
`settings_review.csv` and `settings_review.md` summarize the operating points.
`settings_review_oof.csv` saves held-out calibration probabilities for auditing.
These remain pending review, not frozen. Results are validation selection results,
not independent performance estimates. Calibration improves probability estimates;
it does not guarantee true probabilities or clinical safety.

## Earlier single-model experiment

The original 13 October settings are preserved under
`archive/single_model_2026_10_13/frozen_settings.json`. The old top-level
`frozen_settings.json` is marked superseded and unfrozen. Its rounded common
thresholds and margins were not reproducible per-model optima or exactly 5%
uncertainty coverage. They are not the final shared-model settings.

The earlier 21-eye holdout results remain available as historical observations.
These eyes have already been examined; do not describe them as untouched or use
their outcomes to tune the new rules. The present selection scripts read validation
only. Referral counts alone do not establish safety because reliable disease
labels are unavailable for these low-quality eyes.

## Final holdout procedure

Commit the approved frozen settings. Only afterward run the low-quality holdout report with
those fixed settings. Do not tune on holdout, internal test or external test data.

The prepared command is:

```bash
python scripts/evaluate_calibration_holdout.py --settings results/calibration/frozen_settings.json
```

It deliberately stops while `frozen` is false. After review, record the review
reference, set `status` to `frozen` and `frozen` to true in the approved settings,
and commit that exact file before running. The evaluator verifies checkpoint and
label hashes, uses batches of eight, and reports uncertain and total referrals
per head and across both heads. It does not infer disease accuracy from these eyes.
