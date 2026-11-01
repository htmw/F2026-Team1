
"""Team EyeQ - Task 13 / SCRUM-75: Internal test scoring.

Modes
-----
--preflight
    Verify frozen settings, checkpoints, labels and image paths.
    Never open test images or run inference.

--smoke-test
    Exercise calibration, decision rules and CSV serialization
    using synthetic logits only. Never open test images.

--run-internal-test --confirm-one-time-test
    Score the approved internal test split using all nine checkpoints.
    This is intentionally gated and must be run only after review.

Approved training, model, preprocessing and calibration scripts
are imported, not modified.

No calibration fitting, threshold selection or model training occurs.
"""

import argparse
import csv
import json
import platform
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
from torch.utils.data import DataLoader

from calibrate_models import (
    PROJECT_ROOT,
    LABELS_FILE,
    IMAGE_DIR,
    SEEDS,
    file_sha256,
    load_cataract_model,
    load_glaucoma_model,
)
from calibrate_shared_models import load_model
from evaluate_calibration_holdout import verify_settings
from fundus_dataset import FundusDataset, get_validation_transform


SETTINGS_FILE = (
    PROJECT_ROOT / "results/calibration/frozen_settings.json"
)

OUTPUT_DIR = PROJECT_ROOT / "results/task13/internal_test"

EXPECTED_TEST_EYES = 1036
EXPECTED_TEST_PATIENTS = 522

DISEASES = ("cataract", "glaucoma")
MODEL_KINDS = ("single", "shared")
NORMAL_SPLITS = ("train", "validation", "test")

PREDICTION_FIELDS = [
    "model_kind",
    "seed",
    "disease",
    "patient_id",
    "eye",
    "filename",
    "true_label",
    "raw_logit",
    "calibrated_probability",
    "threshold",
    "uncertain_margin",
    "decision",
    "is_uncertain",
    "is_referred",
    "checkpoint_sha256",
    "settings_sha256",
]


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def load_and_verify_settings():
    """Reuse approved frozen-settings and checkpoint verification."""
    if not SETTINGS_FILE.is_file():
        raise FileNotFoundError(
            f"Frozen settings not found: {SETTINGS_FILE}"
        )

    settings = verify_settings(SETTINGS_FILE)

    print("PASS: Frozen calibration settings verified.")
    print("PASS: Checkpoint fingerprints verified.")

    return settings


def load_labels():
    """Read CSV metadata without opening any images."""
    if not LABELS_FILE.is_file():
        raise FileNotFoundError(LABELS_FILE)

    with LABELS_FILE.open(
        newline="", encoding="utf-8"
    ) as handle:
        reader = csv.DictReader(handle)

        required = {
            "patient_id",
            "eye",
            "filename",
            "cataract",
            "glaucoma",
            "split",
        }

        if reader.fieldnames is None:
            raise ValueError("Labels CSV has no header.")

        missing = required - set(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Missing label columns: {sorted(missing)}"
            )

        rows = list(reader)

    if not rows:
        raise ValueError("Labels CSV is empty.")

    return rows


def verify_test_metadata(rows):
    """Validate test identities, labels and normal-split separation."""
    test_rows = [
        row for row in rows
        if row["split"] == "test"
    ]

    if len(test_rows) != EXPECTED_TEST_EYES:
        raise ValueError(
            f"Expected {EXPECTED_TEST_EYES} test eyes, "
            f"found {len(test_rows)}."
        )

    filenames = [row["filename"] for row in test_rows]
    patients = [row["patient_id"] for row in test_rows]

    if any(not value.strip() for value in filenames):
        raise ValueError("Empty test filename.")

    if len(set(filenames)) != len(filenames):
        raise ValueError("Duplicate test filenames.")

    if any(not value.strip() for value in patients):
        raise ValueError("Missing test patient ID.")

    if len(set(patients)) != EXPECTED_TEST_PATIENTS:
        raise ValueError(
            f"Expected {EXPECTED_TEST_PATIENTS} test patients, "
            f"found {len(set(patients))}."
        )

    for row in test_rows:
        for disease in DISEASES:
            if row[disease] not in ("0", "1"):
                raise ValueError(
                    f"Invalid {disease} label: {row['filename']}"
                )

    patient_splits = {}

    for row in rows:
        if row["split"] not in NORMAL_SPLITS:
            continue

        patient = row["patient_id"]

        if not patient.strip():
            raise ValueError("Missing normal-split patient ID.")

        patient_splits.setdefault(patient, set()).add(
            row["split"]
        )

    overlapping = [
        patient
        for patient, splits in patient_splits.items()
        if len(splits) > 1
    ]

    if overlapping:
        raise ValueError(
            f"{len(overlapping)} patients overlap across "
            "train/validation/test."
        )

    eye_keys = [
        (row["patient_id"], row["eye"])
        for row in rows
    ]

    if len(set(eye_keys)) != len(eye_keys):
        raise ValueError("Duplicate patient/eye rows.")

    print(f"PASS: {len(test_rows)} unique internal test eyes.")
    print(f"PASS: {len(set(patients))} internal test patients.")
    print("PASS: Binary disease labels.")
    print("PASS: No normal-split patient leakage.")
    print("PASS: No duplicate patient/eye rows.")

    return test_rows


def verify_image_paths(test_rows):
    """Check paths without decoding or loading test images."""
    if not IMAGE_DIR.is_dir():
        raise FileNotFoundError(IMAGE_DIR)

    root = IMAGE_DIR.resolve()

    for row in test_rows:
        path = (IMAGE_DIR / row["filename"]).resolve()

        if not path.is_relative_to(root):
            raise ValueError(
                f"Image escapes approved directory: "
                f"{row['filename']}"
            )

        if not path.is_file():
            raise FileNotFoundError(path)

    print(
        f"PASS: All {len(test_rows)} test image paths exist."
    )


def verify_run_configuration(settings):
    """Require all 12 settings and nine distinct checkpoints."""
    expected = {
        (kind, disease, seed)
        for kind in MODEL_KINDS
        for disease in DISEASES
        for seed in SEEDS
    }

    runs = settings["runs"]

    actual = [
        (run["model_kind"], run["disease"], run["seed"])
        for run in runs
    ]

    if len(actual) != len(expected) or set(actual) != expected:
        raise ValueError(
            "Expected exactly 12 unique model/head/seed settings."
        )

    checkpoints = {
        run["checkpoint"]
        for run in runs
    }

    if len(checkpoints) != 9:
        raise ValueError(
            f"Expected 9 checkpoints, found {len(checkpoints)}."
        )

    for seed in SEEDS:
        shared = {
            run["checkpoint"]
            for run in runs
            if run["model_kind"] == "shared"
            and run["seed"] == seed
        }

        if len(shared) != 1:
            raise ValueError(
                f"Inconsistent shared checkpoint for seed {seed}."
            )

    print("PASS: 12 model/head/seed settings.")
    print("PASS: 9 distinct checkpoints.")


def run_preflight():
    """Perform all metadata and integrity checks."""
    print("=" * 60)
    print("TEAM EYEQ - TASK 13 PREFLIGHT")
    print("=" * 60)

    settings = load_and_verify_settings()
    verify_run_configuration(settings)

    rows = load_labels()
    test_rows = verify_test_metadata(rows)

    verify_image_paths(test_rows)

    counts = Counter(row["split"] for row in rows)

    print("\nDataset split counts:")

    for split in (
        "train",
        "validation",
        "test",
        "holdout",
        "excluded",
    ):
        print(f"  {split}: {counts.get(split, 0)}")

    print("\nFrozen settings SHA-256:")
    print(file_sha256(SETTINGS_FILE))

    print("\nPREFLIGHT PASSED")
    print("No model inference was performed.")

    return settings, test_rows


def settings_lookup(settings):
    """Index frozen settings by model, disease and seed."""
    return {
        (
            run["model_kind"],
            run["disease"],
            run["seed"],
        ): run
        for run in settings["runs"]
    }


def calibrate_and_decide(raw_logits, run):
    """Apply frozen Platt calibration and decision rules.

    The input must contain raw logits, not probabilities.
    """
    raw = np.asarray(raw_logits, dtype=np.float64)

    if raw.ndim != 1:
        raise ValueError("Expected one-dimensional logits.")

    if not np.isfinite(raw).all():
        raise ValueError("Nonfinite raw logits.")

    scale = float(run["scale"])
    offset = float(run["offset"])
    threshold = float(run["threshold"])
    margin = float(run["uncertain_margin"])

    values = (scale * raw) + offset

    # Stable sigmoid, avoiding overflow for extreme logits.
    probabilities = np.empty_like(values)

    positive = values >= 0

    probabilities[positive] = (
        1.0 / (1.0 + np.exp(-values[positive]))
    )

    exp_values = np.exp(values[~positive])

    probabilities[~positive] = (
        exp_values / (1.0 + exp_values)
    )

    if not np.isfinite(probabilities).all():
        raise ValueError("Nonfinite calibrated probabilities.")

    uncertain = (
        np.abs(probabilities - threshold) <= margin
    )

    ordinary_referral = (
        (probabilities >= threshold) & ~uncertain
    )

    referred = ordinary_referral | uncertain

    decisions = np.where(
        uncertain,
        "Uncertain, refer",
        np.where(
            ordinary_referral,
            "Refer",
            "No concern",
        ),
    )

    return probabilities, decisions, uncertain, referred


def make_prediction_rows(
    test_rows,
    raw_logits,
    run,
    settings_hash,
):
    """Build disease-specific per-eye output records."""
    if len(raw_logits) != len(test_rows):
        raise ValueError(
            "Prediction count does not match test labels."
        )

    probabilities, decisions, uncertain, referred = (
        calibrate_and_decide(raw_logits, run)
    )

    output = []

    for index, row in enumerate(test_rows):
        disease = run["disease"]

        output.append({
            "model_kind": run["model_kind"],
            "seed": int(run["seed"]),
            "disease": disease,
            "patient_id": row["patient_id"],
            "eye": row["eye"],
            "filename": row["filename"],
            "true_label": int(row[disease]),
            "raw_logit": float(raw_logits[index]),
            "calibrated_probability": float(
                probabilities[index]
            ),
            "threshold": float(run["threshold"]),
            "uncertain_margin": float(
                run["uncertain_margin"]
            ),
            "decision": str(decisions[index]),
            "is_uncertain": int(uncertain[index]),
            "is_referred": int(referred[index]),
            "checkpoint_sha256": run[
                "checkpoint_sha256"
            ],
            "settings_sha256": settings_hash,
        })

    return output


def write_csv(path, records):
    """Write CSV with explicit schema; never overwrite."""
    with path.open(
        "x", newline="", encoding="utf-8"
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=PREDICTION_FIELDS,
        )
        writer.writeheader()
        writer.writerows(records)


def synthetic_smoke_test():
    """Check scoring and serialization without real test data."""
    print("Running synthetic smoke tests...")

    run = {
        "model_kind": "single",
        "disease": "cataract",
        "seed": 42,
        "scale": 1.0,
        "offset": 0.0,
        "threshold": 0.5,
        "uncertain_margin": 0.05,
        "checkpoint_sha256": "synthetic-checkpoint",
    }

    logits = np.array(
        [-10.0, 0.0, 10.0],
        dtype=np.float64,
    )

    probabilities, decisions, uncertain, referred = (
        calibrate_and_decide(logits, run)
    )

    assert probabilities[0] < 0.01
    assert abs(probabilities[1] - 0.5) < 1e-12
    assert probabilities[2] > 0.99

    assert list(decisions) == [
        "No concern",
        "Uncertain, refer",
        "Refer",
    ]

    assert list(uncertain) == [False, True, False]
    assert list(referred) == [False, True, True]

    test_rows = [
        {
            "patient_id": "1",
            "eye": "left",
            "filename": "synthetic_1.jpg",
            "cataract": "0",
            "glaucoma": "0",
        },
        {
            "patient_id": "2",
            "eye": "left",
            "filename": "synthetic_2.jpg",
            "cataract": "1",
            "glaucoma": "0",
        },
        {
            "patient_id": "3",
            "eye": "right",
            "filename": "synthetic_3.jpg",
            "cataract": "1",
            "glaucoma": "0",
        },
    ]

    records = make_prediction_rows(
        test_rows,
        logits,
        run,
        "synthetic-settings",
    )

    assert len(records) == 3

    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "synthetic_predictions.csv"

        write_csv(path, records)

        with path.open(
            newline="", encoding="utf-8"
        ) as handle:
            saved = list(csv.DictReader(handle))

        assert len(saved) == 3
        assert saved[1]["decision"] == "Uncertain, refer"
        assert saved[2]["patient_id"] == "3"

        # Existing outputs must never be overwritten.
        try:
            write_csv(path, records)
        except FileExistsError:
            pass
        else:
            raise AssertionError(
                "Output overwrite protection failed."
            )

    # Reject invalid numerical predictions.
    try:
        calibrate_and_decide(
            np.array([float("nan")]),
            run,
        )
    except ValueError:
        pass
    else:
        raise AssertionError(
            "Nonfinite prediction was accepted."
        )

    print("PASS: Frozen calibration arithmetic.")
    print("PASS: Uncertain/referral decision rules.")
    print("PASS: Prediction-to-patient alignment.")
    print("PASS: CSV serialization.")
    print("PASS: Overwrite protection.")
    print("PASS: Nonfinite prediction rejection.")
    print("SMOKE TEST PASSED")
    print("No real test images or checkpoints were loaded.")


def build_test_loader():
    """Use approved deterministic preprocessing and fixed order."""
    dataset = FundusDataset(
        labels_csv=LABELS_FILE,
        image_dir=IMAGE_DIR,
        split="test",
        transform=get_validation_transform(),
    )

    if len(dataset) != EXPECTED_TEST_EYES:
        raise ValueError(
            "Unexpected test dataset length."
        )

    return DataLoader(
        dataset,
        batch_size=8,
        shuffle=False,
        num_workers=0,
    )


def collect_model_logits(models, loader, expected_rows):
    """Collect both disease logits with filename alignment checks.

    `models` contains either:
      - one shared two-head model, or
      - separate cataract and glaucoma models.
    """
    scores = {
        "cataract": [],
        "glaucoma": [],
    }

    observed_names = []

    # Explicit CPU placement for consistent evaluation.
    for model in models:
        model.to("cpu")
        model.eval()

    with torch.inference_mode():
        for batch in loader:
            names = list(batch["filename"])
            images = batch["image"].to("cpu")

            if len(models) == 1:
                outputs = models[0](images)
            else:
                outputs = tuple(
                    model(images)
                    for model in models
                )

            if not isinstance(outputs, (tuple, list)):
                raise ValueError(
                    "Expected separate cataract and glaucoma logits."
                )

            if len(outputs) != 2:
                raise ValueError(
                    "Expected exactly two disease outputs."
                )

            for disease, logits in zip(
                DISEASES, outputs, strict=True
            ):
                values = logits.reshape(-1)

                if values.numel() != len(names):
                    raise ValueError(
                        f"Unexpected {disease} output shape."
                    )

                if not torch.isfinite(values).all():
                    raise ValueError(
                        f"Nonfinite {disease} prediction."
                    )

                scores[disease].extend(
                    values.detach().cpu().tolist()
                )

            observed_names.extend(names)

    expected_names = [
        row["filename"]
        for row in expected_rows
    ]

    if observed_names != expected_names:
        raise ValueError(
            "Model prediction order does not match label order."
        )

    for disease in DISEASES:
        if len(scores[disease]) != EXPECTED_TEST_EYES:
            raise ValueError(
                f"Wrong {disease} prediction count."
            )

    return scores


def load_models(kind, seed, runs):
    """Load approved checkpoints without changing model weights."""
    if kind == "shared":
        model, _checkpoint = load_model(seed)
        return [model]

    cataract_model = load_cataract_model(seed)

    glaucoma_path = (
        PROJECT_ROOT
        / runs[("single", "glaucoma", seed)]["checkpoint"]
    )

    glaucoma_model = load_glaucoma_model(
        glaucoma_path,
        seed,
    )

    return [cataract_model, glaucoma_model]


def run_internal_test():
    """Execute the one-time internal test after explicit authorization."""
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Output directory already exists: {OUTPUT_DIR}. "
            "Refusing to overwrite or repeat the evaluation."
        )

    settings, test_rows = run_preflight()

    # Create the output directory exclusively before any test inference.
    # A failed run leaves the directory in place, blocking a rerun
    # until the team reviews the failure.
    OUTPUT_DIR.mkdir(parents=True, exist_ok=False)

    started_at = utc_now()
    settings_hash = file_sha256(SETTINGS_FILE)
    runs = settings_lookup(settings)

    manifest = {
        "task": "SCRUM-75",
        "split": "test",
        "status": "started",
        "started_at_utc": started_at,
        "settings_sha256": settings_hash,
        "labels_sha256": file_sha256(LABELS_FILE),
        "test_eyes": len(test_rows),
        "test_patients": len({
            row["patient_id"]
            for row in test_rows
        }),
        "model_kinds": list(MODEL_KINDS),
        "seeds": list(SEEDS),
        "diseases": list(DISEASES),
        "batch_size": 8,
        "device": "cpu",
        "transform": "get_validation_transform",
        "python_version": sys.version,
        "platform": platform.platform(),
        "torch_version": torch.__version__,
        "numpy_version": np.__version__,
        "checkpoints": {
            run["checkpoint"]: run["checkpoint_sha256"]
            for run in settings["runs"]
        },
        "outputs": [],
    }

    manifest_path = OUTPUT_DIR / "run_manifest.json"

    def save_manifest():
        with manifest_path.open(
            "w", encoding="utf-8"
        ) as handle:
            json.dump(
                manifest,
                handle,
                indent=2,
                allow_nan=False,
                default=str,
            )
            handle.write("\n")

    save_manifest()

    try:
        torch.set_num_threads(4)

        loader = build_test_loader()

        for kind in MODEL_KINDS:
            for seed in SEEDS:
                print(
                    f"Scoring model_kind={kind}, seed={seed}",
                    flush=True,
                )

                models = load_models(
                    kind,
                    seed,
                    runs,
                )

                scores = collect_model_logits(
                    models,
                    loader,
                    test_rows,
                )

                for disease in DISEASES:
                    run = runs[(kind, disease, seed)]

                    records = make_prediction_rows(
                        test_rows,
                        scores[disease],
                        run,
                        settings_hash,
                    )

                    filename = (
                        f"{kind}_{disease}_seed_{seed}_test.csv"
                    )

                    output_path = OUTPUT_DIR / filename

                    write_csv(output_path, records)

                    manifest["outputs"].append({
                        "filename": filename,
                        "rows": len(records),
                        "sha256": file_sha256(output_path),
                        "model_kind": kind,
                        "seed": seed,
                        "disease": disease,
                    })

                    save_manifest()

                del models
                del scores

        if len(manifest["outputs"]) != 12:
            raise ValueError(
                "Expected exactly 12 prediction CSV files."
            )

        manifest["status"] = "completed"
        manifest["completed_at_utc"] = utc_now()
        save_manifest()

        print("\nINTERNAL TEST SCORING COMPLETED")
        print(f"Output directory: {OUTPUT_DIR}")
        print("Prediction CSV files: 12")
        print("No calibration fitting was performed.")

    except BaseException as exc:
        manifest["status"] = "failed"
        manifest["failed_at_utc"] = utc_now()
        manifest["failure"] = (
            f"{type(exc).__name__}: {exc}"
        )

        save_manifest()
        raise


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    modes = parser.add_mutually_exclusive_group(
        required=True
    )

    modes.add_argument(
        "--preflight",
        action="store_true",
        help="Verify metadata and checkpoints only.",
    )

    modes.add_argument(
        "--smoke-test",
        action="store_true",
        help="Test calculations with synthetic logits only.",
    )

    modes.add_argument(
        "--run-internal-test",
        action="store_true",
        help="Run real internal test inference.",
    )

    parser.add_argument(
        "--confirm-one-time-test",
        action="store_true",
        help="Explicit authorization flag for real test inference.",
    )

    args = parser.parse_args()

    if args.preflight:
        run_preflight()

    elif args.smoke_test:
        synthetic_smoke_test()

    elif args.run_internal_test:
        if not args.confirm_one_time_test:
            parser.error(
                "Real test inference requires "
                "--confirm-one-time-test."
            )

        run_internal_test()


if __name__ == "__main__":
    main()
