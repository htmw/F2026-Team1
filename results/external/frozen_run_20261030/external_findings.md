# External evaluation findings

This file supplements the generated results for the frozen run in this folder. The generated files (`predictions.csv`, `metrics.csv`, `calibration_bins.csv`, and `external_results.md`) are unchanged; their hashes are recorded in `run_manifest.json`.

## Run provenance

- Code commit used for the run: `cd357921e6e47a3982751adf42a2afe009330f8c`
- Run time: 30 October 2026, 15:18 to 16:49 UTC
- Device: CPU; batch size 8; no shuffling
- Frozen settings: `results/calibration/frozen_settings.json` (SHA-256 `d1d97e58e25d32892527db0ad459a7b9d555391e5abda924ff33f1700f14db71`)
- Protocol: `documents/evaluation/external_validation_protocol.md` (SHA-256 `8ff2d9afec94a0e3fad5fe7ef8250271a4c280ffa8fd3af9a1c893bfa4d24470`)
- Software: torch 2.14.0, torchvision 0.29.0, numpy 2.5.3, scikit-learn 1.9.1, and Pillow 12.3.0
- Input, checkpoint, script, and output hashes are recorded in `run_manifest.json`.

## Either-disease referrals on retina_dataset_2016

A photo is referred if either the cataract or glaucoma output is `Refer` or `Uncertain, refer`. This is the only external dataset with labels for both diseases. Of its 601 labeled photos, 201 have cataract or glaucoma labels and 400 are other photos (300 normal and 100 with other retinal diseases).

| Model | Seed | Photos referred | Cataract or glaucoma photos referred (of 201) | Other photos referred (of 400) |
|---|---:|---:|---:|---:|
| single | 42 | 251/601 | 153 | 98 |
| single | 43 | 267/601 | 147 | 120 |
| single | 44 | 208/601 | 123 | 85 |
| shared | 42 | 313/601 | 161 | 152 |
| shared | 43 | 272/601 | 147 | 125 |
| shared | 44 | 325/601 | 165 | 160 |

These counts were recomputed by grouping `predictions.csv` by photo and counting a photo once if either disease output referred it.

## Calibration summary for shared seed 42

| Dataset | Disease | Positive-label share | Mean calibrated probability | Brier | ECE |
|---|---|---:|---:|---:|---:|
| ORIGA | glaucoma | 0.258 | 0.034 | 0.228 | 0.226 |
| DRISHTI-GS | glaucoma | 0.693 | 0.091 | 0.545 | 0.602 |
| ACRIMA | glaucoma | 0.562 | 0.007 | 0.554 | 0.555 |
| retina_dataset_2016 | cataract | 0.166 | 0.041 | 0.114 | 0.125 |
| retina_dataset_2016 | glaucoma | 0.168 | 0.025 | 0.148 | 0.143 |

Calibration bins for every dataset, model, and seed are in `calibration_bins.csv`.

## Findings and limitations

- Across all 30 dataset, disease, model, and seed combinations, the mean calibrated probability is below the observed positive-label share. Calibration fitted on the ODIR validation split did not transfer as reliable risk estimates to these external sets. AUROC measures ranking and is not changed by probability calibration; referrals use the frozen decision thresholds and abstention margins.
- ACRIMA glaucoma AUROC ranges from 0.31 to 0.64 across models and seeds, so ranking is near or below chance in most runs. A possible explanation is that ACRIMA images are tight optic-disc crops rather than full fundus photographs; this result does not establish the cause.
- DRISHTI-GS glaucoma AUROC ranges from 0.87 to 0.91, while calibration is poor (Brier about 0.5 and ECE about 0.6). Its positive-label share is 69%, which differs substantially from the ODIR validation distribution used for calibration.
- ORIGA and retina_dataset_2016 glaucoma AUROC are moderate, ranging from 0.68 to 0.79.
- retina_dataset_2016 cataract AUROC ranges from 0.90 to 0.93. It is the only external cataract dataset, so this finding is based on one dataset.
- No images were excluded from the evaluation. Missing cataract labels were not treated as negative labels. The overlap check detects identical files only, not resized or edited copies. Image-level bootstrap intervals assume independent images; unavailable patient identifiers mean fellow-eye dependence could make intervals too narrow.
- Comparison against internal-test AUROC is tracked separately in Task 17 (SCRUM-63), as specified by the protocol.
