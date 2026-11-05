# External evaluation

Image-level bootstrap assumes independent images. Patient identifiers are unavailable, so fellow-eye dependence may make confidence intervals too narrow. The existing ODIR/retina overlap check detects identical files only, not resized or edited copies.

Frozen settings were applied without refitting. Referral metrics include uncertain eyes.
AUROC intervals describe image resampling, while seed SD describes variation across runs.

## ORIGA

| Disease | Model | Seed | AUROC (95% CI) | Sensitivity | Specificity | Referrals | Uncertain | Brier | ECE |
|---|---|---|---|---|---|---|---|---|---|
| glaucoma | single | 42 | 0.7795 (0.7393, 0.8173) | 61.3% | 77.8% | 210/650 | 20 | 0.2331 | 0.2329 |
| glaucoma | single | 43 | 0.7759 (0.7347, 0.8142) | 69.6% | 69.7% | 263/650 | 37 | 0.2274 | 0.2256 |
| glaucoma | single | 44 | 0.7506 (0.7069, 0.7912) | 53.6% | 79.3% | 190/650 | 20 | 0.2226 | 0.2201 |
| glaucoma | shared | 42 | 0.7665 (0.7244, 0.8056) | 69.6% | 68.5% | 269/650 | 28 | 0.2276 | 0.2258 |
| glaucoma | shared | 43 | 0.7419 (0.7006, 0.7821) | 81.0% | 56.8% | 344/650 | 47 | 0.2222 | 0.2166 |
| glaucoma | shared | 44 | 0.7377 (0.6900, 0.7819) | 51.2% | 83.2% | 167/650 | 34 | 0.2352 | 0.2349 |

Across seeds (mean ± sample SD):

- glaucoma, single: auroc: 0.7687 ± 0.0158; sensitivity: 0.6151 ± 0.0804; specificity: 0.7559 ± 0.0514; referral_rate: 0.3400 ± 0.0580; brier_calibrated: 0.2277 ± 0.0053
- glaucoma, shared: auroc: 0.7487 ± 0.0156; sensitivity: 0.6726 ± 0.1502; specificity: 0.6950 ± 0.1320; referral_rate: 0.4000 ± 0.1367; brier_calibrated: 0.2283 ± 0.0065

## DRISHTI-GS

| Disease | Model | Seed | AUROC (95% CI) | Sensitivity | Specificity | Referrals | Uncertain | Brier | ECE |
|---|---|---|---|---|---|---|---|---|---|
| glaucoma | single | 42 | 0.8659 (0.7792, 0.9325) | 90.0% | 45.2% | 80/101 | 2 | 0.4970 | 0.5631 |
| glaucoma | single | 43 | 0.9065 (0.8394, 0.9599) | 80.0% | 80.6% | 62/101 | 4 | 0.5751 | 0.6204 |
| glaucoma | single | 44 | 0.8816 (0.8090, 0.9411) | 82.9% | 83.9% | 63/101 | 4 | 0.4825 | 0.5539 |
| glaucoma | shared | 42 | 0.8687 (0.7940, 0.9291) | 77.1% | 74.2% | 62/101 | 1 | 0.5449 | 0.6016 |
| glaucoma | shared | 43 | 0.8903 (0.8151, 0.9528) | 77.1% | 80.6% | 60/101 | 4 | 0.5336 | 0.5915 |
| glaucoma | shared | 44 | 0.8871 (0.8113, 0.9472) | 67.1% | 90.3% | 50/101 | 7 | 0.5783 | 0.6225 |

Across seeds (mean ± sample SD):

- glaucoma, single: auroc: 0.8846 ± 0.0205; sensitivity: 0.8429 ± 0.0515; specificity: 0.6989 ± 0.2148; referral_rate: 0.6766 ± 0.1002; brier_calibrated: 0.5182 ± 0.0498
- glaucoma, shared: auroc: 0.8820 ± 0.0117; sensitivity: 0.7381 ± 0.0577; specificity: 0.8172 ± 0.0812; referral_rate: 0.5677 ± 0.0637; brier_calibrated: 0.5523 ± 0.0232

## ACRIMA

| Disease | Model | Seed | AUROC (95% CI) | Sensitivity | Specificity | Referrals | Uncertain | Brier | ECE |
|---|---|---|---|---|---|---|---|---|---|
| glaucoma | single | 42 | 0.3144 (0.2745, 0.3557) | 84.6% | 5.8% | 626/705 | 21 | 0.5312 | 0.5313 |
| glaucoma | single | 43 | 0.5048 (0.4611, 0.5481) | 12.9% | 94.2% | 69/705 | 39 | 0.5470 | 0.5485 |
| glaucoma | single | 44 | 0.4042 (0.3609, 0.4466) | 9.8% | 77.7% | 108/705 | 27 | 0.5542 | 0.5536 |
| glaucoma | shared | 42 | 0.5098 (0.4666, 0.5540) | 14.6% | 83.2% | 110/705 | 45 | 0.5540 | 0.5548 |
| glaucoma | shared | 43 | 0.6418 (0.6009, 0.6829) | 3.0% | 97.4% | 20/705 | 13 | 0.5556 | 0.5569 |
| glaucoma | shared | 44 | 0.5136 (0.4711, 0.5559) | 23.0% | 84.5% | 139/705 | 28 | 0.5471 | 0.5495 |

Across seeds (mean ± sample SD):

- glaucoma, single: auroc: 0.4078 ± 0.0952; sensitivity: 0.3577 ± 0.4231; specificity: 0.5922 ± 0.4697; referral_rate: 0.3797 ± 0.4410; brier_calibrated: 0.5441 ± 0.0118
- glaucoma, shared: auroc: 0.5551 ± 0.0752; sensitivity: 0.1355 ± 0.1002; specificity: 0.8835 ± 0.0787; referral_rate: 0.1272 ± 0.0880; brier_calibrated: 0.5522 ± 0.0045

## retina_dataset_2016

| Disease | Model | Seed | AUROC (95% CI) | Sensitivity | Specificity | Referrals | Uncertain | Brier | ECE |
|---|---|---|---|---|---|---|---|---|---|
| cataract | single | 42 | 0.9172 (0.8894, 0.9435) | 58.0% | 97.0% | 73/601 | 36 | 0.1231 | 0.1305 |
| cataract | single | 43 | 0.9226 (0.8900, 0.9510) | 69.0% | 94.2% | 98/601 | 52 | 0.1178 | 0.1268 |
| cataract | single | 44 | 0.9274 (0.8984, 0.9531) | 66.0% | 97.0% | 81/601 | 38 | 0.1085 | 0.1193 |
| cataract | shared | 42 | 0.9088 (0.8744, 0.9394) | 73.0% | 90.0% | 123/601 | 71 | 0.1140 | 0.1253 |
| cataract | shared | 43 | 0.8999 (0.8656, 0.9303) | 52.0% | 97.0% | 67/601 | 33 | 0.1339 | 0.1394 |
| cataract | shared | 44 | 0.9208 (0.8851, 0.9505) | 62.0% | 97.8% | 73/601 | 41 | 0.1177 | 0.1275 |
| glaucoma | single | 42 | 0.7721 (0.7128, 0.8284) | 75.2% | 68.6% | 233/601 | 30 | 0.1483 | 0.1439 |
| glaucoma | single | 43 | 0.7726 (0.7142, 0.8253) | 70.3% | 73.8% | 202/601 | 35 | 0.1462 | 0.1393 |
| glaucoma | single | 44 | 0.6786 (0.6183, 0.7354) | 46.5% | 73.4% | 180/601 | 26 | 0.1504 | 0.1461 |
| glaucoma | shared | 42 | 0.7604 (0.7022, 0.8125) | 72.3% | 62.4% | 261/601 | 42 | 0.1477 | 0.1426 |
| glaucoma | shared | 43 | 0.7927 (0.7357, 0.8427) | 75.2% | 72.6% | 213/601 | 27 | 0.1483 | 0.1433 |
| glaucoma | shared | 44 | 0.7032 (0.6369, 0.7630) | 75.2% | 51.0% | 321/601 | 61 | 0.1465 | 0.1359 |

Across seeds (mean ± sample SD):

- cataract, single: auroc: 0.9224 ± 0.0051; sensitivity: 0.6433 ± 0.0569; specificity: 0.9607 ± 0.0161; referral_rate: 0.1398 ± 0.0212; brier_calibrated: 0.1165 ± 0.0074
- cataract, shared: auroc: 0.9099 ± 0.0105; sensitivity: 0.6233 ± 0.1050; specificity: 0.9494 ± 0.0428; referral_rate: 0.1459 ± 0.0512; brier_calibrated: 0.1218 ± 0.0106
- glaucoma, single: auroc: 0.7411 ± 0.0541; sensitivity: 0.6403 ± 0.1535; specificity: 0.7193 ± 0.0289; referral_rate: 0.3411 ± 0.0443; brier_calibrated: 0.1483 ± 0.0021
- glaucoma, shared: auroc: 0.7521 ± 0.0453; sensitivity: 0.7426 ± 0.0171; specificity: 0.6200 ± 0.1081; referral_rate: 0.4409 ± 0.0900; brier_calibrated: 0.1475 ± 0.0009

No images were excluded. Missing cataract labels were not treated as negative labels.
The complete CSV includes both threshold-only and final-referral policies, raw/calibrated metrics,
confidence intervals and undefined-ratio reasons. Internal comparisons belong to Task 17.
