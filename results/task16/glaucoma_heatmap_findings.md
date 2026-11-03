# SCRUM-62: Glaucoma Grad-CAM Optic Disc Localization Findings

## Objective

Evaluate whether the frozen glaucoma model's Grad-CAM peak activation
falls inside the annotated optic disc on the ORIGA and DRISHTI-GS datasets.

This is a spatial localization check, not a measurement of glaucoma
classification accuracy or a demonstration of clinical causation.

## Model and Evaluation Configuration

- Model: Frozen shared ResNet50 with separate disease classification heads.
- Model seed: 42.
- Checkpoint: `checkpoints/task11/shared/shared_seed_42_best.pt`.
- Explanation target: Glaucoma logit.
- Grad-CAM target: Final ResNet50 convolutional block.
- Input: Preprocessed 512 x 512 fundus images.
- Model weights: Unchanged.
- Frozen settings: `results/calibration/frozen_settings.json`.

## Datasets and Generated Outputs

| Dataset | Generated heatmaps | Manifest |
|---|---:|---|
| ORIGA | 650 | `origa_heatmap_manifest.csv` |
| DRISHTI-GS | 101 | `drishti_heatmap_manifest.csv` |
| **Total** | **751** | |

All 751 heatmaps were generated and validated.

The generation scripts are:

- `scripts/generate_glaucoma_heatmaps.py`
- `scripts/generate_drishti_glaucoma_heatmaps.py`

The reproducible localization evaluation script is:

- `scripts/evaluate_glaucoma_optic_disc_hits.py`

## Localization Evaluation Method

For each image, the evaluation identifies the peak Grad-CAM activation
coordinate on the 512 x 512 image grid.

The corresponding optic disc annotation is transformed using the same
fundus crop geometry as the image and resized using nearest-neighbor
interpolation.

A hit is counted when the peak activation coordinate falls inside
the resulting optic disc mask.

The hit rate is:

`optic_disc_hits / evaluated_images * 100`

### ORIGA Mask Definition

The optic disc region is defined as annotation values greater than zero.
This includes the optic cup as part of the disc region.

### DRISHTI-GS Mask Definition

The primary optic disc region is defined using the OD segmentation
softmap threshold of at least 128.

This threshold is an evaluation choice, not an official dataset threshold.

Sensitivity checks also use thresholds of at least 1 and at least 255.

## Primary Results

| Dataset | Generated | Evaluated | Excluded | Hits | Misses | Hit rate |
|---|---:|---:|---:|---:|---:|---:|
| ORIGA | 650 | 649 | 1 | 239 | 410 | 36.83% |
| DRISHTI-GS | 101 | 101 | 0 | 68 | 33 | 67.33% |

Machine-readable results are saved in:

`results/task16/glaucoma_optic_disc_hit_rates.csv`

## DRISHTI-GS Mask Threshold Sensitivity

| OD softmap threshold | Hits / evaluated | Hit rate |
|---|---:|---:|
| >= 1 | 70 / 101 | 69.31% |
| >= 128 (primary) | 68 / 101 | 67.33% |
| >= 255 | 65 / 101 | 64.36% |

The observed hit rate varies with the optic disc mask threshold.

## ORIGA Annotation Exclusion

ORIGA image 359 was excluded from the primary localization denominator.

Its original image has a height of 3085 pixels, while the corresponding
annotation has a height of 3072 pixels. Both have a width of 2048 pixels.

The annotation alignment cannot be established from matching dimensions
alone. Rather than silently applying an uncertain transformation, the
evaluation records this image as excluded.

This exclusion requires team review before the denominator and result
are treated as final.

All 650 heatmaps were generated; the exclusion affects only the
optic disc localization calculation.

## Interpretation

The observed Grad-CAM peak localization rates are 36.83% on ORIGA
and 67.33% on DRISHTI-GS using the specified masks.

These results describe how often the strongest activation location
overlaps the annotated optic disc under this evaluation procedure.

They do not establish glaucoma diagnostic performance or prove that
the model relies causally on optic disc structures.

## Limitations

1. Grad-CAM provides approximate spatial explanations, not causal evidence.
2. A single peak coordinate does not describe the full activation distribution.
3. Results depend on annotation definitions and alignment.
4. The DRISHTI-GS primary threshold of 128 is an evaluation choice.
5. ORIGA image 359 requires an annotation-alignment review.
6. Per-image Grad-CAM normalization does not make heatmap intensity
   directly comparable across different images.
7. The two datasets differ in image characteristics and annotation formats.
8. The reported hit rates are localization metrics, not classification metrics.

## Generated Heatmap Storage and Git Policy

The evaluation generated 751 PNG heatmap overlays:

- ORIGA: 650 PNG files, approximately 156.02 MB.
- DRISHTI-GS: 101 PNG files, approximately 24.47 MB.
- Combined PNG size: approximately 180.49 MB.

These PNGs contain fundus photograph overlays. Section 11.2 of the
project brief states that photographs must not be placed in Git.

For this reason, the complete PNG collection is intentionally excluded
from the SCRUM-104 Git commit. This also avoids adding approximately
180 MB of generated images to repository history.

The Git commit instead includes the generation and evaluation scripts,
CSV manifests, numerical results, and this findings report.

The complete PNG collection remains stored locally under
`results/task16/` and has not been deleted.

The team should confirm an approved storage or sharing location for
the generated overlays if the complete collection is required for
review or archival purposes.

The scripts and manifests support reproducibility when the authorized
source datasets, frozen checkpoint, and required environment are
available.

## Conclusion

The frozen shared glaucoma model produced 751 Grad-CAM heatmaps across
ORIGA and DRISHTI-GS.

Using the current documented localization procedure, the optic disc
peak hit rate was 239/649 (36.83%) for ORIGA and 68/101 (67.33%)
for DRISHTI-GS.

The results should be reviewed together with the mask definitions,
sensitivity analysis, and ORIGA image 359 exclusion before final approval.
