"""SCRUM-97: Evaluate media-opacity holdout eyes using frozen shared model."""

import json
from pathlib import Path

import pandas as pd
import torch
from torch.utils.data import DataLoader

from calibrate_models import IMAGE_DIR, LABELS_FILE, file_sha256
from calibrate_shared_models import load_model
from evaluate_internal_test import (
    SETTINGS_FILE,
    calibrate_and_decide,
    make_prediction_rows,
    settings_lookup,
)
from fundus_dataset import FundusDataset, get_validation_transform


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "results" / "task15"
PREDICTIONS_FILE = OUTPUT_DIR / "media_opacity_predictions.csv"

EXPECTED_MEDIA_OPACITY_EYES = 63
DEPLOYMENT_SEED = 42
MODEL_KIND = "shared"
DISEASE = "cataract"
BATCH_SIZE = 8


def build_media_opacity_loader():
    """Load only media-opacity holdout eyes with approved transforms."""
    dataset = FundusDataset(
        labels_csv=LABELS_FILE,
        image_dir=IMAGE_DIR,
        split="holdout",
        transform=get_validation_transform(),
    )

    if "media_opacity" not in dataset.labels.columns:
        raise ValueError("Missing media_opacity column.")

    dataset.labels = dataset.labels[
        dataset.labels["media_opacity"] == 1
    ].reset_index(drop=True)

    if len(dataset) != EXPECTED_MEDIA_OPACITY_EYES:
        raise ValueError(
            f"Expected {EXPECTED_MEDIA_OPACITY_EYES} media-opacity eyes, "
            f"found {len(dataset)}."
        )

    if not (dataset.labels["cataract"] == 0).all():
        raise ValueError(
            "Expected all media-opacity eyes to be cataract-negative."
        )

    if dataset.labels["filename"].duplicated().any():
        raise ValueError("Duplicate media-opacity filenames detected.")

    loader = DataLoader(
        dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    return loader, dataset.labels


def collect_media_opacity_logits(loader, labels):
    """Score media-opacity eyes using the frozen shared seed 42 model."""
    model, _checkpoint = load_model(DEPLOYMENT_SEED)

    model.to("cpu")
    model.eval()

    raw_logits = []
    observed_names = []

    with torch.inference_mode():
        for batch in loader:
            images = batch["image"].to("cpu")
            names = list(batch["filename"])

            outputs = model(images)

            if not isinstance(outputs, (tuple, list)) or len(outputs) != 2:
                raise ValueError(
                    "Expected cataract and glaucoma outputs."
                )

            cataract_logits = outputs[0].reshape(-1)

            if cataract_logits.numel() != len(names):
                raise ValueError("Unexpected cataract output shape.")

            if not torch.isfinite(cataract_logits).all():
                raise ValueError("Nonfinite cataract predictions.")

            raw_logits.extend(
                cataract_logits.detach().cpu().tolist()
            )
            observed_names.extend(names)

    expected_names = labels["filename"].tolist()

    if observed_names != expected_names:
        raise ValueError(
            "Prediction order does not match label order."
        )

    if len(raw_logits) != EXPECTED_MEDIA_OPACITY_EYES:
        raise ValueError(
            f"Expected {EXPECTED_MEDIA_OPACITY_EYES} predictions, "
            f"received {len(raw_logits)}."
        )

    return raw_logits


def build_media_opacity_predictions(raw_logits, labels):
    """Apply frozen cataract settings and build per-eye prediction records."""
    with SETTINGS_FILE.open("r", encoding="utf-8") as handle:
        settings = json.load(handle)

    deployment = settings["deployment"]

    if (
        deployment["model_kind"] != MODEL_KIND
        or int(deployment["seed"]) != DEPLOYMENT_SEED
    ):
        raise ValueError("Unexpected frozen deployment configuration.")

    runs = settings_lookup(settings)
    run_key = (MODEL_KIND, DISEASE, DEPLOYMENT_SEED)

    if run_key not in runs:
        raise ValueError("Approved cataract calibration run not found.")

    run = runs[run_key]

    if len(raw_logits) != EXPECTED_MEDIA_OPACITY_EYES:
        raise ValueError("Unexpected number of raw logits.")

    if len(labels) != EXPECTED_MEDIA_OPACITY_EYES:
        raise ValueError("Unexpected number of label records.")

    settings_hash = file_sha256(SETTINGS_FILE)

    records = make_prediction_rows(
        test_rows=labels.to_dict(orient="records"),
        raw_logits=raw_logits,
        run=run,
        settings_hash=settings_hash,
    )

    if len(records) != EXPECTED_MEDIA_OPACITY_EYES:
        raise ValueError("Unexpected number of prediction records.")

    return records


def main():
    """Run the frozen media-opacity holdout evaluation."""
    import csv

    if PREDICTIONS_FILE.exists():
        raise FileExistsError(
            f"Predictions already exist: {PREDICTIONS_FILE}. "
            "Refusing to overwrite the saved evaluation."
        )

    loader, labels = build_media_opacity_loader()
    raw_logits = collect_media_opacity_logits(loader, labels)
    records = build_media_opacity_predictions(raw_logits, labels)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with PREDICTIONS_FILE.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=list(records[0].keys()),
        )
        writer.writeheader()
        writer.writerows(records)

    referred = sum(int(row["is_referred"]) for row in records)

    print("PASS: Media-opacity evaluation completed")
    print("Evaluated eyes:", len(records))
    print("Referred eyes:", referred)
    print("Referral rate:", f"{100 * referred / len(records):.2f}%")
    print("Saved predictions:", PREDICTIONS_FILE)


if __name__ == "__main__":
    main()
