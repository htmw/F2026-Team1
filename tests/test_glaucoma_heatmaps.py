import csv
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest
import torch

sys.path.insert(
    0,
    str(Path(__file__).resolve().parents[1] / "scripts")
)

from dual_model import DualNet
from generate_glaucoma_heatmaps import GlaucomaGradCAM
from evaluate_glaucoma_optic_disc_hits import get_crop_geometry
from preprocess_images import crop_fundus


@pytest.fixture(scope="module")
def model():
    torch.manual_seed(42)
    torch.set_num_threads(1)

    network = DualNet(pretrained=False)
    network.eval()

    return network


@pytest.fixture(scope="module")
def gradcam_result(model):
    image_tensor = torch.randn(1, 3, 64, 64)
    gradcam = GlaucomaGradCAM(model)

    try:
        heatmap, logit = gradcam.generate(image_tensor)
    finally:
        gradcam.close()

    return heatmap, logit


def test_glaucoma_target_layer(model):
    gradcam = GlaucomaGradCAM(model)

    try:
        assert gradcam.target_layer is model.backbone.features[7][-1]
    finally:
        gradcam.close()


def test_gradcam_uses_glaucoma_head(model):
    image_tensor = torch.randn(1, 3, 64, 64)

    with torch.no_grad():
        cataract_logits, glaucoma_logits = model(image_tensor)

    gradcam = GlaucomaGradCAM(model)

    try:
        _, returned_logit = gradcam.generate(image_tensor)
    finally:
        gradcam.close()

    expected = glaucoma_logits.reshape(-1)[0].item()

    assert np.isclose(returned_logit, expected, atol=1e-5)
    assert np.isfinite(cataract_logits.detach().numpy()).all()


def test_heatmap_dimensions(gradcam_result):
    heatmap, _ = gradcam_result
    assert heatmap.shape == (64, 64)


def test_heatmap_normalization(gradcam_result):
    heatmap, logit = gradcam_result

    assert np.isfinite(heatmap).all()
    assert np.isfinite(logit)
    assert heatmap.min() >= 0.0
    assert heatmap.max() <= 1.0


def test_crop_geometry_matches_preprocessing():
    image = np.zeros((180, 240, 3), dtype=np.uint8)

    cv2.circle(
        image,
        (120, 90),
        65,
        (100, 140, 180),
        -1
    )

    x, y, side = get_crop_geometry(image)

    expected = crop_fundus(image)
    actual = image[y:y + side, x:x + side]

    assert actual.shape == expected.shape
    assert np.array_equal(actual, expected)


def test_forward_hook_cleanup(model):
    layer = model.backbone.features[7][-1]
    initial_hooks = len(layer._forward_hooks)

    gradcam = GlaucomaGradCAM(model)

    assert len(layer._forward_hooks) == initial_hooks + 1

    gradcam.close()

    assert len(layer._forward_hooks) == initial_hooks


def test_hit_count_consistency(tmp_path):
    csv_path = tmp_path / "results.csv"

    rows = [
        {
            "dataset": "ORIGA",
            "evaluated_images": 650,
            "optic_disc_hits": 240,
            "optic_disc_misses": 410,
        },
        {
            "dataset": "DRISHTI-GS",
            "evaluated_images": 101,
            "optic_disc_hits": 68,
            "optic_disc_misses": 33,
        },
    ]

    with csv_path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(rows[0].keys())
        )
        writer.writeheader()
        writer.writerows(rows)

    with csv_path.open("r", newline="", encoding="utf-8") as stream:
        saved_rows = list(csv.DictReader(stream))

    assert len(saved_rows) == 2

    for row in saved_rows:
        hits = int(row["optic_disc_hits"])
        misses = int(row["optic_disc_misses"])
        evaluated = int(row["evaluated_images"])

        assert hits + misses == evaluated
