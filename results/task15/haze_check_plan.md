# SCRUM-96: Cataract Haze Check Plan

Status: Prepared before running the haze experiments.

## Purpose
Check whether the cataract model might be identifying image haze or blur as a sign of cataract, even when cataract is not confirmed.

## Media-opacity comparison (SCRUM-97)
- Evaluate all 63 media-opacity holdout eyes.
- Report a separate result for eyes whose fellow eye was not used in training.
- Compare cataract-positive rates with normal eyes from the internal-test set.
- Record the number of positive predictions, total images, and percentages.
- A higher positive rate for media-opacity eyes than normal eyes will be considered a possible haze-related warning.
- This comparison alone cannot prove that the model uses a haze shortcut.

## Synthetic-blur experiment (SCRUM-98)
- Apply increasing amounts of blur to normal-eye images.
- Record how the cataract prediction scores change.
- Compare these responses with scores from real cataract images.
- A consistent increase in cataract scores as blur increases will be considered a possible sign of blur sensitivity.
- Report unexpected or inconsistent results as well.

## Cataract heatmaps (SCRUM-99)
- Generate heatmaps to examine which image regions influence cataract predictions.
- Look for attention around cloudy regions, image boundaries, or retinal structures.
- Treat heatmaps as supporting observations rather than proof of a shortcut.

## Evaluation rules
- Do not change model weights, thresholds, or calibration based on holdout results.
- Use the final model settings agreed upon by the team.
- Coordinate internal-test results with SCRUM-57.
- Record processing failures and limitations.
- Document the exact blur levels and image selection before running the experiment.

## Final comparison (SCRUM-100)
Compare the media-opacity results, synthetic-blur response, and heatmap observations against the criteria written above. Report whether the findings suggest a possible haze shortcut or remain inconclusive.

## Predefined synthetic-blur settings
- Input: Preprocessed 512 x 512 RGB fundus images.
- Gaussian blur sigma values (pixels): 0, 1, 2, 4, 8.
- Sigma 0 means no additional blur.
- Apply blur to the RGB image before tensor conversion and ImageNet normalization.
- Use the same selected images at every blur level.
- Do not change blur levels after examining model predictions.
- These blur levels are experimental choices, not clinical thresholds.

## Predefined image-selection criteria for SCRUM-98
- Dataset: Validation split only for the initial synthetic-blur experiment.
- Normal group: diagnosis_text exactly "normal fundus"; cataract, glaucoma, suspected_glaucoma, media_opacity, image_quality_flag, and exclusion all equal 0.
- Real cataract group: diagnosis_text exactly "cataract"; cataract equals 1; media_opacity, image_quality_flag, and exclusion all equal 0.
- Eligible normal images: 396.
- Eligible real cataract images: 38.
- Use all eligible images rather than selecting examples based on model predictions.
- Apply every predefined blur level to the same normal-eye images.
- Use the real cataract images as a reference group.
- Treat validation results as development evidence, not independent test performance.
- Do not change image-selection criteria after examining predictions.
- Final evaluation dataset and model settings must be agreed upon before reporting final results.

## Predefined interpretation criteria
- SCRUM-97 warning: The cataract-positive percentage is higher in media-opacity holdout eyes than in internal-test normal eyes, using the agreed frozen model and threshold.
- SCRUM-98 warning: The mean cataract probability for normal validation eyes at Gaussian blur sigma 8 is greater than at sigma 0.
- Report mean scores at sigma 0, 1, 2, 4, and 8, including non-monotonic changes and individual variation.
- Compare the blurred normal-eye scores with the unblurred real-cataract reference group.
- SCRUM-99: Heatmaps are qualitative supporting evidence only, not independent proof of a haze shortcut.
- SCRUM-100: Report each warning separately, discuss conflicting findings, and avoid claiming causation from these checks alone.
- These are predefined experimental warning criteria, not clinical diagnostic thresholds.
