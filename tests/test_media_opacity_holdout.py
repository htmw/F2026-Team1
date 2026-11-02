"""Tests for SCRUM-97 media-opacity holdout evaluation.

Run from the repository root:
    python -m pytest tests/test_media_opacity_holdout.py -v
"""

from pathlib import Path

import pandas as pd
import pytest


ROOT = Path(__file__).resolve().parents[1]
PREDICTIONS_FILE = ROOT / "results" / "task15" / "media_opacity_predictions.csv"
LABELS_FILE = ROOT / "labels" / "eye_labels_task7.csv"
SUBGROUPS_FILE = ROOT / "results" / "task15" / "media_opacity_subgroups.csv"


@pytest.fixture(scope="module")
def evaluation_data():
    """Load the committed evaluation data."""
    predictions = pd.read_csv(
        PREDICTIONS_FILE, dtype={"patient_id": str}
    )
    labels = pd.read_csv(
        LABELS_FILE, dtype={"patient_id": str}
    )
    return predictions, labels


def test_media_opacity_holdout_size_and_labels(evaluation_data):
    """All 63 predictions must match cataract-negative holdout eyes."""
    predictions, labels = evaluation_data

    assert len(predictions) == 63
    assert predictions["filename"].is_unique
    assert labels["filename"].is_unique
    assert (predictions["true_label"] == 0).all()

    holdout = labels.loc[
        (labels["split"] == "holdout")
        & (labels["media_opacity"] == 1)
    ]

    assert len(holdout) == 63
    assert (holdout["cataract"] == 0).all()
    assert set(predictions["filename"]) == set(holdout["filename"])


def test_media_opacity_referral_counts(evaluation_data):
    """Check the frozen evaluation's saved referral decisions."""
    predictions, _ = evaluation_data

    assert predictions["is_referred"].isin([0, 1]).all()
    assert predictions["is_uncertain"].isin([0, 1]).all()

    assert int(predictions["is_referred"].sum()) == 54
    assert int(predictions["is_uncertain"].sum()) == 7
    assert int((predictions["is_referred"] == 0).sum()) == 9


def test_training_overlap_subgroups(evaluation_data):
    """Verify the 28/35 split directly from labels and predictions."""
    predictions, labels = evaluation_data

    training_patients = set(
        labels.loc[labels["split"] == "train", "patient_id"]
    )

    merged = predictions.merge(
        labels[["filename", "patient_id"]],
        on="filename",
        how="inner",
        validate="one_to_one",
        suffixes=("_prediction", "_label"),
    )

    assert len(merged) == 63
    assert (
        merged["patient_id_prediction"]
        == merged["patient_id_label"]
    ).all()

    merged["in_training"] = merged[
        "patient_id_label"
    ].isin(training_patients)

    expected = {
        False: (35, 28, 4),
        True: (28, 26, 3),
    }

    for in_training, (eyes, referred, uncertain) in expected.items():
        group = merged.loc[merged["in_training"] == in_training]

        assert len(group) == eyes
        assert int(group["is_referred"].sum()) == referred
        assert int(group["is_uncertain"].sum()) == uncertain


def test_saved_subgroup_summary(evaluation_data):
    """Check the generated CSV against independently calculated counts."""
    predictions, labels = evaluation_data
    summary = pd.read_csv(SUBGROUPS_FILE)

    assert len(summary) == 2
    assert set(summary["patient_in_training"]) == {"No", "Yes"}

    training_patients = set(
        labels.loc[labels["split"] == "train", "patient_id"]
    )

    for group_name, in_training in [("No", False), ("Yes", True)]:
        group = predictions.loc[
            predictions["patient_id"].isin(training_patients)
            == in_training
        ]
        saved = summary.loc[
            summary["patient_in_training"] == group_name
        ]

        assert len(saved) == 1
        assert int(saved.iloc[0]["eyes"]) == len(group)
        assert int(saved.iloc[0]["referred"]) == int(
            group["is_referred"].sum()
        )
        assert int(saved.iloc[0]["uncertain"]) == int(
            group["is_uncertain"].sum()
        )

        expected_rate = round(
            100 * group["is_referred"].mean(), 2
        )
        assert float(saved.iloc[0]["referral_rate_percent"]) == pytest.approx(
            expected_rate
        )


def test_patient_overlap_with_negative_baseline(evaluation_data):
    """Verify patient overlap with cataract-negative internal-test eyes."""
    predictions, labels = evaluation_data

    holdout_patients = set(predictions["patient_id"])

    negative_test_patients = set(
        labels.loc[
            (labels["split"] == "test")
            & (labels["cataract"] == 0),
            "patient_id",
        ]
    )

    assert len(holdout_patients) == 53
    assert len(negative_test_patients) == 512
    assert len(holdout_patients & negative_test_patients) == 5
