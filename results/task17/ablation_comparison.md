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