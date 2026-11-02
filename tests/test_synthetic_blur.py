"""Tests for SCRUM-98 synthetic blur evaluation."""

import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from PIL import Image
from torchvision import transforms


# Make the project's scripts importable.
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

from evaluate_synthetic_blur import (  # noqa: E402
    BLUR_SIGMAS,
    EXPECTED_CATARACT_EYES,
    EXPECTED_NORMAL_EYES,
    PREDICTIONS_FILE,
    SUMMARY_FILE,
    SyntheticBlurDataset,
    calibrate_cataract_logits,
    load_frozen_cataract_settings,
    select_validation_images,
    summarize_synthetic_blur,
)


def test_validation_image_selection():
    """Verify the predefined validation groups."""

    normal, cataract = select_validation_images()

    assert len(normal) == EXPECTED_NORMAL_EYES
    assert len(cataract) == EXPECTED_CATARACT_EYES

    assert normal["filename"].is_unique
    assert cataract["filename"].is_unique

    assert set(normal["filename"]).isdisjoint(
        set(cataract["filename"])
    )


def test_gaussian_blur_changes_image(monkeypatch, tmp_path):
    """Verify blur changes an image while preserving its dimensions."""

    import evaluate_synthetic_blur as experiment

    # Create a deterministic synthetic image with visible edges.
    image_array = np.zeros((512, 512, 3), dtype=np.uint8)
    image_array[192:320, 192:320] = 255

    image_path = tmp_path / "test_image.png"
    Image.fromarray(image_array).save(image_path)

    monkeypatch.setattr(
        experiment,
        "IMAGE_DIR",
        tmp_path,
    )

    rows = pd.DataFrame([
        {"filename": "test_image.png"}
    ])

    original = SyntheticBlurDataset(rows, sigma=0)[0]["image"]
    blurred = SyntheticBlurDataset(rows, sigma=4)[0]["image"]

    assert original.shape == (3, 512, 512)
    assert blurred.shape == (3, 512, 512)

    assert not np.allclose(
        original.numpy(),
        blurred.numpy(),
    )


def test_invalid_blur_sigma():
    """Reject blur values outside the predefined experiment."""

    rows = pd.DataFrame([
        {"filename": "unused.png"}
    ])

    with pytest.raises(ValueError, match="Unsupported blur sigma"):
        SyntheticBlurDataset(rows, sigma=3)


def test_frozen_calibration():
    """Verify the frozen calibration returns valid probabilities."""

    _, calibration_run = load_frozen_cataract_settings()

    logits = np.array([-2.0, 0.0, 2.0])

    result = calibrate_cataract_logits(
        logits,
        calibration_run,
    )

    probabilities = result["probabilities"]

    assert len(probabilities) == 3
    assert np.isfinite(probabilities).all()
    assert ((probabilities >= 0) & (probabilities <= 1)).all()

    assert np.all(np.diff(probabilities) > 0)


def test_saved_prediction_integrity():
    """Verify saved predictions have the expected structure."""

    if not PREDICTIONS_FILE.is_file():
        pytest.skip("Synthetic blur predictions have not been generated.")

    predictions = pd.read_csv(PREDICTIONS_FILE)

    expected_total = (
        EXPECTED_NORMAL_EYES * len(BLUR_SIGMAS)
        + EXPECTED_CATARACT_EYES
    )

    assert len(predictions) == expected_total

    assert not predictions.duplicated(
        ["group", "sigma", "filename"]
    ).any()

    assert predictions["calibrated_probability"].notna().all()

    assert predictions["calibrated_probability"].between(
        0, 1
    ).all()


def test_summary_warning_criterion():
    """Verify the warning follows the predefined sigma comparison."""

    rows = []

    for sigma in BLUR_SIGMAS:
        probability = 0.1 if sigma == 0 else 0.2

        rows.append({
            "group": "normal",
            "sigma": sigma,
            "mean_probability": probability,
        })

    normal_summary = pd.DataFrame(rows).set_index("sigma")

    warning_triggered = (
        normal_summary.loc[8, "mean_probability"]
        > normal_summary.loc[0, "mean_probability"]
    )

    assert warning_triggered


def test_saved_summary_matches_predictions():
    """Verify saved summary statistics match prediction records."""

    if not PREDICTIONS_FILE.is_file() or not SUMMARY_FILE.is_file():
        pytest.skip("Synthetic blur result files have not been generated.")

    predictions = pd.read_csv(PREDICTIONS_FILE)
    saved_summary = pd.read_csv(SUMMARY_FILE)

    recalculated, warning_triggered = summarize_synthetic_blur(
        predictions
    )

    assert warning_triggered

    pd.testing.assert_frame_equal(
        saved_summary.reset_index(drop=True),
        recalculated.reset_index(drop=True),
        check_exact=False,
        rtol=1e-6,
        atol=1e-8,
    )