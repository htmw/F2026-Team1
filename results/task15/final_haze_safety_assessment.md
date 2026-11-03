# SCRUM-100: Final Cataract Haze Safety Assessment

## Objective

This assessment combines the results of SCRUM-97 (media-opacity holdout), SCRUM-98 (synthetic blur), and SCRUM-99 (Grad-CAM) to evaluate whether the frozen cataract model may be sensitive to image haze, blur, or other nonclinical visual characteristics.

The assessment follows the predefined criteria in `results/task15/haze_check_plan.md`.

The purpose is to identify potential safety concerns, not to establish a causal explanation for the model's predictions.

## Model and Evaluation Configuration

- Model: Frozen shared ResNet50 with cataract and glaucoma heads.
- Deployment seed: 42.
- Checkpoint: `checkpoints/task11/shared/shared_seed_42_best.pt`.
- Checkpoint SHA-256: `9c4b9e7b4de308dd428af3f22a1eae0b5f3d857aa91464067c7e287b7dc910c7`.
- Calibration: Existing frozen Platt calibration.
- Decision policy: Existing frozen threshold and uncertainty margin.
- Model retraining: None.
- Evaluation sources: ODIR media-opacity holdout, ODIR validation images, and predefined Grad-CAM examples.

No model weights, calibration parameters, or decision thresholds were modified in response to the results.

## Summary of Findings

| Investigation | Main result | Assessment |
|---|---|---|
| SCRUM-97: Media-opacity holdout | 54/63 eyes referred (85.71%), versus 44/419 normal internal-test eyes (10.50%) | Predefined warning triggered |
| SCRUM-98: Synthetic blur | Mean calibrated probability increased from 1.85% at sigma 0 to 55.50% at sigma 8 | Predefined warning triggered |
| SCRUM-99: Grad-CAM | Recurring upper-boundary activation across 21 selected examples | Qualitative supporting observation |

Both predefined quantitative warning criteria were triggered.

These findings suggest possible sensitivity to image quality or other visual characteristics, but they do not establish a causal haze shortcut.

## SCRUM-97: Media-Opacity Holdout

The frozen cataract model was evaluated on 63 media-opacity holdout eyes from 53 patients. All 63 eyes had negative ground-truth cataract labels.

The recorded decisions were:

| Decision | Eyes | Percentage |
|---|---:|---:|
| Refer | 47 | 74.60% |
| Uncertain, refer | 7 | 11.11% |
| No concern | 9 | 14.29% |
| Total | 63 | 100.00% |

The total referral rate was 54/63 (85.71%), including uncertainty-based referrals.

The normal-fundus internal-test comparison group had 44 referrals among 419 eyes (10.50%), a difference of approximately 75.21 percentage points.

The broader cataract-negative internal-test group had 85 referrals among 996 eyes (8.53%).

### Training-Overlap Subgroups

| Patient represented in training | Eyes | Referred | Referral rate |
|---|---:|---:|---:|
| No | 35 | 28 | 80.00% |
| Yes | 28 | 26 | 92.86% |

The elevated referral rate remained present among eyes from patients not represented in training.

### Predefined Warning Decision

**SCRUM-97 warning: TRIGGERED.**

The media-opacity holdout referral rate exceeded the normal-fundus internal-test referral rate.

This observational comparison raises concern about possible haze-related sensitivity. However, differences between the evaluation groups may also contribute to the observed results.

The referral rate includes both strict `Refer` decisions and `Uncertain, refer` decisions. These categories should not be treated as identical to confirmed cataract diagnoses.

## SCRUM-98: Synthetic Blur

The experiment evaluated 396 normal validation eyes at five predefined Gaussian blur levels: sigma 0, 1, 2, 4, and 8 pixels.

The same images were evaluated at every blur level. An additional 38 unblurred real-cataract validation eyes provided a reference group.

The experiment produced 2,018 predictions.

### Results

| Image group | Sigma | Eyes | Mean calibrated probability | Referral rate |
|---|---:|---:|---:|---:|
| Normal | 0 | 396 | 0.018503 | 10.10% |
| Normal | 1 | 396 | 0.015406 | 11.62% |
| Normal | 2 | 396 | 0.030007 | 31.06% |
| Normal | 4 | 396 | 0.193993 | 93.18% |
| Normal | 8 | 396 | 0.555002 | 100.00% |
| Real cataract | 0 | 38 | 0.697405 | 97.37% |

Mean calibrated probability for normal eyes increased by approximately 53.65 percentage points between sigma 0 and sigma 8.

The response was not strictly monotonic: mean probability decreased at sigma 1 before increasing at sigma 2, 4, and 8.

The unblurred real-cataract reference group had a mean probability of 69.74%. This group was not matched to the normal-eye group and should not be treated as a clinical equivalence comparison.

### Predefined Warning Decision

**SCRUM-98 warning: TRIGGERED.**

The mean calibrated probability at sigma 8 exceeded the mean at sigma 0, satisfying the predefined criterion.

The results demonstrate sensitivity to strong synthetic Gaussian blur in the selected validation images.

They do not establish that synthetic blur reproduces clinical cataract haze or that the model uses haze as a causal shortcut.

## SCRUM-99: Grad-CAM Observations

SCRUM-99 generated 21 Grad-CAM heatmaps from predefined examples representing normal-fundus, cataract-positive, and media-opacity groups.

Visual examination showed recurring strong activation near the upper boundary of the circular fundus images across all three groups.

Some examples also showed broader or scattered activation within the retinal image.

Normal-fundus examples with `No concern`, `Refer`, and `Uncertain, refer` decisions displayed peripheral activation patterns. All three selected cataract-positive examples showed prominent upper-boundary activation.

The predefined selection plan requested correctly and incorrectly classified examples where available. All 31 eligible cataract-positive internal-test eyes were referred by the frozen model, so no misclassified cataract-positive examples were available for selection.

### Numerical Consistency

All 21 Grad-CAM examples retained their original referral decisions.

Three examples had historical-versus-current raw-logit differences greater than 0.0001. The maximum difference was approximately 0.00630760.

The maximum calibrated probability difference was approximately 0.00025112, or 0.0251 percentage points.

Controlled checks confirmed that Grad-CAM logits matched fresh inference in the current environment, the checkpoint hashes matched, and the image preprocessing tensors were identical.

The remaining historical-versus-current raw-logit differences have not been fully explained.

### Interpretation

Recurring boundary activation suggests that the model may respond to image-boundary characteristics or other visual patterns shared across diagnostic groups.

However, Grad-CAM provides approximate spatial explanations rather than causal evidence.

**SCRUM-99 assessment: Qualitative supporting observation only.**

The heatmaps do not independently establish a haze shortcut.

## Combined Interpretation

The three investigations provide complementary but different forms of evidence.

SCRUM-97 identified substantially elevated referrals in cataract-negative media-opacity holdout eyes.

SCRUM-98 demonstrated a strong response to increasing synthetic blur in normal validation images.

SCRUM-99 identified recurring image-boundary activation across selected examples from multiple diagnostic groups.

Together, these results raise a potential concern that the frozen cataract model may be sensitive to image degradation or nonclinical visual features.

However, the experiments do not isolate a single causal mechanism.

The observational media-opacity comparison may reflect differences between cohorts. Synthetic blur is not equivalent to clinical media opacity, and the strongest blur levels may produce unrealistic images. Grad-CAM activation patterns do not establish which visual characteristics caused a prediction.

The evidence is therefore consistent with a possible image-quality-related shortcut or robustness problem, but the specific mechanism remains unconfirmed.

## Conflicting and Qualifying Findings

Several observations limit a simple interpretation:

1. The synthetic-blur response was not strictly monotonic because mean probability decreased at sigma 1.
2. Grad-CAM boundary activation occurred across multiple diagnostic groups and prediction outcomes, not only in referred media-opacity images.
3. Some media-opacity eyes received `No concern` decisions despite the elevated overall referral rate.
4. The media-opacity subgroup without patient representation in training still showed elevated referrals, but this does not eliminate other cohort differences.
5. The real-cataract reference images were not matched to the normal validation images.
6. Small historical-versus-current raw-logit differences remain unexplained, although referral decisions were unchanged.

These findings should be reported alongside the triggered warnings rather than omitted.

## Limitations

- The media-opacity comparison is observational and cannot establish causation.
- The internal-test cataract-negative baseline includes eyes with other conditions; the normal-fundus baseline is a narrower comparison.
- Five patients appeared in both the media-opacity and internal-test evaluation groups.
- Some media-opacity patients had fellow-eye representation in training.
- Synthetic Gaussian blur does not reproduce every optical or biological characteristic of clinical media opacity.
- Strong blur levels may create images outside the model's training or clinical-use distribution.
- The synthetic-blur experiment used validation images, so its results are development evidence rather than independent clinical validation.
- Repeated predictions across blur levels came from the same 396 normal eyes and are not independent observations.
- The real-cataract reference group was not clinically matched.
- Grad-CAM observations were qualitative and limited to 21 predefined examples.
- Heatmap activation does not identify a causal feature or confirm disease localization.
- Each Grad-CAM heatmap is normalized independently to its own minimum and maximum. Color intensity indicates relative activation within an image, not the strength of cataract evidence. Colors cannot be compared directly across images, and red regions in No concern images do not imply strong cataract evidence.
- Small historical-versus-current raw-logit differences were observed without decision changes.
- These predefined warnings are experimental screening criteria, not clinical diagnostic thresholds.

## Safety Assessment and Recommendations

**Overall assessment: Potential haze-related shortcut or image-quality robustness concern; causal mechanism inconclusive.**

Both predefined quantitative warnings were triggered. The Grad-CAM observations provide additional qualitative context but do not prove a shortcut.

Recommended follow-up work:

1. Review these findings with the project team before drawing deployment or clinical-use conclusions.
2. Investigate whether image-boundary artifacts, acquisition conditions, or other image-quality characteristics contribute to predictions.
3. Consider additional controlled experiments that separate blur, boundary effects, and other image-quality changes.
4. Evaluate robustness on independent, clinically relevant datasets when suitable data and agreed evaluation procedures are available.
5. Preserve the frozen model and calibration settings during this assessment; any proposed changes should undergo separate development and validation.
6. Treat these findings as a safety concern requiring further evaluation rather than evidence of clinical diagnostic reliability.

## Conclusion

The SCRUM-61 cataract haze checks identified two triggered quantitative warning criteria.

The frozen cataract model referred 85.71% of cataract-negative media-opacity holdout eyes, compared with 10.50% of normal-fundus internal-test eyes.

Under strong synthetic blur, the mean calibrated cataract probability for normal validation eyes increased from 1.85% to 55.50%.

Grad-CAM heatmaps showed recurring upper-boundary activation across multiple diagnostic groups.

Together, these results suggest a possible image-quality-related shortcut or robustness concern.

**The findings do not establish that the model causally relies on haze or image boundaries to identify cataracts.**

Further controlled investigation and team review are recommended before any clinical-use conclusions.

## Supporting Artifacts

- `results/task15/haze_check_plan.md` - Predefined evaluation plan and warning criteria.
- `results/task15/media_opacity_findings.md` - SCRUM-97 findings.
- `results/task15/media_opacity_predictions.csv` - SCRUM-97 predictions.
- `results/task15/media_opacity_subgroups.csv` - SCRUM-97 subgroup analysis.
- `results/task15/synthetic_blur_findings.md` - SCRUM-98 findings.
- `results/task15/synthetic_blur_summary.csv` - SCRUM-98 aggregate results.
- `results/task15/synthetic_blur_predictions.csv` - SCRUM-98 predictions.
- `results/task15/synthetic_blur_plot.png` - SCRUM-98 visualization.
- `results/task15/cataract_heatmap_findings.md` - SCRUM-99 findings.
- `results/task15/cataract_heatmap_contact_sheet.png` - SCRUM-99 contact sheet.
- `results/task15/heatmap_generation_manifest.csv` - SCRUM-99 generation records.
- `results/task15/heatmap_selection_plan.md` - SCRUM-99 predefined selection criteria.
