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
| ORIGA | 650 | 650 | 0 | 240 | 410 | 36.92% |
| DRISHTI-GS | 101 | 101 | 0 | 68 | 33 | 67.33% |

### Results by glaucoma label

| Dataset | Glaucoma eyes | Healthy eyes |
|---|---:|---:|
| ORIGA | 94/168 (56.0%) | 146/482 (30.3%) |
| DRISHTI-GS | 50/70 (71.4%) | 18/31 (58.1%) |

The peak lands in the optic disc more often on glaucoma eyes than
on healthy eyes in both datasets.

Machine-readable results are saved in:

`results/task16/glaucoma_optic_disc_hit_rates.csv`

## DRISHTI-GS Mask Threshold Sensitivity

| OD softmap threshold | Hits / evaluated | Hit rate |
|---|---:|---:|
| >= 1 | 70 / 101 | 69.31% |
| >= 128 (primary) | 68 / 101 | 67.33% |
| >= 255 | 65 / 101 | 64.36% |

The observed hit rate varies with the optic disc mask threshold.

## ORIGA Image 359 Annotation Alignment

ORIGA image 359 is included in the optic disc localization evaluation.

The original photograph and annotation are both 2048 pixels tall.
The photograph is 3085 pixels wide, while its annotation is
3072 pixels wide, giving a 13-pixel width difference.

To align the annotation with the photograph, the evaluation script
pads the annotation with 13 zero-valued columns on the right before
applying the existing fundus crop and resize procedure.

The team independently checked left-aligned, right-aligned, and
stretched annotation placements and reported that the Grad-CAM peak
falls inside the optic disc in each case.

Image 359 contributes one glaucoma-positive optic disc hit.
All 650 ORIGA images are evaluated, with zero exclusions.

## Interpretation

The observed Grad-CAM peak localization rates are 36.92% on ORIGA
and 67.33% on DRISHTI-GS using the specified optic disc masks.

The optic disc covers approximately 2.4% of the 512 x 512 image
in ORIGA and 3.7% in DRISHTI-GS, according to the team's review.
Under a uniformly random peak-location baseline, a randomly
placed peak would fall inside the optic disc approximately that
often. The observed localization rates are substantially higher.

The peak falls inside the optic disc more frequently for
glaucoma-positive eyes than healthy eyes in both datasets.

These results describe how often the strongest Grad-CAM activation
overlaps the annotated optic disc under this evaluation procedure.

They do not establish glaucoma diagnostic performance or prove
that the model relies causally on optic disc structures.

## Limitations

1. Grad-CAM provides approximate spatial explanations, not causal evidence.
2. A single peak coordinate does not describe the full activation distribution.
3. Results depend on annotation definitions and alignment.
4. The DRISHTI-GS primary threshold of 128 is an evaluation choice.
5. ORIGA image 359 uses 13-column right-padding to align its annotation; the original annotation width differs from the image.
6. Per-image Grad-CAM normalization does not make heatmap intensity
   directly comparable across different images.
7. The two datasets differ in image characteristics and annotation formats.
8. The reported hit rates are localization metrics, not classification metrics.

## Generated Heatmap Storage and Git Policy

The evaluation generated 751 PNG heatmap overlays:

- ORIGA: 650 PNG files, approximately 156.02 MB.
- DRISHTI-GS: 101 PNG files, approximately 24.47 MB.
- Combined PNG size: approximately 180.49 MB.

Fundus photographs and heatmap examples are permitted in the
repository, as demonstrated by existing dataset files and
the Task 15 cataract heatmaps.

The complete collection is intentionally kept outside Git
primarily because of its size. Committing approximately 180 MB
of generated PNGs would unnecessarily increase repository history.

The repository includes the generation and evaluation scripts,
CSV manifests, numerical results, and this findings report.

A representative glaucoma heatmap contact sheet was generated
for team review, presentation slides, and the project paper:

`results/task16/glaucoma_heatmap_contact_sheet.png`

The contact sheet contains eight examples arranged by dataset:

- ORIGA: glaucoma hit (036), glaucoma miss (037),
  healthy hit (004), and healthy miss (001).
- DRISHTI-GS: glaucoma hit (001), glaucoma miss (003),
  healthy hit (007), and healthy miss (009).

Hit and miss categories were determined using the same optic disc
localization criteria as the quantitative evaluation.

The contact sheet contains selected examples only and should not
be interpreted as a representative statistical sample.

### Complete Heatmap Archive on Google Drive

The complete collection of 751 generated glaucoma Grad-CAM PNG heatmaps (650 ORIGA and 101 DRISHTI-GS) is available here:

[Download SCRUM-62 Glaucoma Heatmaps ZIP](https://drive.google.com/file/d/1u33q_EUCgEziXSJy0zWo0UGzkFVWFhsT/view?usp=drive_link)

The ZIP archive is approximately 180.66 MB. Google Drive sharing is restricted to authorized teammates. The uploaded archive was successfully downloaded and opened for verification by the file owner.

The full PNG directories are excluded from Git to avoid adding approximately 180 MB of generated images. A representative eight-image contact sheet is retained in the repository for review and presentation purposes.

## Conclusion

The frozen shared glaucoma model produced 751 Grad-CAM heatmaps across
ORIGA and DRISHTI-GS.

Using the documented localization procedure, the optic disc
peak hit rate was 240/650 (36.92%) for ORIGA and 68/101 (67.33%)
for DRISHTI-GS.

All 650 ORIGA images were included, with image 359's annotation
right-padded by 13 columns to match the original photograph.

The peak falls inside the optic disc more often for glaucoma-positive
eyes than healthy eyes in both datasets. The observed rates are also
higher than the approximate uniformly random peak-location baselines.

These findings describe Grad-CAM localization, not glaucoma
classification accuracy or causal reliance on optic disc structures.
