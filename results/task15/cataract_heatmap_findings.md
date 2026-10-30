# SCRUM-99: Cataract Grad-CAM Heatmap Findings

## Objective

Investigate which image regions influence the frozen cataract model's predictions and assess whether the observed activation patterns provide supporting evidence of possible haze-related shortcut behavior.

Grad-CAM is used for qualitative interpretation only. Heatmaps do not establish causation or identify clinical disease locations.

## Model and Evaluation Configuration

- Model: Frozen shared ResNet50 with separate cataract and glaucoma classification heads.
- Model seed: 42.
- Checkpoint: `checkpoints/task11/shared/shared_seed_42_best.pt`.
- Target: Final ResNet50 convolutional block.
- Explanation target: Cataract logit.
- Input: Preprocessed 512 × 512 RGB fundus images.
- Preprocessing: Existing validation transform with ImageNet normalization.
- Model weights: Unchanged.
- Calibration and decision thresholds: Unchanged.

## Predefined Image Selection

Images were selected according to `results/task15/heatmap_selection_plan.md`, before examining their heatmaps.

The reproducible selection script is `scripts/select_cataract_heatmap_images.py`.

A total of 21 images were selected across seven categories, with three images per category:

| Group | Decision Category | Images |
|---|---|---:|
| Normal fundus | No concern | 3 |
| Normal fundus | Refer | 3 |
| Normal fundus | Uncertain, refer | 3 |
| Cataract-positive | Refer | 3 |
| Media opacity | No concern | 3 |
| Media opacity | Refer | 3 |
| Media opacity | Uncertain, refer | 3 |
| **Total** | | **21** |

The selected image IDs, prediction outcomes, and selection ranks are recorded in `results/task15/heatmap_selected_images.csv`.

## Generated Outputs

- Individual Grad-CAM overlays: 21 images.
- Generation manifest: `results/task15/heatmap_generation_manifest.csv`.
- Contact sheet: `results/task15/cataract_heatmap_contact_sheet.png`.

All 21 heatmaps were generated successfully.

Verification confirmed that the output files exist and have valid dimensions.

## Qualitative Observations

Visual examination of the 21-image contact sheet revealed recurring strong activation near the upper boundary of the circular fundus images.

This pattern was observed across normal-fundus, cataract-positive, and media-opacity examples.

Some heatmaps also showed broader or scattered activation within the fundus region.

### Normal Fundus

Normal-fundus images classified as No concern frequently showed localized peripheral activation.

Normal-fundus images classified as Refer or Uncertain, refer showed upper-boundary activation alongside additional internal activation in several examples.

### Cataract-Positive

All three selected cataract-positive examples showed prominent activation near the upper image boundary.

Some examples also showed broader activation within the fundus image.

### Media Opacity

Media-opacity examples displayed peripheral activation, often concentrated near the upper image boundary.

Several examples classified as Refer showed broader activation across visually hazy regions.

These observations are descriptive and were not established through quantitative localization measurements.

## Comparison With Other Haze Checks

### SCRUM-97: Media-Opacity Holdout

The media-opacity evaluation reported 54 referrals among 63 holdout eyes, including uncertain referrals, corresponding to 85.71%.

### SCRUM-98: Synthetic Blur

The mean calibrated cataract probability for normal validation eyes increased from 1.85% at Gaussian blur sigma 0 to 55.50% at sigma 8.

The predefined synthetic-blur sensitivity warning was triggered.

### SCRUM-99: Grad-CAM

The heatmaps show recurring activation near image boundaries and, in some cases, broader activation across retinal regions.

These observations provide qualitative context for the earlier findings but do not independently demonstrate a haze shortcut.

## Numerical Consistency Verification

All 21 Grad-CAM predictions retained their original referral decisions.

Three images showed raw-logit differences greater than 0.0001 when compared with historical internal-test predictions:

| Image | Absolute Raw-Logit Difference |
|---|---:|
| `100_right.jpg` | 0.00125694 |
| `1013_left.jpg` | 0.00630760 |
| `103_right.jpg` | 0.00148106 |

The maximum calibrated probability difference was approximately 0.00025112, equivalent to 0.0251 percentage points.

Controlled checks confirmed:

- Grad-CAM logits matched fresh inference on the current Windows environment.
- The frozen checkpoint SHA-256 hashes matched.
- Direct PIL preprocessing and the existing dataset loader produced identical tensors.
- Changing gradient tracking, CPU thread count, or batch size did not reproduce the historical discrepancy.
- The historical internal-test CSV matched the SHA-256 recorded in its original evaluation manifest.

The historical evaluation ran on macOS ARM64 with Python 3.11.9 and PyTorch 2.14.1, while the current evaluation ran on Windows with different software versions.

Environment-related floating-point differences are a possible explanation, but the exact cause remains unconfirmed.

Historical prediction records were preserved.

## Interpretation

The repeated upper-boundary activation suggests that the model may respond to image-boundary characteristics or other visual patterns shared across diagnostic groups.

Together with the media-opacity and synthetic-blur results, this warrants further investigation of possible image-quality-related shortcut behavior.

However, these observations do not prove that the model relies on haze, image boundaries, or other nonclinical features to identify cataracts.

## Limitations

1. Grad-CAM provides approximate spatial explanations rather than causal evidence.
2. The analysis includes only 21 predefined examples.
3. Activation patterns were examined qualitatively rather than quantified.
4. Image-boundary activation may reflect several possible visual characteristics.
5. Synthetic Gaussian blur does not fully represent clinical cataract-related haze.
6. Small historical-versus-current raw-logit differences remain unexplained.
7. The selected examples do not establish population-level localization behavior.

## Conclusion

The SCRUM-99 heatmaps show recurring upper-boundary activation across normal, cataract-positive, and media-opacity examples.

These patterns provide supporting qualitative observations for the SCRUM-61 cataract haze shortcut safety investigation.

The combined findings from SCRUM-97, SCRUM-98, and SCRUM-99 suggest possible sensitivity to image quality or nonclinical visual features, but they do not establish causation.

Final interpretation should be completed under SCRUM-100 using the predefined evaluation criteria.