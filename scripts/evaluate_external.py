"""Prepare or run external evaluation with committed, frozen calibration.

Default: validate files without model inference. The final run requires a recorded
protocol review reference and an explicit acknowledgement of overlap limitations.
"""

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path
import subprocess

import numpy as np
from PIL import Image
import torch

from calibrate_models import PROJECT_ROOT, file_sha256, load_cataract_model, load_glaucoma_model
from calibrate_shared_models import load_model
from evaluate_calibration_holdout import verify_settings
from external_metrics import probabilities
from fundus_dataset import get_validation_transform

DATASETS = {
    "ORIGA": ("origa_labels.csv", 650, {"glaucoma": 168}),
    "DRISHTI-GS": ("drishti_labels.csv", 101, {"glaucoma": 70}),
    "ACRIMA": ("acrima_labels.csv", 705, {"glaucoma": 396}),
    "retina_dataset_2016": ("retina_labels.csv", 601, {"cataract": 100, "glaucoma": 101}),
}
PROTOCOL = PROJECT_ROOT / "documents/evaluation/external_validation_protocol.md"
SETTINGS = PROJECT_ROOT / "results/calibration/frozen_settings.json"
LIMITATION = ("Image-level bootstrap assumes independent images. Patient identifiers are unavailable, "
              "so fellow-eye dependence may make confidence intervals too narrow. The existing "
              "ODIR/retina overlap check detects identical files only, not resized or edited copies.")


def now():
    """Record unambiguous UTC run timestamps."""
    return datetime.now(timezone.utc).isoformat()


def write_json(path, value):
    """Disallow NaN and Infinity in saved results."""
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + "\n")


def write_csv(path, rows):
    """Save a nonempty result table with explicit headers."""
    if not rows:
        raise ValueError(f"No records for {path}")
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def read_dataset(root, dataset):
    """Validate external labels and retain full relative image paths."""
    filename, count, expected = DATASETS[dataset]
    label_path = root / "labels/external" / filename
    with label_path.open(newline="") as stream:
        rows = list(csv.DictReader(stream))
    if len(rows) != count:
        raise ValueError(f"Unexpected image count for {dataset}")
    seen = set()
    for row in rows:
        relative = Path(row["path"])
        if relative.is_absolute() or ".." in relative.parts or relative.parts[:2] != ("External", dataset):
            raise ValueError("External image path leaves its dataset")
        if row["split"] != "test" or row["path"] in seen:
            raise ValueError("Expected unique test-only image paths")
        if relative.name != row["filename"]:
            raise ValueError("Image filename does not match path")
        seen.add(row["path"])
        for disease in expected:
            if row[disease] not in ("0", "1"):
                raise ValueError("Nonbinary external label")
            row[disease] = int(row[disease])
        row["preprocessed"] = str(Path("Preprocessed", *relative.parts[1:]))
    if any(sum(r[d] for r in rows) != total for d, total in expected.items()):
        raise ValueError(f"Unexpected disease counts for {dataset}")
    return rows


def preflight():
    """Verify inputs and fingerprints without collecting model predictions."""
    settings = verify_settings(SETTINGS)
    committed = subprocess.check_output(["git", "show", "HEAD:" + str(PROTOCOL.relative_to(PROJECT_ROOT))],
                                        cwd=PROJECT_ROOT)
    if committed != PROTOCOL.read_bytes():
        raise ValueError("Commit the exact evaluation protocol before proceeding")
    manifest = {}
    for line in (PROJECT_ROOT / "data/MANIFEST.sha256").read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        manifest[name.removeprefix("./")] = digest
    datasets, fingerprints = {}, {}
    for dataset, (label, _, _) in DATASETS.items():
        rows = read_dataset(PROJECT_ROOT, dataset)
        fingerprints[f"labels/external/{label}"] = file_sha256(PROJECT_ROOT / "labels/external" / label)
        for row in rows:
            raw = PROJECT_ROOT / "data" / row["path"]
            if file_sha256(raw) != manifest.get(row["path"]):
                raise ValueError(f"Original image differs from manifest: {raw}")
            processed = PROJECT_ROOT / row["preprocessed"]
            with Image.open(processed) as image:
                image.load()
                if image.size != (512, 512):
                    raise ValueError(f"Expected 512x512 image: {processed}")
            fingerprints[row["preprocessed"]] = file_sha256(processed)
        datasets[dataset] = rows
        print(f"{dataset}: {len(rows)} labels, original hashes and preprocessed images checked", flush=True)
    # Reproduce the existing exact-file check, without claiming edited-copy detection.
    odir_hashes = set()
    for path in (PROJECT_ROOT / "data/Internal/ODIR-5K/Training Images").iterdir():
        if path.is_file() and path.suffix.lower() in (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"):
            odir_hashes.add(hashlib.md5(path.read_bytes()).hexdigest())
    if not odir_hashes:
        raise ValueError("No ODIR images available for exact overlap check")
    matches = [r["path"] for r in datasets["retina_dataset_2016"]
               if hashlib.md5((PROJECT_ROOT / "data" / r["path"]).read_bytes()).hexdigest() in odir_hashes]
    if matches:
        raise ValueError(f"Exact ODIR/retina overlap detected: {matches}")
    print("Exact-file ODIR/retina matches: 0", flush=True)
    record = dict(settings_sha256=file_sha256(SETTINGS), protocol_sha256=file_sha256(PROTOCOL),
                  dataset_manifest_sha256=file_sha256(PROJECT_ROOT / "data/MANIFEST.sha256"),
                  input_sha256=fingerprints, checkpoint_sha256={r["checkpoint"]:r["checkpoint_sha256"]
                  for r in settings["runs"]}, exact_file_overlap_count=0, limitation=LIMITATION)
    return settings, datasets, record


def infer(model, rows, shared):
    """Collect deterministic CPU logits with the calibration transform."""
    transform = get_validation_transform()
    output = [[], []] if shared else [[]]
    with torch.inference_mode():
        for start in range(0, len(rows), 8):
            images = []
            for row in rows[start:start + 8]:
                with Image.open(PROJECT_ROOT / row["preprocessed"]) as image:
                    images.append(transform(image.convert("RGB")))
            scores = model(torch.stack(images))
            for saved, logits in zip(output, scores if shared else (scores,), strict=True):
                values = logits.reshape(-1)
                if len(values) != len(images) or not torch.isfinite(values).all():
                    raise ValueError("Invalid external model output")
                saved.extend(values.tolist())
    return output


def evaluate(output, settings, datasets, record, review):
    """Run a new campaign, retaining partial artifacts on any failure."""
    output.mkdir(parents=True, exist_ok=False)
    record.update(status="running", started_at=now(), protocol_review=review,
                  commit=subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=PROJECT_ROOT, text=True).strip(),
                  code_sha256={str(p.relative_to(PROJECT_ROOT)): file_sha256(p)
                               for p in sorted((PROJECT_ROOT / "scripts").glob("*.py"))},
                  versions={p:importlib.metadata.version(p) for p in
                            ("torch", "torchvision", "numpy", "scikit-learn", "pillow")},
                  device="cpu", batch_size=8, threads=4, shuffle=False,
                  bootstrap=dict(replicates=2000, seed=42, unit="image", max_attempts=10000),
                  review_settings=settings)
    manifest_path = output / "run_manifest.json"
    write_json(manifest_path, record)
    try:
        predictions = []
        runs = {(r["model_kind"], r["disease"], r["seed"]):r for r in settings["runs"]}
        for kind in ("single", "shared"):
            for seed in (42, 43, 44):
                for target in (("cataract", "glaucoma") if kind == "single" else ("both",)):
                    model = (load_model(seed)[0] if kind == "shared" else load_cataract_model(seed)
                             if target == "cataract" else load_glaucoma_model(
                                 PROJECT_ROOT / runs[(kind, target, seed)]["checkpoint"], seed))
                    for dataset, rows in datasets.items():
                        diseases = DATASETS[dataset][2]
                        if kind == "single" and target not in diseases:
                            continue
                        print(f"Scoring {dataset}: {kind} {target}, seed {seed}", flush=True)
                        heads = infer(model, rows, kind == "shared")
                        for disease in diseases:
                            if kind == "single" and disease != target:
                                continue
                            raw = heads[(0 if disease == "cataract" else 1) if kind == "shared" else 0]
                            r = runs[(kind, disease, seed)]
                            p = probabilities(r["scale"] * np.asarray(raw) + r["offset"])
                            for row, z, prob in zip(rows, raw, p, strict=True):
                                uncertain = bool(abs(prob-r["threshold"]) <= r["uncertain_margin"])
                                predictions.append(dict(dataset=dataset, path=row["path"], model_kind=kind,
                                    seed=seed, disease=disease, label=row[disease], raw_logit=z,
                                    probability=float(prob), threshold=r["threshold"], margin=r["uncertain_margin"],
                                    uncertain=uncertain, decision="Uncertain, refer" if uncertain else
                                    "Refer" if prob >= r["threshold"] else "No concern"))
                        write_csv(output / "predictions.partial.csv", predictions)
                    del model
        expected_count = sum(len(rows) * len(DATASETS[name][2]) * 6
                             for name, rows in datasets.items())
        if len(predictions) != expected_count:
            raise ValueError(f"Expected {expected_count} applicable predictions")
        (output / "predictions.partial.csv").rename(output / "predictions.csv")
        record["predictions_sha256"] = file_sha256(output / "predictions.csv")
        record["status"] = "predictions_saved"
        write_json(manifest_path, record)
        record["completed_at"] = now()
        write_json(manifest_path, record)
    except Exception as error:
        record.update(status="failed", failed_at=now(), error=f"{type(error).__name__}: {error}")
        write_json(manifest_path, record)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", action="store_true", help="Collect final external predictions")
    parser.add_argument("--output", type=Path, help="New result directory; never overwritten")
    parser.add_argument("--protocol-review", help="Review link approving bootstrap choices and overlap limitation")
    parser.add_argument("--acknowledge-exact-only-overlap", action="store_true")
    args = parser.parse_args()
    if args.run and not (args.output and args.protocol_review and args.acknowledge_exact_only_overlap):
        parser.error("Final run requires --output, --protocol-review and --acknowledge-exact-only-overlap")
    torch.set_num_threads(4)
    settings, datasets, record = preflight()
    if not args.run:
        print("Preflight passed. No external inference was performed. Final run awaits protocol review.")
        return
    evaluate(args.output, settings, datasets, record, args.protocol_review)


if __name__ == "__main__":
    main()
