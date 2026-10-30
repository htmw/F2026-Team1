# SCRUM-97 - Media-Opacity Holdout Evaluation

## Objective
Evaluate whether the frozen cataract model produces unusually high referral rates for cataract-negative eyes with media opacity.

## Model Configuration
- Model: Frozen shared ResNet50
- Deployment seed: 42
- Dataset: ODIR media-opacity holdout
- Evaluated eyes: 63
- Unique patients: 53
- Ground-truth cataract labels: All negative
- Prediction file: results/task15/media_opacity_predictions.csv

## Media-Opacity Results

| Decision | Eyes | Percentage |
|---|---:|---:|
| Refer | 47 | 74.60% |
| Uncertain, refer | 7 | 11.11% |
| No concern | 9 | 14.29% |
| Total | 63 | 100.00% |

Overall referral rate: 54/63 = 85.71%.

Referral rates include both 'Refer' and 'Uncertain, refer' decisions; the latter are referred under the frozen uncertainty policy. The strict 'Refer' rate is 47/63 (74.60%).

## Internal-Test Baseline Comparison

| Metric | Media-opacity holdout | Internal-test baseline |
|---|---:|---:|
| Cataract-negative eyes | 63 | 996 |
| Refer | 47 | 40 |
| Uncertain, refer | 7 | 45 |
| No concern | 9 | 911 |
| Total referred | 54 | 85 |
| Referral rate | 85.71% | 8.53% |

Referral-rate difference: +77.18 percentage points.

The baseline includes all 996 cataract-negative internal-test eyes, not only normal-fundus eyes. Following the project label rule, eyes with other conditions (such as diabetic retinopathy, AMD, or glaucoma) also count as cataract-negative. When restricted to normal-fundus eyes, 44 of 419 were referred (10.50%), so the conclusion remains unchanged.

## Patient Overlap
- Media-opacity patients: 53
- Internal-test baseline patients: 512
- Patients appearing in both evaluation groups: 5
- Identical filenames across evaluation groups: 0
- Media-opacity patients also represented in training: 28
- Media-opacity patients absent from training: 25
- Identical filenames shared with training: 0

## Training-Overlap Subgroup Analysis

| Patient represented in training | Eyes | Referred | Uncertain | Referral rate |
|---|---:|---:|---:|---:|
| No | 35 | 28 | 4 | 80.00% |
| Yes | 28 | 26 | 3 | 92.86% |

The elevated referral rate is present even among patients absent from training.

## Reproducibility

The subgroup analysis uses the saved media-opacity predictions and dataset labels. No model inference or retraining is required.

Run the subgroup analysis from the repository root:

    python scripts/summarize_media_opacity_holdout.py

This generates results/task15/media_opacity_subgroups.csv and prints the patient-overlap and training-overlap statistics.

Run the automated tests:

    python -m pytest tests/test_media_opacity_holdout.py -v

## Model Provenance

Checkpoint SHA256:
9c4b9e7b4de308dd428af3f22a1eae0b5f3d857aa91464067c7e287b7dc910c7

Current settings SHA256:
420336fdfccac95f7a96555be24b1182361b943e21313d380e8e8c4cda04aa0c

Task 13 recorded settings SHA256:
d1d97e58e25d32892527db0ad459a7b9d555391e5abda924ff33f1700f14db71

The checkpoint hashes match. The settings hash in the prediction CSV (420336fd...) differs from the Task 13 hash (d1d97e58...) only because the file was hashed with Windows line endings (CRLF) on a local checkout. The content is identical: converting the committed file to CRLF reproduces the 420336fd... hash. The model used the same frozen settings as Task 13.

## Interpretation

The frozen cataract model referred 85.71% of cataract-negative media-opacity eyes, compared with 8.53% of cataract-negative internal-test eyes.

This substantial difference raises concern about a possible media-opacity or haze shortcut. However, the comparison is observational and does not establish causation.

## Limitations

- The internal-test cataract-negative group is not necessarily a clinically healthy control group.
- Five patients appear in both evaluation groups.
- Some holdout patients have fellow-eye representation in training.
- Other cohort differences may contribute to the referral-rate difference.
- Further blur and heatmap analyses are needed for the broader shortcut-safety assessment.

## Conclusion

The frozen cataract model demonstrates a substantially elevated referral rate on cataract-negative media-opacity holdout eyes. This is a potential safety concern requiring further investigation.
