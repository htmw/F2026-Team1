"""SCRUM-98: Synthetic blur experiment using the frozen shared cataract model."""

import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from PIL import Image, ImageFilter
from torch.utils.data import DataLoader, Dataset
from torchvision import transforms

from calibrate_models import IMAGE_DIR, LABELS_FILE, file_sha256
from calibrate_shared_models import load_model
from evaluate_internal_test import (
    SETTINGS_FILE,
    calibrate_and_decide,
    settings_lookup,
)
from fundus_dataset import IMAGENET_MEAN, IMAGENET_STD


# ---------------------------------------------------------
# Project paths
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "results" / "task15"

PREDICTIONS_FILE = OUTPUT_DIR / "synthetic_blur_predictions.csv"
SUMMARY_FILE = OUTPUT_DIR / "synthetic_blur_summary.csv"
PLOT_FILE = OUTPUT_DIR / "synthetic_blur_plot.png"


# ---------------------------------------------------------
# Frozen model configuration
# ---------------------------------------------------------

MODEL_KIND = "shared"
DISEASE = "cataract"
DEPLOYMENT_SEED = 42


# ---------------------------------------------------------
# Predefined SCRUM-96 experiment settings
# ---------------------------------------------------------

BLUR_SIGMAS = (0, 1, 2, 4, 8)

EXPECTED_NORMAL_EYES = 396
EXPECTED_CATARACT_EYES = 38

IMAGE_SIZE = (512, 512)
BATCH_SIZE = 8
DEVICE = "cpu"


# ---------------------------------------------------------
# Approved validation preprocessing
# ---------------------------------------------------------

VALIDATION_TRANSFORM = transforms.Compose([
    transforms.ToTensor(),
    transforms.Normalize(
        mean=IMAGENET_MEAN,
        std=IMAGENET_STD,
    ),
])


# ---------------------------------------------------------
# Validation image selection
# ---------------------------------------------------------

def select_validation_images():
    """Select the predefined normal and cataract validation images."""

    labels = pd.read_csv(LABELS_FILE)

    required_columns = [
        "filename",
        "split",
        "diagnosis_text",
        "cataract",
        "glaucoma",
        "suspected_glaucoma",
        "media_opacity",
        "image_quality_flag",
        "exclusion",
    ]

    missing_columns = set(required_columns) - set(labels.columns)

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {sorted(missing_columns)}"
        )

    validation = labels[
        labels["split"] == "validation"
    ].copy()

    quality_flags = [
        "media_opacity",
        "image_quality_flag",
        "exclusion",
    ]

    normal_flags = [
        "cataract",
        "glaucoma",
        "suspected_glaucoma",
    ] + quality_flags

    normal = validation[
        (validation["diagnosis_text"] == "normal fundus")
        & validation[normal_flags].eq(0).all(axis=1)
    ].copy()

    cataract = validation[
        (validation["diagnosis_text"] == "cataract")
        & (validation["cataract"] == 1)
        & validation[quality_flags].eq(0).all(axis=1)
    ].copy()

    if len(normal) != EXPECTED_NORMAL_EYES:
        raise ValueError(
            f"Expected {EXPECTED_NORMAL_EYES} normal eyes, "
            f"found {len(normal)}."
        )

    if len(cataract) != EXPECTED_CATARACT_EYES:
        raise ValueError(
            f"Expected {EXPECTED_CATARACT_EYES} cataract eyes, "
            f"found {len(cataract)}."
        )

    selected = pd.concat(
        [normal, cataract],
        ignore_index=True,
    )

    if selected["filename"].duplicated().any():
        raise ValueError(
            "Duplicate filenames detected."
        )

    missing_images = [
        filename
        for filename in selected["filename"]
        if not (IMAGE_DIR / filename).is_file()
    ]

    if missing_images:
        raise FileNotFoundError(
            f"Missing {len(missing_images)} images: "
            f"{missing_images[:10]}"
        )

    return (
        normal.reset_index(drop=True),
        cataract.reset_index(drop=True),
    )


# ---------------------------------------------------------
# Synthetic Gaussian blur dataset
# ---------------------------------------------------------

class SyntheticBlurDataset(Dataset):
    """Load validation images and apply deterministic Gaussian blur."""

    def __init__(self, rows, sigma=0):
        self.rows = rows.reset_index(drop=True).copy()
        self.sigma = float(sigma)

        if self.sigma not in BLUR_SIGMAS:
            raise ValueError(
                f"Unsupported blur sigma: {self.sigma}"
            )

    def __len__(self):
        return len(self.rows)

    def __getitem__(self, index):
        row = self.rows.iloc[index]

        image_path = IMAGE_DIR / str(row["filename"])

        with Image.open(image_path) as source:
            image = source.convert("RGB")

        if image.size != IMAGE_SIZE:
            raise ValueError(
                f"Unexpected image size for {row['filename']}: "
                f"{image.size}"
            )

        # Apply Gaussian blur before tensor conversion
        # and ImageNet normalization.
        if self.sigma > 0:
            image = image.filter(
                ImageFilter.GaussianBlur(
                    radius=self.sigma
                )
            )

        image_tensor = VALIDATION_TRANSFORM(image)

        return {
            "image": image_tensor,
            "filename": str(row["filename"]),
        }


# ---------------------------------------------------------
# DataLoader creation
# ---------------------------------------------------------

def create_blur_loader(rows, sigma):
    """Create a deterministic DataLoader without shuffling."""

    dataset = SyntheticBlurDataset(
        rows,
        sigma=sigma,
    )

    return DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )


# ---------------------------------------------------------
# Frozen model inference
# ---------------------------------------------------------

def collect_cataract_logits(model, rows, sigma):
    """Collect cataract logits without changing model weights."""

    loader = create_blur_loader(rows, sigma)
    all_logits = []
    all_filenames = []

    model.eval()

    with torch.inference_mode():
        for batch in loader:
            images = batch["image"].to(DEVICE)

            outputs = model(images)

            if not isinstance(outputs, (tuple, list)):
                raise TypeError(
                    "Expected shared model to return multiple outputs."
                )

            cataract_logits = outputs[0]

            cataract_logits = (
                cataract_logits.detach()
                .cpu()
                .reshape(-1)
                .numpy()
            )

            all_logits.extend(cataract_logits.tolist())
            all_filenames.extend(batch["filename"])

    if len(all_logits) != len(rows):
        raise ValueError(
            f"Expected {len(rows)} predictions, "
            f"received {len(all_logits)}."
        )

    expected_filenames = rows["filename"].astype(str).tolist()

    if all_filenames != expected_filenames:
        raise ValueError(
            "Prediction filenames do not match dataset order."
        )

    return np.asarray(all_logits, dtype=np.float64)


# ---------------------------------------------------------
# Frozen Platt calibration
# ---------------------------------------------------------

def load_frozen_cataract_settings():
    """Load the approved frozen cataract calibration settings."""

    with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
        settings = json.load(file)

    lookup = settings_lookup(settings)

    key = (
        MODEL_KIND,
        DISEASE,
        DEPLOYMENT_SEED,
    )

    if key not in lookup:
        raise ValueError(
            f"Frozen calibration settings not found for {key}."
        )

    return settings, lookup[key]


def calibrate_cataract_logits(raw_logits, calibration_run):
    """Apply the existing frozen Platt calibration."""

    probabilities, decisions, uncertain, referred = (
        calibrate_and_decide(
            raw_logits,
            calibration_run,
        )
    )

    return {
        "probabilities": probabilities,
        "decisions": decisions,
        "uncertain": uncertain,
        "referred": referred,
    }


# ---------------------------------------------------------
# Synthetic blur experiment
# ---------------------------------------------------------

def run_synthetic_blur_experiment():
    """Evaluate synthetic blur using the frozen cataract model."""

    normal_rows, cataract_rows = select_validation_images()

    settings, calibration_run = load_frozen_cataract_settings()

    model, checkpoint = load_model(DEPLOYMENT_SEED)
    model = model.to(DEVICE)
    model.eval()

    prediction_rows = []

    def evaluate_group(rows, group, sigma):
        """Evaluate one group at one predefined blur level."""

        raw_logits = collect_cataract_logits(
            model,
            rows,
            sigma,
        )

        calibrated = calibrate_cataract_logits(
            raw_logits,
            calibration_run,
        )

        for index, row in rows.reset_index(drop=True).iterrows():
            prediction_rows.append({
                "group": group,
                "sigma": sigma,
                "patient_id": row["patient_id"],
                "eye": row["eye"],
                "filename": row["filename"],
                "true_label": int(row["cataract"]),
                "raw_logit": float(raw_logits[index]),
                "calibrated_probability": float(
                    calibrated["probabilities"][index]
                ),
                "decision": str(
                    calibrated["decisions"][index]
                ),
                "is_uncertain": bool(
                    calibrated["uncertain"][index]
                ),
                "is_referred": bool(
                    calibrated["referred"][index]
                ),
            })

    # Evaluate the same normal eyes at each blur level.
    for sigma in BLUR_SIGMAS:
        print(f"Evaluating normal eyes at sigma={sigma}...")

        evaluate_group(
            normal_rows,
            group="normal",
            sigma=sigma,
        )

    # Evaluate real cataract eyes without synthetic blur.
    print("Evaluating real cataract eyes at sigma=0...")

    evaluate_group(
        cataract_rows,
        group="real_cataract",
        sigma=0,
    )

    predictions = pd.DataFrame(prediction_rows)

    expected_predictions = (
        EXPECTED_NORMAL_EYES * len(BLUR_SIGMAS)
        + EXPECTED_CATARACT_EYES
    )

    if len(predictions) != expected_predictions:
        raise ValueError(
            f"Expected {expected_predictions} predictions, "
            f"found {len(predictions)}."
        )

    return predictions


# ---------------------------------------------------------
# Synthetic blur summary calculations
# ---------------------------------------------------------

def summarize_synthetic_blur(predictions):
    """Summarize calibrated probabilities and referral rates."""

    expected_groups = [
        ("normal", sigma, EXPECTED_NORMAL_EYES)
        for sigma in BLUR_SIGMAS
    ]

    expected_groups.append(
        ("real_cataract", 0, EXPECTED_CATARACT_EYES)
    )

    summary_rows = []

    for group, sigma, expected_count in expected_groups:
        subset = predictions[
            (predictions["group"] == group)
            & (predictions["sigma"] == sigma)
        ]

        if len(subset) != expected_count:
            raise ValueError(
                f"Expected {expected_count} predictions for "
                f"{group} at sigma={sigma}, found {len(subset)}."
            )

        probabilities = subset[
            "calibrated_probability"
        ].to_numpy(dtype=np.float64)

        if not np.isfinite(probabilities).all():
            raise ValueError(
                f"Invalid probabilities for {group} at sigma={sigma}."
            )

        summary_rows.append({
            "group": group,
            "sigma": sigma,
            "n_eyes": len(subset),
            "mean_probability": float(np.mean(probabilities)),
            "std_probability": float(
                np.std(probabilities, ddof=1)
            ),
            "median_probability": float(
                np.median(probabilities)
            ),
            "min_probability": float(
                np.min(probabilities)
            ),
            "max_probability": float(
                np.max(probabilities)
            ),
            "n_uncertain": int(
                subset["is_uncertain"].sum()
            ),
            "n_referred": int(
                subset["is_referred"].sum()
            ),
            "referral_rate": float(
                subset["is_referred"].mean()
            ),
        })

    summary = pd.DataFrame(summary_rows)

    normal_summary = summary[
        summary["group"] == "normal"
    ].set_index("sigma")

    baseline_mean = float(
        normal_summary.loc[0, "mean_probability"]
    )

    maximum_blur_mean = float(
        normal_summary.loc[8, "mean_probability"]
    )

    warning_triggered = maximum_blur_mean > baseline_mean

    print("\nSynthetic Blur Summary")
    print(
        summary[
            [
                "group",
                "sigma",
                "n_eyes",
                "mean_probability",
                "referral_rate",
            ]
        ].to_string(index=False)
    )

    print(
        "\nSCRUM-98 blur sensitivity warning:",
        "TRIGGERED" if warning_triggered else "NOT TRIGGERED",
    )

    return summary, warning_triggered


# ---------------------------------------------------------
# Synthetic blur comparison graph
# ---------------------------------------------------------

def plot_synthetic_blur_summary(summary, output_path):
    """Plot blur sensitivity against the real-cataract reference."""

    normal = summary[
        summary["group"] == "normal"
    ].sort_values("sigma")

    cataract = summary[
        summary["group"] == "real_cataract"
    ]

    if len(normal) != len(BLUR_SIGMAS):
        raise ValueError(
            "Missing normal-eye blur summary levels."
        )

    if len(cataract) != 1:
        raise ValueError(
            "Expected one real-cataract reference group."
        )

    sigma_values = normal["sigma"].to_numpy()
    mean_values = normal["mean_probability"].to_numpy()
    std_values = normal["std_probability"].to_numpy()

    cataract_reference = float(
        cataract["mean_probability"].iloc[0]
    )

    fig, ax = plt.subplots(figsize=(9, 6))

    ax.errorbar(
        sigma_values,
        mean_values,
        yerr=std_values,
        fmt="o-",
        linewidth=2,
        capsize=4,
        label="Normal eyes (mean ± SD)",
    )

    ax.axhline(
        y=cataract_reference,
        linestyle="--",
        linewidth=2,
        label="Real cataract (unblurred mean)",
    )

    ax.set_title(
        "SCRUM-98: Synthetic Blur Sensitivity"
    )
    ax.set_xlabel(
        "Gaussian Blur Sigma (pixels)"
    )
    ax.set_ylabel(
        "Mean Calibrated Cataract Probability"
    )

    ax.set_xticks(BLUR_SIGMAS)
    ax.set_ylim(0, 1)
    ax.grid(True, alpha=0.3)
    ax.legend()

    fig.tight_layout()
    fig.savefig(
        output_path,
        dpi=200,
        bbox_inches="tight",
    )

    plt.close(fig)


# ---------------------------------------------------------
# Safe output saving and main execution
# ---------------------------------------------------------

def main():
    """Run the experiment and save its outputs safely."""

    output_files = [
        PREDICTIONS_FILE,
        SUMMARY_FILE,
        PLOT_FILE,
    ]

    # Prevent accidental overwriting of existing results.
    existing_files = [
        path for path in output_files if path.exists()
    ]

    if existing_files:
        raise FileExistsError(
            "Refusing to overwrite existing experiment outputs: "
            + ", ".join(str(path) for path in existing_files)
        )

    print("SCRUM-98: Synthetic Blur Experiment")
    print("Model: Frozen shared ResNet50, seed 42")
    print(f"Blur levels: {BLUR_SIGMAS}")

    predictions = run_synthetic_blur_experiment()

    summary, warning_triggered = summarize_synthetic_blur(
        predictions
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    predictions.to_csv(
        PREDICTIONS_FILE,
        index=False,
    )

    summary.to_csv(
        SUMMARY_FILE,
        index=False,
    )

    plot_synthetic_blur_summary(
        summary,
        PLOT_FILE,
    )

    print("\nExperiment completed successfully.")
    print(f"Predictions: {PREDICTIONS_FILE}")
    print(f"Summary: {SUMMARY_FILE}")
    print(f"Plot: {PLOT_FILE}")

    print(
        "Blur sensitivity warning:",
        "TRIGGERED" if warning_triggered else "NOT TRIGGERED",
    )


if __name__ == "__main__":
    main()