import sys
from pathlib import Path

import numpy as np
import pytest
import torch
from PIL import Image

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from dual_model import DualNet
from generate_cataract_heatmaps import CataractGradCAM, create_overlay


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

    gradcam = CataractGradCAM(model)

    try:
        heatmap, logit = gradcam.generate(image_tensor)
    finally:
        gradcam.close()

    return heatmap, logit


def test_target_layer(model):
    gradcam = CataractGradCAM(model)

    try:
        assert gradcam.target_layer is model.backbone.features[7][-1]
    finally:
        gradcam.close()


def test_heatmap_dimensions(gradcam_result):
    heatmap, _ = gradcam_result

    assert heatmap.shape == (64, 64)


def test_heatmap_normalization(gradcam_result):
    heatmap, _ = gradcam_result

    assert heatmap.min() >= 0.0
    assert heatmap.max() <= 1.0


def test_heatmap_contains_finite_values(gradcam_result):
    heatmap, logit = gradcam_result

    assert np.isfinite(heatmap).all()
    assert np.isfinite(logit)


def test_overlay_dimensions_and_mode():
    image = Image.new("RGB", (64, 64), color=(120, 80, 60))
    heatmap = np.zeros((64, 64), dtype=np.float32)

    overlay = create_overlay(image, heatmap)

    assert overlay.size == (64, 64)
    assert overlay.mode == "RGB"


def test_forward_hook_cleanup(model):
    target_layer = model.backbone.features[7][-1]
    initial_hooks = len(target_layer._forward_hooks)

    gradcam = CataractGradCAM(model)

    assert len(target_layer._forward_hooks) == initial_hooks + 1

    gradcam.close()

    assert len(target_layer._forward_hooks) == initial_hooks


def test_model_weights_unchanged(model):
    original_weights = {
        name: parameter.detach().clone()
        for name, parameter in model.named_parameters()
    }

    gradcam = CataractGradCAM(model)

    try:
        gradcam.generate(torch.randn(1, 3, 64, 64))
    finally:
        gradcam.close()

    for name, parameter in model.named_parameters():
        assert torch.equal(parameter.detach(), original_weights[name])
