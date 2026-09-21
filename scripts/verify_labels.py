"""Task 3: checks the ODIR label file.

The expected numbers are taken from the brief, so we compare the label file
to what it should be. Prints PASS or FAIL for each check.

Run from the repo folder:

    python scripts/verify_labels.py labels/eye_labels_task7.csv

Optional:
    --images "<Datasets>/Internal/ODIR-5K/Training Images"   check all image files exist
    --manifest "<Datasets>"   check the data files against MANIFEST.sha256 (takes a bit longer)

The stub (labels/labels_stub.csv) should fail, since it only has 22 fake rows.
Checks for the external datasets come later (after Task 9).
"""
import argparse
import csv
import hashlib
import os
import sys
from collections import defaultdict

# Expected counts per eye (from the brief)
EXPECTED_COUNTS = {
    "rows": 7000,
    "cataract": 313,
    "glaucoma": 282,
    "suspected_glaucoma": 44,
    "media_opacity": 63,
    "image_quality_flag": 426,
    "exclusion": 30,
    "normal_only": 2818,
    "diabetic_retinopathy": 1796,
}

# Expected counts per patient (from the brief)
EXPECTED_PATIENTS = {
    "patients with cataract in one eye only": 111,
    "patients with glaucoma in one eye only": 72,
    "patients with both cataract and glaucoma": 1,
}

COLUMNS = ["patient_id", "eye", "filename", "diagnosis_text", "cataract", "glaucoma",
           "suspected_glaucoma", "media_opacity", "image_quality_flag", "exclusion", "split"]
SPLITS = {"train", "validation", "test", "holdout", "excluded"}
MAIN_SPLITS = ("train", "validation", "test")
TARGET_SHARE = {"train": 0.70, "validation": 0.15, "test": 0.15}
SHARE_TOLERANCE = 0.01  # allow 1% difference from 70/15/15

DR = {"mild nonproliferative retinopathy", "moderate non proliferative retinopathy",
      "severe nonproliferative retinopathy", "proliferative diabetic retinopathy",
      "severe proliferative diabetic retinopathy", "diabetic retinopathy"}


def tokens(text):
    """Split the diagnosis text into separate phrases (some cells use a Chinese comma)."""
    text = (text or "").replace("，", ",").lower()
    return {" ".join(t.split()) for t in text.split(",") if t.strip()}


class Report:
    def __init__(self):
        self.passed = 0
        self.failed = 0

    def check(self, name, ok, detail):
        print(f"  {'PASS' if ok else 'FAIL'}  {name}: {detail}")
        if ok:
            self.passed += 1
        else:
            self.failed += 1

    def equal(self, name, got, expected):
        self.check(name, got == expected, f"{got}" if got == expected else f"expected {expected}, got {got}")


def check_labels(rows, report):
    # 1. Columns
    columns = list(rows[0].keys()) if rows else []
    report.equal("columns", columns, COLUMNS)
    if columns != COLUMNS:
        print("  Stopping: the other checks need the agreed columns.")
        return

    # 2. Per-eye counts
    counts = {"rows": len(rows)}
    for col in ("cataract", "glaucoma", "suspected_glaucoma", "media_opacity",
                "image_quality_flag", "exclusion"):
        counts[col] = sum(int(r[col]) for r in rows)
    counts["normal_only"] = sum(tokens(r["diagnosis_text"]) == {"normal fundus"} for r in rows)
    counts["diabetic_retinopathy"] = sum(bool(tokens(r["diagnosis_text"]) & DR) for r in rows)
    for name, expected in EXPECTED_COUNTS.items():
        report.equal(name, counts[name], expected)

    # 3. Per-patient counts
    by_patient = defaultdict(list)
    for r in rows:
        by_patient[r["patient_id"]].append(r)
    cataract_eyes = {p: sum(int(r["cataract"]) for r in eyes) for p, eyes in by_patient.items()}
    glaucoma_eyes = {p: sum(int(r["glaucoma"]) for r in eyes) for p, eyes in by_patient.items()}
    both = [p for p in by_patient if cataract_eyes[p] and glaucoma_eyes[p]]
    got = {
        "patients with cataract in one eye only": sum(n == 1 for n in cataract_eyes.values()),
        "patients with glaucoma in one eye only": sum(n == 1 for n in glaucoma_eyes.values()),
        "patients with both cataract and glaucoma": len(both),
    }
    for name, expected in EXPECTED_PATIENTS.items():
        report.equal(name, got[name], expected)

    # 4. Filenames
    names = [r["filename"] for r in rows]
    dupes = len(names) - len(set(names))
    report.check("no duplicate filenames", dupes == 0, "none" if dupes == 0 else f"{dupes} duplicates")

    # 5. Split
    bad = sorted({r["split"] for r in rows} - SPLITS)
    report.check("split names", not bad,
                 "all in " + ", ".join(sorted(SPLITS)) if not bad else f"unknown names {bad}")

    groups = defaultdict(set)
    for r in rows:
        if r["split"] in MAIN_SPLITS:
            groups[r["patient_id"]].add(r["split"])
    leaks = [p for p, s in groups.items() if len(s) > 1]
    report.check("no patient in more than one of train/validation/test", not leaks,
                 "none" if not leaks else f"{len(leaks)} patients, e.g. {leaks[:3]}")

    set_aside = [r["filename"] for r in rows if r["split"] in MAIN_SPLITS and (
        int(r["suspected_glaucoma"]) or int(r["media_opacity"]) or int(r["exclusion"]))]
    report.check("no suspected glaucoma, media opacity or excluded eye in train/validation/test",
                 not set_aside, "none" if not set_aside else f"{len(set_aside)} eyes, e.g. {set_aside[:3]}")

    both_splits = {r["split"] for p in both for r in by_patient[p] if r["split"] in MAIN_SPLITS}
    report.check("patient with both conditions is in train", both_splits == {"train"},
                 "yes" if both_splits == {"train"} else f"found in {sorted(both_splits) or 'no main split'}")

    patients_in = {s: sum(s in g for g in groups.values()) for s in MAIN_SPLITS}
    total = sum(patients_in.values())
    for s in MAIN_SPLITS:
        share = patients_in[s] / total if total else 0
        report.check(f"{s} share of patients", abs(share - TARGET_SHARE[s]) <= SHARE_TOLERANCE,
                     f"{patients_in[s]} patients, {share:.1%} (target {TARGET_SHARE[s]:.0%})")


def check_images(rows, folder, report):
    on_disk = set(os.listdir(folder))
    missing = [r["filename"] for r in rows if r["filename"] not in on_disk]
    report.check("every filename exists in the image folder", not missing,
                 "all found" if not missing else f"{len(missing)} missing, e.g. {missing[:3]}")


def check_manifest(datasets, report):
    manifest = os.path.join(datasets, "MANIFEST.sha256")
    bad, total = [], 0
    with open(manifest, encoding="utf-8") as f:
        for line in f:
            expected, path = line.rstrip("\n").split("  ", 1)
            total += 1
            full = os.path.join(datasets, path)
            if not os.path.exists(full):
                bad.append(f"{path} (missing)")
                continue
            h = hashlib.sha256()
            with open(full, "rb") as data:
                for chunk in iter(lambda: data.read(1 << 20), b""):
                    h.update(chunk)
            if h.hexdigest() != expected:
                bad.append(f"{path} (changed)")
    report.check("data files match MANIFEST.sha256", not bad,
                 f"all {total} match" if not bad else f"{len(bad)} of {total} differ, e.g. {bad[:3]}")


def main():
    parser = argparse.ArgumentParser(description="Check the ODIR-5K label file (Task 3).")
    parser.add_argument("labels", help="path to the label CSV")
    parser.add_argument("--images", help="ODIR-5K 'Training Images' folder")
    parser.add_argument("--manifest", help="Datasets folder that holds MANIFEST.sha256")
    args = parser.parse_args()

    with open(args.labels, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    report = Report()
    print(f"Checking {args.labels}")
    check_labels(rows, report)
    if args.images:
        check_images(rows, args.images, report)
    if args.manifest:
        check_manifest(args.manifest, report)

    print(f"\n{report.passed} passed, {report.failed} failed.")
    sys.exit(1 if report.failed else 0)


if __name__ == "__main__":
    main()
