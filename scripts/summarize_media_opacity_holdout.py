"""Summarize SCRUM-97 media-opacity holdout results without model inference."""

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
LABELS_FILE = ROOT / "labels" / "eye_labels_task7.csv"
PREDICTIONS_FILE = ROOT / "results" / "task15" / "media_opacity_predictions.csv"
OUTPUT_FILE = ROOT / "results" / "task15" / "media_opacity_subgroups.csv"


def summarize():
    """Validate predictions and calculate patient-overlap subgroups."""
    labels = pd.read_csv(LABELS_FILE, dtype={"patient_id": str})
    predictions = pd.read_csv(PREDICTIONS_FILE, dtype={"patient_id": str})

    if len(predictions) != 63:
        raise ValueError("Expected exactly 63 media-opacity predictions.")

    if predictions["filename"].duplicated().any():
        raise ValueError("Duplicate prediction filenames detected.")

    if labels["filename"].duplicated().any():
        raise ValueError("Duplicate label filenames detected.")

    holdout = labels.loc[
        (labels["split"] == "holdout")
        & (labels["media_opacity"] == 1)
    ]

    if len(holdout) != 63:
        raise ValueError("Expected exactly 63 media-opacity holdout labels.")

    if set(predictions["filename"]) != set(holdout["filename"]):
        raise ValueError("Prediction filenames do not match the holdout.")

    if not (holdout["cataract"] == 0).all():
        raise ValueError("Media-opacity holdout contains cataract-positive eyes.")

    if not (predictions["true_label"] == 0).all():
        raise ValueError("Predictions contain cataract-positive labels.")

    merged = predictions.merge(
        holdout[["filename", "patient_id", "eye"]],
        on="filename",
        how="inner",
        validate="one_to_one",
        suffixes=("_prediction", "_label"),
    )

    if not (
        merged["patient_id_prediction"].astype(str)
        == merged["patient_id_label"].astype(str)
    ).all():
        raise ValueError("Patient IDs disagree between predictions and labels.")

    if not (
        merged["eye_prediction"] == merged["eye_label"]
    ).all():
        raise ValueError("Eye labels disagree between predictions and labels.")

    if not merged["is_referred"].isin([0, 1]).all():
        raise ValueError("Invalid referral values.")

    if not merged["is_uncertain"].isin([0, 1]).all():
        raise ValueError("Invalid uncertainty values.")

    train_patients = set(
        labels.loc[labels["split"] == "train", "patient_id"]
    )
    test_patients = set(
        labels.loc[(labels["split"] == "test") & (labels["cataract"] == 0), "patient_id"]
    )
    holdout_patients = set(holdout["patient_id"])

    merged["patient_in_training"] = merged[
        "patient_id_label"
    ].isin(train_patients)

    rows = []
    for in_training in [False, True]:
        group = merged.loc[merged["patient_in_training"] == in_training]
        eyes = len(group)
        referred = int(group["is_referred"].sum())
        uncertain = int(group["is_uncertain"].sum())

        rows.append({
            "patient_in_training": "Yes" if in_training else "No",
            "eyes": eyes,
            "referred": referred,
            "uncertain": uncertain,
            "referral_rate_percent": round(
                100 * referred / eyes, 2
            ) if eyes else 0.0,
        })

    summary = pd.DataFrame(rows)

    if int(summary["eyes"].sum()) != 63:
        raise ValueError("Subgroup eye counts do not total 63.")

    if int(summary["referred"].sum()) != 54:
        raise ValueError("Expected exactly 54 referred eyes.")

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    summary.to_csv(OUTPUT_FILE, index=False)

    print("Media-opacity eyes:", len(holdout))
    print("Media-opacity patients:", len(holdout_patients))
    print("Internal-test patients:", len(test_patients))
    print(
        "Patients overlapping internal test:",
        len(holdout_patients & test_patients),
    )
    print(
        "Patients represented in training:",
        len(holdout_patients & train_patients),
    )
    print(
        "Patients absent from training:",
        len(holdout_patients - train_patients),
    )
    print("Identical filenames shared with training:", len(
        set(holdout["filename"])
        & set(labels.loc[labels["split"] == "train", "filename"])
    ))
    print("Identical filenames shared with internal test:", len(
        set(holdout["filename"])
        & set(labels.loc[labels["split"] == "test", "filename"])
    ))
    print()
    print(summary.to_string(index=False))
    print()
    print("Saved:", OUTPUT_FILE)


if __name__ == "__main__":
    summarize()
