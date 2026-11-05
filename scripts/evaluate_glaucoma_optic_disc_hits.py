"""Evaluate glaucoma Grad-CAM peak localization within annotated optic discs.

Datasets:
    ORIGA: optic disc defined by annotation mask > 0.
    DRISHTI-GS: optic disc defined by softmap >= 128.

Heatmaps were generated using the frozen shared glaucoma model.

ORIGA image 359 has a 13-pixel annotation width mismatch.
Its mask is right-padded with zeros to match the original image.

This script evaluates localization, not classification accuracy.
"""

import argparse
import csv
from pathlib import Path

import cv2
import numpy as np
from scipy.io import loadmat


PROJECT_ROOT = Path(__file__).resolve().parents[1]

RESULTS_DIR = PROJECT_ROOT / "results/task16"

ORIGA_ROOT = PROJECT_ROOT / "data/External/ORIGA"

DRISHTI_ROOT = PROJECT_ROOT / "data/External/DRISHTI-GS"

ORIGA_MANIFEST = RESULTS_DIR / "origa_heatmap_manifest.csv"

DRISHTI_MANIFEST = RESULTS_DIR / "drishti_heatmap_manifest.csv"

OUTPUT_CSV = RESULTS_DIR / "glaucoma_optic_disc_hit_rates.csv"

IMAGE_SIZE = 512

EXPECTED_COUNTS = {
    "ORIGA": 650,
    "DRISHTI-GS": 101,
}

ORIGA_EXCLUDED_IDS = set()

DRISHTI_PRIMARY_THRESHOLD = 128

DRISHTI_SENSITIVITY_THRESHOLDS = (1, 255)


def read_manifest(path):
    """Read a Grad-CAM manifest and reject empty input."""
    with path.open(
        "r",
        encoding="utf-8-sig",
        newline=""
    ) as stream:
        rows = list(csv.DictReader(stream))

    if not rows:
        raise ValueError(f"Empty manifest: {path}")

    return rows




def validate_manifest(rows, dataset):
    """Validate Grad-CAM records and return rows indexed by image ID."""
    expected = EXPECTED_COUNTS[dataset]

    if len(rows) != expected:
        raise ValueError(
            f"{dataset}: expected {expected} records, found {len(rows)}"
        )

    indexed = {}

    for row in rows:
        image_id = Path(row["filename"]).stem

        if not image_id:
            raise ValueError(f"{dataset}: empty image identifier")

        if image_id in indexed:
            raise ValueError(
                f"{dataset}: duplicate image identifier {image_id}"
            )

        if row["processing_status"] != "Generated":
            raise ValueError(
                f"{dataset}: heatmap not generated for {image_id}"
            )

        if row["gradcam_peak_status"] != "Valid":
            raise ValueError(
                f"{dataset}: invalid Grad-CAM peak for {image_id}"
            )

        try:
            peak_x = int(row["gradcam_peak_x"])
            peak_y = int(row["gradcam_peak_y"])
            peak_value = float(row["gradcam_peak_value"])
        except (ValueError, TypeError, KeyError) as error:
            raise ValueError(
                f"{dataset}: invalid peak data for {image_id}"
            ) from error

        if not (
            0 <= peak_x < IMAGE_SIZE
            and 0 <= peak_y < IMAGE_SIZE
        ):
            raise ValueError(
                f"{dataset}: peak outside image for {image_id}"
            )

        if not np.isfinite(peak_value):
            raise ValueError(
                f"{dataset}: non-finite peak value for {image_id}"
            )

        indexed[image_id] = row

    return indexed

def get_crop_geometry(image):
    """Reproduce the fundus preprocessing crop coordinates."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 0)

    _, mask = cv2.threshold(
        blurred, 10, 255, cv2.THRESH_BINARY
    )

    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        np.ones((5, 5), np.uint8)
    )

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    height, width = image.shape[:2]

    if contours:
        x, y, w, h = cv2.boundingRect(
            max(contours, key=cv2.contourArea)
        )

        if w * h >= height * width * 0.20:
            cx = x + w // 2
            cy = y + h // 2

            side = min(max(w, h), height, width)
            half = side // 2

            x1 = min(max(0, cx - half), width - side)
            y1 = min(max(0, cy - half), height - side)

            if side > 0:
                return x1, y1, side

    side = min(height, width)

    return (
        (width - side) // 2,
        (height - side) // 2,
        side
    )


def evaluate_origa():
    """Calculate ORIGA Grad-CAM peak hits inside annotated optic discs."""
    rows = read_manifest(ORIGA_MANIFEST)
    indexed = validate_manifest(rows, "ORIGA")

    originals = {
        path.stem: path
        for path in ORIGA_ROOT.rglob("*.jpg")
    }

    annotations = {
        path.stem: path
        for path in ORIGA_ROOT.rglob("*.mat")
        if path.stem.isdigit()
    }

    expected = EXPECTED_COUNTS["ORIGA"]

    if len(originals) != expected or len(annotations) != expected:
        raise ValueError("Unexpected ORIGA image or annotation count")

    if set(indexed) != set(originals) or set(indexed) != set(annotations):
        raise ValueError("ORIGA image and annotation identifiers differ")

    hits = 0
    misses = 0
    excluded = []
    label_counts = {
        0: {"hits": 0, "total": 0},
        1: {"hits": 0, "total": 0},
    }

    for image_id, row in sorted(indexed.items()):
        if image_id in ORIGA_EXCLUDED_IDS:
            excluded.append(image_id)
            continue

        image = cv2.imread(str(originals[image_id]))

        if image is None:
            raise ValueError(f"Unreadable ORIGA image: {image_id}")

        annotation = loadmat(str(annotations[image_id]))["mask"]

        if image_id == "359":
            image_height, image_width = image.shape[:2]
            annotation_height, annotation_width = annotation.shape

            if (
                image_height != annotation_height
                or image_width - annotation_width != 13
            ):
                raise ValueError(
                    "Unexpected ORIGA image 359 dimensions: "
                    f"image={image.shape[:2]}, "
                    f"annotation={annotation.shape}"
                )

            annotation = np.pad(
                annotation,
                ((0, 0), (0, 13)),
                mode="constant",
                constant_values=0
            )

        if image.shape[:2] != annotation.shape:
            raise ValueError(
                f"ORIGA image/annotation mismatch: {image_id}"
            )

        x1, y1, side = get_crop_geometry(image)

        disc = (annotation > 0).astype(np.uint8)

        cropped = disc[
            y1:y1 + side,
            x1:x1 + side
        ]

        aligned = cv2.resize(
            cropped,
            (IMAGE_SIZE, IMAGE_SIZE),
            interpolation=cv2.INTER_NEAREST
        )

        if not aligned.any():
            raise ValueError(f"Empty ORIGA optic disc: {image_id}")

        peak_x = int(row["gradcam_peak_x"])
        peak_y = int(row["gradcam_peak_y"])

        label = int(row["glaucoma"])
        if label not in label_counts:
            raise ValueError(f"Invalid ORIGA glaucoma label: {label}")

        is_hit = aligned[peak_y, peak_x] > 0
        label_counts[label]["total"] += 1

        if is_hit:
            hits += 1
            label_counts[label]["hits"] += 1
        else:
            misses += 1

    evaluated = hits + misses

    if evaluated + len(excluded) != expected:
        raise ValueError("ORIGA evaluation count mismatch")

    if excluded:
        raise ValueError(f"Unexpected ORIGA exclusions: {excluded}")

    hit_rate = round(100 * hits / evaluated, 2)

    if sum(group["total"] for group in label_counts.values()) != evaluated:
        raise ValueError("ORIGA label totals do not match evaluated images")

    if sum(group["hits"] for group in label_counts.values()) != hits:
        raise ValueError("ORIGA label hits do not match total hits")

    return {
        "dataset": "ORIGA",
        "total_heatmaps": expected,
        "evaluated_images": evaluated,
        "excluded_images": len(excluded),
        "optic_disc_hits": hits,
        "optic_disc_misses": misses,
        "hit_rate_percent": hit_rate,
        "glaucoma_eyes": label_counts[1]["total"],
        "glaucoma_hits": label_counts[1]["hits"],
        "glaucoma_hit_rate_percent": round(
            100 * label_counts[1]["hits"] / label_counts[1]["total"], 2
        ),
        "healthy_eyes": label_counts[0]["total"],
        "healthy_hits": label_counts[0]["hits"],
        "healthy_hit_rate_percent": round(
            100 * label_counts[0]["hits"] / label_counts[0]["total"], 2
        ),
        "mask_definition": "mask > 0",
        "exclusion_note": (
            "No exclusions; image 359 annotation right-padded "
            "by 13 columns"
        ),
    }


def evaluate_drishti():
    """Calculate DRISHTI-GS Grad-CAM optic disc localization."""
    rows = read_manifest(DRISHTI_MANIFEST)
    indexed = validate_manifest(rows, "DRISHTI-GS")

    originals = {}
    softmaps = {}

    for path in DRISHTI_ROOT.rglob("drishtiGS_*.png"):
        if path.name.endswith("_ODsegSoftmap.png"):
            image_id = path.name.removesuffix("_ODsegSoftmap.png")

            if image_id in softmaps:
                raise ValueError(
                    f"Duplicate DRISHTI softmap: {image_id}"
                )

            softmaps[image_id] = path

        elif (
            "SoftMap" not in path.parts
            and "GT" not in path.parts
            and "Test_GT" not in path.parts
        ):
            if path.stem in originals:
                raise ValueError(
                    f"Duplicate DRISHTI image: {path.stem}"
                )

            originals[path.stem] = path

    expected = EXPECTED_COUNTS["DRISHTI-GS"]

    if len(originals) != expected or len(softmaps) != expected:
        raise ValueError(
            "Unexpected DRISHTI image or softmap count"
        )

    if set(indexed) != set(originals) or set(indexed) != set(softmaps):
        raise ValueError(
            "DRISHTI image and annotation identifiers differ"
        )

    thresholds = (
        *DRISHTI_SENSITIVITY_THRESHOLDS,
        DRISHTI_PRIMARY_THRESHOLD,
    )

    hits = {threshold: 0 for threshold in thresholds}
    label_counts = {
        0: {"hits": 0, "total": 0},
        1: {"hits": 0, "total": 0},
    }

    for image_id, row in sorted(indexed.items()):
        image = cv2.imread(str(originals[image_id]))

        softmap = cv2.imread(
            str(softmaps[image_id]),
            cv2.IMREAD_GRAYSCALE
        )

        if image is None or softmap is None:
            raise ValueError(
                f"Unreadable DRISHTI image or softmap: {image_id}"
            )

        if image.shape[:2] != softmap.shape:
            raise ValueError(
                f"DRISHTI image/annotation mismatch: {image_id}"
            )

        x1, y1, side = get_crop_geometry(image)

        cropped = softmap[
            y1:y1 + side,
            x1:x1 + side
        ]

        aligned = cv2.resize(
            cropped,
            (IMAGE_SIZE, IMAGE_SIZE),
            interpolation=cv2.INTER_NEAREST
        )

        if not np.any(aligned >= 255):
            raise ValueError(
                f"Empty DRISHTI optic disc: {image_id}"
            )

        peak_x = int(row["gradcam_peak_x"])
        peak_y = int(row["gradcam_peak_y"])

        peak_annotation_value = int(
            aligned[peak_y, peak_x]
        )

        label = int(row["glaucoma"])
        if label not in label_counts:
            raise ValueError(f"Invalid DRISHTI glaucoma label: {label}")

        label_counts[label]["total"] += 1

        if peak_annotation_value >= DRISHTI_PRIMARY_THRESHOLD:
            label_counts[label]["hits"] += 1

        for threshold in thresholds:
            if peak_annotation_value >= threshold:
                hits[threshold] += 1

    evaluated = len(indexed)
    primary_hits = hits[DRISHTI_PRIMARY_THRESHOLD]
    primary_misses = evaluated - primary_hits

    hit_rate = round(
        100 * primary_hits / evaluated,
        2
    )

    if sum(group["total"] for group in label_counts.values()) != evaluated:
        raise ValueError("DRISHTI label totals do not match evaluated images")

    if sum(group["hits"] for group in label_counts.values()) != primary_hits:
        raise ValueError("DRISHTI label hits do not match primary hits")

    result = {
        "dataset": "DRISHTI-GS",
        "total_heatmaps": expected,
        "evaluated_images": evaluated,
        "excluded_images": 0,
        "optic_disc_hits": primary_hits,
        "optic_disc_misses": primary_misses,
        "hit_rate_percent": hit_rate,
        "glaucoma_eyes": label_counts[1]["total"],
        "glaucoma_hits": label_counts[1]["hits"],
        "glaucoma_hit_rate_percent": round(
            100 * label_counts[1]["hits"] / label_counts[1]["total"], 2
        ),
        "healthy_eyes": label_counts[0]["total"],
        "healthy_hits": label_counts[0]["hits"],
        "healthy_hit_rate_percent": round(
            100 * label_counts[0]["hits"] / label_counts[0]["total"], 2
        ),
        "mask_definition": "OD softmap >= 128",
        "exclusion_note": "None",
    }

    sensitivity = {
        threshold: {
            "hits": hits[threshold],
            "evaluated": evaluated,
            "hit_rate_percent": round(
                100 * hits[threshold] / evaluated,
                2
            ),
        }
        for threshold in DRISHTI_SENSITIVITY_THRESHOLDS
    }

    return result, sensitivity


def main():
    """Evaluate both datasets and save reproducible localization results."""
    parser = argparse.ArgumentParser(
        description="Evaluate glaucoma Grad-CAM optic disc localization."
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=OUTPUT_CSV,
        help="Output CSV path."
    )

    args = parser.parse_args()

    print("Glaucoma Grad-CAM optic disc evaluation")
    print("Project root:", PROJECT_ROOT)
    print()

    print("Evaluating ORIGA...", flush=True)
    origa = evaluate_origa()

    print("Evaluating DRISHTI-GS...", flush=True)
    drishti, sensitivity = evaluate_drishti()

    results = [origa, drishti]

    for result in results:
        if (
            result["optic_disc_hits"]
            + result["optic_disc_misses"]
            != result["evaluated_images"]
        ):
            raise ValueError(
                f"Invalid hit/miss counts: {result['dataset']}"
            )

        if (
            result["evaluated_images"]
            + result["excluded_images"]
            != result["total_heatmaps"]
        ):
            raise ValueError(
                f"Invalid evaluation count: {result['dataset']}"
            )

    args.output.parent.mkdir(parents=True, exist_ok=True)

    with args.output.open(
        "w",
        encoding="utf-8",
        newline=""
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=list(results[0].keys())
        )
        writer.writeheader()
        writer.writerows(results)

    print()
    print("Primary optic disc hit rates:")

    for result in results:
        print(
            f"  {result['dataset']}: "
            f"{result['optic_disc_hits']}/"
            f"{result['evaluated_images']} = "
            f"{result['hit_rate_percent']:.2f}%"
        )

    print()
    print("DRISHTI-GS sensitivity analysis:")

    for threshold in sorted(sensitivity):
        values = sensitivity[threshold]

        print(
            f"  Threshold >= {threshold}: "
            f"{values['hits']}/{values['evaluated']} = "
            f"{values['hit_rate_percent']:.2f}%"
        )

    print()
    print("Results saved:", args.output)
    print("Evaluation completed successfully.")


if __name__ == "__main__":
    main()
