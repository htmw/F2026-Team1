
# Task 13 — Internal Test Results

## 1. Overview

This report summarizes the internal ODIR-5K test results for the Team EyeQ Dual Ocular Disease Screener. It compares the single-disease ResNet-50 models against the shared dual-head ResNet-50 model for cataract and glaucoma classification.

The internal test evaluation was performed once, after model training and calibration settings were frozen. This report uses previously committed evaluation results and does not involve additional model inference, threshold tuning, or bootstrap analysis.

## 2. Internal Test Dataset

| Characteristic | Value |
|---|---|
| Dataset | ODIR-5K internal test split |
| Test eyes | 1,036 |
| Unique patients | 522 |
| Cataract-positive eyes | 40 |
| Cataract-negative eyes | 996 |
| Glaucoma-positive eyes | 45 |
| Glaucoma-negative eyes | 991 |
| Training seeds evaluated | 42, 43, 44 |

The same internal test population was used for all model comparisons.

## 3. Mean AUROC Across Three Seeds

| Model | Disease | Seeds | Mean AUROC | Sample SD |
|---|---|---:|---:|---:|
| Single-head ResNet-50 | Cataract | 3 | 0.9910 | 0.0036 |
| Single-head ResNet-50 | Glaucoma | 3 | 0.9241 | 0.0178 |
| Shared dual-head ResNet-50 | Cataract | 3 | 0.9948 | 0.0004 |
| Shared dual-head ResNet-50 | Glaucoma | 3 | 0.9309 | 0.0125 |

These values are descriptive summaries across three training seeds. Sample standard deviation measures variability across seeds and must not be interpreted as a 95% confidence interval.

## 4. Per-Seed AUROC With 95% Confidence Intervals

| Model | Disease | Seed | AUROC | 95% CI |
|---|---|---:|---:|---|
| Single-head | Cataract | 42 | 0.9870 | [0.9782, 0.9943] |
| Single-head | Cataract | 43 | 0.9942 | [0.9887, 0.9984] |
| Single-head | Cataract | 44 | 0.9918 | [0.9857, 0.9967] |
| Single-head | Glaucoma | 42 | 0.9166 | [0.8765, 0.9498] |
| Single-head | Glaucoma | 43 | 0.9444 | [0.9127, 0.9685] |
| Single-head | Glaucoma | 44 | 0.9113 | [0.8409, 0.9657] |
| Shared dual-head | Cataract | 42 | 0.9948 | [0.9906, 0.9985] |
| Shared dual-head | Cataract | 43 | 0.9953 | [0.9912, 0.9981] |
| Shared dual-head | Cataract | 44 | 0.9945 | [0.9901, 0.9978] |
| Shared dual-head | Glaucoma | 42 | 0.9207 | [0.8764, 0.9591] |
| Shared dual-head | Glaucoma | 43 | 0.9449 | [0.9108, 0.9720] |
| Shared dual-head | Glaucoma | 44 | 0.9272 | [0.8777, 0.9670] |

All values are rounded to four decimal places for readability. Full-precision results are preserved in the original CSV files.

## 5. Confidence Interval Methodology

The previously completed AUROC analysis used patient-cluster bootstrap resampling with 2,000 valid replicates for each model, disease, and seed combination.

Patient-level resampling accounts for the possibility that two eyes from the same patient are statistically dependent.

The confidence intervals in Section 4 represent uncertainty for individual model-seed evaluations. They are not confidence intervals for the three-seed mean AUROC.

No new bootstrap calculations were performed for this report.

## 6. Interpretation

The shared dual-head model achieved a slightly higher mean AUROC than the corresponding single-head model for both diseases:

- **Cataract:** 0.9948 (shared) versus 0.9910 (single).
- **Glaucoma:** 0.9309 (shared) versus 0.9241 (single).

These results describe performance on the internal ODIR-5K test split only.

The observed differences do not, by themselves, establish statistically significant improvements or performance on independent external datasets. Formal ablation conclusions and external validation should be reported separately.

## 7. Source Files and Reproducibility

The results in this report were transcribed and rounded from the existing committed artifacts:

- [per_seed_auc_ci.csv](internal_auc_ci/per_seed_auc_ci.csv) — Full-precision AUROC and 95% confidence intervals for all 12 combinations.
- [seed_summary.csv](internal_auc_ci/seed_summary.csv) — Mean AUROC and sample standard deviation across seeds.
- [analysis_manifest.json](internal_auc_ci/analysis_manifest.json) — AUROC analysis provenance and configuration.
- [run_manifest.json](internal_test/run_manifest.json) — Original internal evaluation run manifest.
- [Internal test prediction files](internal_test/) — Prediction CSV files from the one-time internal evaluation.

The original per-seed CSV also records checkpoint SHA-256 and frozen-settings SHA-256 fingerprints, along with bootstrap validity counts.

This report is a presentation of existing results. It does not modify the original predictions, analysis files, checkpoints, or evaluation methodology.
