# Single-disease and shared-model comparison

## Purpose

This comparison examines whether sharing one ResNet-50 backbone
for cataract and glaucoma improves performance compared with
training a separate model for each disease.

## Internal test results

The table uses the existing ODIR internal-test results.
Each model was trained with seeds 42, 43, and 44.
Values show mean AUROC and sample standard deviation across these seeds.

| Disease | Single model: mean AUROC ± SD | Shared model: mean AUROC ± SD | Shared minus single |
|---|---:|---:|---:|
| Cataract | 0.9910 ± 0.0036 | 0.9948 ± 0.0004 | +0.0038 |
| Glaucoma | 0.9241 ± 0.0178 | 0.9309 ± 0.0125 | +0.0068 |

The shared model has a slightly higher average AUROC for both diseases.
These differences alone do not establish a statistically significant improvement.

Source: [Internal test results](../task13/internal_results.md).


## External glaucoma results

These results use the frozen calibration and thresholds.
Values show mean AUROC and sample standard deviation across
seeds 42, 43, and 44.

| Dataset | Single model: mean AUROC ± SD | Shared model: mean AUROC ± SD | Shared minus single |
|---|---:|---:|---:|
| ORIGA | 0.7687 ± 0.0158 | 0.7487 ± 0.0156 | -0.0200 |
| DRISHTI-GS | 0.8846 ± 0.0205 | 0.8820 ± 0.0117 | -0.0026 |
| ACRIMA | 0.4078 ± 0.0952 | 0.5551 ± 0.0752 | +0.1473 |
| retina_dataset_2016 | 0.7411 ± 0.0541 | 0.7521 ± 0.0453 | +0.0110 |

The shared model has higher average AUROC on ACRIMA and
retina_dataset_2016, and lower average AUROC on ORIGA and DRISHTI-GS.
There is no consistent improvement across all external datasets.

Source: [External test results](../external/frozen_run_20261030/external_results.md).

## Conclusion

The shared model had a slightly higher average AUROC for both
diseases on the internal test. For external glaucoma testing,
it did better on ACRIMA and retina_dataset_2016, but worse on
ORIGA and DRISHTI-GS. So, sharing one backbone did not improve
the results on every dataset.

Both models had lower glaucoma AUROC on the external datasets
than on the internal test. ACRIMA was especially difficult.
Even though the shared model did better there, its average
AUROC was only 0.5551, which is close to chance.

These results do not show one model as the clear winner.
We compared three seeds, but we have not tested whether the
differences are statistically significant.

## Evaluation notes

- We used the saved test results without retraining the models.
- We kept the calibration and thresholds fixed.
- The standard deviation shows how much results varied across seeds.
- Internal confidence intervals were calculated by resampling patients.
  External intervals used images because patient IDs were unavailable.
- The datasets contain different images and patient groups.
  We cannot tell from these results alone why performance changed.