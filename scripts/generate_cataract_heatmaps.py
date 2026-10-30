"""Generate reproducible cataract Grad-CAM overlays for SCRUM-99."""

import csv
import json
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from matplotlib import colormaps

from calibrate_shared_models import load_model
from fundus_dataset import get_validation_transform


ROOT = Path(__file__).resolve().parents[1]
SELECTION_FILE = ROOT / "results/task15/heatmap_selected_images.csv"
SETTINGS_FILE = ROOT / "results/calibration/frozen_settings.json"
IMAGE_DIR = ROOT / "Preprocessed/ODIR"
OUTPUT_DIR = ROOT / "results/task15/cataract_heatmaps"
MANIFEST_FILE = ROOT / "results/task15/heatmap_generation_manifest.csv"

EXPECTED_IMAGES = 21
OVERLAY_ALPHA = 0.40


class CataractGradCAM:
    """Grad-CAM using the final shared ResNet50 bottleneck."""

    def __init__(self, model):
        self.model = model
        self.activations = None
        self.gradients = None

        self.target_layer = model.backbone.features[7][-1]

        self.forward_hook = self.target_layer.register_forward_hook(
            self._save_activations
        )

    def _save_activations(self, module, inputs, output):
        self.activations = output

        if output.requires_grad:
            output.register_hook(self._save_gradients)

    def _save_gradients(self, gradient):
        self.gradients = gradient

    def generate(self, image_tensor):
        self.activations = None
        self.gradients = None

        self.model.zero_grad(set_to_none=True)

        cataract_logits, _ = self.model(image_tensor)
        cataract_logits.reshape(-1)[0].backward()

        if self.activations is None or self.gradients is None:
            raise RuntimeError("Grad-CAM activations or gradients missing")

        activations = self.activations.detach()
        gradients = self.gradients.detach()

        weights = gradients.mean(dim=(2, 3), keepdim=True)
        cam = torch.relu((weights * activations).sum(dim=1, keepdim=True))

        cam = F.interpolate(
            cam,
            size=image_tensor.shape[-2:],
            mode="bilinear",
            align_corners=False,
        )

        cam = cam[0, 0].cpu().numpy()

        maximum = float(cam.max())
        minimum = float(cam.min())

        if maximum > minimum:
            cam = (cam - minimum) / (maximum - minimum)
        else:
            cam = np.zeros_like(cam)

        return cam, float(cataract_logits.detach().reshape(-1)[0])

    def close(self):
        self.forward_hook.remove()


def create_overlay(image, cam):
    original = np.asarray(image.convert("RGB"), dtype=np.float32) / 255.0

    heatmap = colormaps["jet"](cam)[..., :3].astype(np.float32)

    overlay = (
        (1.0 - OVERLAY_ALPHA) * original
        + OVERLAY_ALPHA * heatmap
    )

    overlay = np.clip(overlay * 255.0, 0, 255).astype(np.uint8)

    return Image.fromarray(overlay, mode="RGB")


def read_selection():
    with SELECTION_FILE.open("r", newline="", encoding="utf-8-sig") as stream:
        rows = list(csv.DictReader(stream))

    if len(rows) != EXPECTED_IMAGES:
        raise ValueError(
            f"Expected {EXPECTED_IMAGES} selected images, got {len(rows)}"
        )

    filenames = [row["filename"] for row in rows]

    if len(filenames) != len(set(filenames)):
        raise ValueError("Duplicate selected image filenames")

    return rows


def verify_frozen_configuration():
    with SETTINGS_FILE.open("r", encoding="utf-8-sig") as stream:
        settings = json.load(stream)

    deployment = settings["deployment"]

    expected = {
        "model_kind": "shared",
        "seed": 42,
        "checkpoint": "checkpoints/task11/shared/shared_seed_42_best.pt",
    }

    for key, value in expected.items():
        if deployment[key] != value:
            raise ValueError(f"Unexpected frozen setting: {key}")


def main():
    if MANIFEST_FILE.exists():
        raise FileExistsError(f"Refusing to overwrite: {MANIFEST_FILE}")

    if OUTPUT_DIR.exists() and any(OUTPUT_DIR.iterdir()):
        raise FileExistsError(f"Output directory is not empty: {OUTPUT_DIR}")

    verify_frozen_configuration()
    rows = read_selection()

    model, checkpoint = load_model(42)
    model = model.to("cpu")
    model.eval()

    transform = get_validation_transform()
    gradcam = CataractGradCAM(model)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    results = []

    try:
        for index, row in enumerate(rows, start=1):
            filename = row["filename"]
            image_path = IMAGE_DIR / filename

            output_name = f"{index:02d}_{Path(filename).stem}_gradcam.png"
            output_path = OUTPUT_DIR / output_name

            record = dict(row)
            record["heatmap_filename"] = output_name
            record["processing_status"] = "Failed"
            record["error"] = ""
            record["gradcam_raw_logit"] = ""

            try:
                with Image.open(image_path) as source:
                    image = source.convert("RGB")

                if image.size != (512, 512):
                    raise ValueError(
                        f"Unexpected image dimensions: {image.size}"
                    )

                image_tensor = transform(image).unsqueeze(0)

                with torch.enable_grad():
                    cam, raw_logit = gradcam.generate(image_tensor)

                overlay = create_overlay(image, cam)
                overlay.save(output_path)

                record["gradcam_raw_logit"] = raw_logit
                record["processing_status"] = "Generated"

                print(f"[{index}/{len(rows)}] Generated: {output_name}")

            except Exception as error:
                record["error"] = str(error)
                print(f"[{index}/{len(rows)}] FAILED: {filename}: {error}")

            results.append(record)

    finally:
        gradcam.close()

        if results:
            with MANIFEST_FILE.open(
                "w", newline="", encoding="utf-8"
            ) as stream:
                writer = csv.DictWriter(
                    stream,
                    fieldnames=list(results[0].keys()),
                )
                writer.writeheader()
                writer.writerows(results)

    successful = sum(
        row["processing_status"] == "Generated"
        for row in results
    )

    print(f"Heatmaps generated: {successful}/{len(rows)}")
    print(f"Manifest: {MANIFEST_FILE}")

    if successful != len(rows):
        raise RuntimeError(
            f"{len(rows) - successful} heatmap(s) failed; inspect manifest"
        )


if __name__ == "__main__":
    main()
