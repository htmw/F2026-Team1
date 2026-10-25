"""Check external evaluation inputs without running model predictions."""

import argparse
import csv
import hashlib
from pathlib import Path
import subprocess

from PIL import Image

from calibrate_models import PROJECT_ROOT, file_sha256
from evaluate_calibration_holdout import verify_settings

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

def main():
    """Run input checks only; external inference is a later step."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    preflight()
    print("Preflight passed. No external inference was performed.")


if __name__ == "__main__":
    main()
