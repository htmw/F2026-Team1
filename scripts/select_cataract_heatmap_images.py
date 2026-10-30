"""Select SCRUM-99 Grad-CAM examples before generating heatmaps."""

import csv
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

LABELS_FILE = ROOT / "labels/eye_labels_task7.csv"
INTERNAL_FILE = ROOT / "results/task13/internal_test/shared_cataract_seed_42_test.csv"
MEDIA_FILE = ROOT / "results/task15/media_opacity_predictions.csv"
IMAGE_DIR = ROOT / "Preprocessed/ODIR"
OUTPUT_FILE = ROOT / "results/task15/heatmap_selected_images.csv"

EXCLUDED_FLAGS = ("media_opacity", "image_quality_flag", "exclusion")

CATEGORIES = (
    ("normal_fundus", "No concern"),
    ("normal_fundus", "Refer"),
    ("normal_fundus", "Uncertain, refer"),
    ("cataract_positive", "Refer"),
    ("media_opacity", "No concern"),
    ("media_opacity", "Refer"),
    ("media_opacity", "Uncertain, refer"),
)

IMAGES_PER_CATEGORY = 3


def read_csv(path):
    with path.open("r", newline="", encoding="utf-8-sig") as stream:
        return list(csv.DictReader(stream))


def eligible_group(label):
    """Identify eligible internal-test normal and cataract images."""
    if any(int(label[flag]) != 0 for flag in EXCLUDED_FLAGS):
        return None

    diagnosis = label["diagnosis_text"]

    if diagnosis == "normal fundus":
        if all(
            int(label[flag]) == 0
            for flag in ("cataract", "glaucoma", "suspected_glaucoma")
        ):
            return "normal_fundus"

    if diagnosis == "cataract" and int(label["cataract"]) == 1:
        return "cataract_positive"

    return None


def select_images():
    labels = {row["filename"]: row for row in read_csv(LABELS_FILE)}

    candidates = []

    for prediction in read_csv(INTERNAL_FILE):
        filename = prediction["filename"]
        if filename not in labels:
            raise ValueError(f"Missing diagnosis label: {filename}")

        label = labels[filename]
        group = eligible_group(label)

        if group is not None:
            candidates.append((group, prediction, label))

    for prediction in read_csv(MEDIA_FILE):
        filename = prediction["filename"]
        if filename not in labels:
            raise ValueError(f"Missing diagnosis label: {filename}")

        candidates.append(("media_opacity", prediction, labels[filename]))

    selected = []

    for group, decision in CATEGORIES:
        matches = [
            (prediction, label)
            for candidate_group, prediction, label in candidates
            if candidate_group == group and prediction["decision"] == decision
        ]

        matches.sort(key=lambda item: item[0]["filename"])

        if len(matches) < IMAGES_PER_CATEGORY:
            raise ValueError(
                f"Insufficient images for {group}/{decision}: {len(matches)}"
            )

        for rank, (prediction, label) in enumerate(
            matches[:IMAGES_PER_CATEGORY], start=1
        ):
            filename = prediction["filename"]
            image_path = IMAGE_DIR / filename

            if not image_path.is_file():
                raise FileNotFoundError(image_path)

            selected.append({
                "group": group,
                "decision_category": decision,
                "selection_rank": rank,
                "patient_id": prediction["patient_id"],
                "eye": prediction["eye"],
                "filename": filename,
                "diagnosis_text": label["diagnosis_text"],
                "true_label": prediction["true_label"],
                "calibrated_probability": prediction["calibrated_probability"],
                "decision": prediction["decision"],
                "is_uncertain": prediction["is_uncertain"],
                "checkpoint_sha256": prediction["checkpoint_sha256"],
                "settings_sha256": prediction["settings_sha256"],
                "heatmap_filename": "",
                "processing_status": "Not generated",
            })

    if len(selected) != 21:
        raise AssertionError(f"Expected 21 images, got {len(selected)}")

    if len({row["filename"] for row in selected}) != len(selected):
        raise ValueError("Duplicate image selected")

    return selected


def main():
    if OUTPUT_FILE.exists():
        raise FileExistsError(f"Refusing to overwrite: {OUTPUT_FILE}")

    rows = select_images()
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)

    print(f"Selected images: {len(rows)}")
    for group, decision in CATEGORIES:
        count = sum(
            row["group"] == group and row["decision_category"] == decision
            for row in rows
        )
        print(f"{group} | {decision}: {count}")

    print(f"Selection saved: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
