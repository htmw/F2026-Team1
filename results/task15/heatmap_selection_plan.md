# SCRUM-99: Cataract Grad-CAM Image Selection Plan

Status: Defined before generating or examining SCRUM-99 heatmaps.

## Objective
Generate representative cataract Grad-CAM heatmaps to investigate which image regions contribute to the frozen model's cataract predictions.

Heatmaps are qualitative supporting evidence, not proof of a haze shortcut or disease localization.

## Frozen Model
- Architecture: Shared ResNet50 (DualNet).
- Seed: 42.
- Checkpoint: checkpoints/task11/shared/shared_seed_42_best.pt.
- Calibration: Existing frozen cataract Platt calibration.
- Decision threshold and uncertainty margin: Existing frozen settings.
- Grad-CAM target: model.backbone.features[7][-1].
- Gradient target: Raw cataract logit, not glaucoma logit.

## Data Sources
- Internal-test predictions: results/task13/internal_test/shared_cataract_seed_42_test.csv.
- Media-opacity predictions: results/task15/media_opacity_predictions.csv.
- Diagnosis labels: labels/eye_labels_task7.csv.
- Images: Preprocessed/ODIR/.

## Eligibility
Normal fundus:
- diagnosis_text equals "normal fundus".
- cataract, glaucoma, suspected_glaucoma, media_opacity, image_quality_flag, and exclusion equal 0.

Cataract-positive:
- diagnosis_text equals "cataract".
- cataract equals 1.
- media_opacity, image_quality_flag, and exclusion equal 0.

Media opacity:
- Use the SCRUM-97 media-opacity holdout prediction records.
- Preserve the original referral decisions.

## Predefined Selection Rule
1. Separate eligible images into the seven categories below.
2. Sort each category by filename in ascending lexicographic order.
3. Select the first three images from each category.
4. Do not replace images based on their heatmap appearance.
5. Record missing images or processing failures rather than silently substituting examples.

## Categories
| Group | Frozen Model Decision | Planned Images |
|---|---|---:|
| Normal fundus | No concern | 3 |
| Normal fundus | Refer | 3 |
| Normal fundus | Uncertain, refer | 3 |
| Cataract-positive | Refer | 3 |
| Media opacity | No concern | 3 |
| Media opacity | Refer | 3 |
| Media opacity | Uncertain, refer | 3 |
| Total | | 21 |

## Required Records
For every selected image, record:
- Patient ID and eye.
- Filename.
- Image group and diagnosis label.
- True cataract label.
- Calibrated cataract probability.
- Frozen model decision.
- Selection category and selection rank.
- Generated heatmap filename.
- Processing status.

## Interpretation Rules
- Examine whether highlighted regions include cloudy areas, image boundaries, or retinal structures.
- Do not interpret Grad-CAM as a definitive explanation of model behavior.
- Do not claim that highlighted regions establish cataract localization.
- Do not change the frozen model, calibration, thresholds, or image-selection criteria after examining heatmaps.
- Document unexpected observations, failures, and limitations.
