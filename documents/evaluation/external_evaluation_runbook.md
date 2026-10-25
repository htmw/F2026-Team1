# External evaluation run instructions

Status: code prepared for review. The final external run is on hold.

The evaluator applies the committed frozen calibration and thresholds. It does
not fit parameters or change the decision rules. Single-head and shared models
are evaluated for seeds 42, 43 and 44. Cataract is evaluated only on
retina_dataset_2016 because the other external label files label glaucoma only.

## Checks that do not run the models

From the repository root, with the project environment activated:

```sh
python scripts/evaluate_external.py
python -m pytest tests/test_external_evaluation.py tests/test_external_metrics.py tests/test_calibration_provenance.py tests/test_calibration_selection.py -q
```

The default command checks frozen settings, checkpoint hashes, image counts,
binary labels, unique paths, source image hashes and decoded 512 by 512 processed
images. It also repeats the existing exact-file ODIR/retina overlap check.
It does not collect external predictions.

## Review before the final run

Record the team's review of these protocol choices:

- 2,000 valid image-level bootstrap samples, seed 42, percentile 95% confidence
  intervals. Images are assumed independent because patient identifiers are
  unavailable. Fellow-eye dependence could make the intervals too narrow.
- The ODIR/retina overlap check detects identical files only. It does not detect
  resized or edited copies, or establish absence of overlap with every dataset.

The current user instruction is to hold the final run until review. The command
below is for use after review, not an instruction to run it now. Replace
REVIEW_LINK with the actual review reference and use a new output directory.

```sh
python scripts/evaluate_external.py --run \
  --output results/external/reviewed_run \
  --protocol-review REVIEW_LINK \
  --acknowledge-exact-only-overlap
```

Commit the reviewed code and protocol before the final run. Existing output
directories are rejected to protect previous results. A failed run retains its
partial predictions and failure manifest. Inspect the failure before restarting;
do not delete saved predictions or rerun models just to improve reported results.

## Outputs

- `run_manifest.json`: review reference, timestamps, software versions, code and
  input fingerprints, frozen settings, bootstrap details and completion status.
- `predictions.csv`: 15,948 applicable image, disease, model and seed predictions,
  including raw logits, calibrated probabilities and decisions.
- `metrics.csv`: each dataset and disease separately, each model and seed, with
  threshold-only and uncertainty-inclusive referral policies.
- `calibration_bins.csv`: ten fixed bins for raw and calibrated probabilities.
- `external_results.md`: per-seed results and mean with sample standard deviation.

Confidence intervals reuse the same image resamples across models and seeds for
each dataset and disease, without refitting. Undefined ratios are left blank with
reasons. Ranking metrics use raw logits to avoid artificial ties when sigmoid
probabilities round to zero or one; positive-slope Platt scaling preserves ranking.

No images are excluded by a photo-quality gate. External outcomes must not be
used to revise calibration, thresholds, margins or the selected app seed.
Internal test results and the final ablation comparison are separate tasks.
