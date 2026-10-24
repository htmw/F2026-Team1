
"""Team EyeQ SCRUM-76: Internal-test AUROC with patient-clustered 95% CIs.

DRAFT: Internal Task 13 bootstrap methodology requires team approval.

Reads SCRUM-75 prediction CSVs without running inference,
refitting calibration, or changing decision thresholds.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.metrics import roc_auc_score


PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = PROJECT_ROOT / "results/task13/internal_test"
OUTPUT_DIR = PROJECT_ROOT / "results/task13/internal_auc_ci"

DISEASES = ("cataract", "glaucoma")
MODEL_KINDS = ("single", "shared")
SEEDS = (42, 43, 44)

BOOTSTRAP_REPLICATES = 2000
BOOTSTRAP_RANDOM_SEED = 42
MAX_BOOTSTRAP_ATTEMPTS = 10000

EXPECTED_TEST_EYES = 1036
EXPECTED_TEST_PATIENTS = 522

REQUIRED_COLUMNS = {
    "model_kind",
    "seed",
    "disease",
    "patient_id",
    "eye",
    "filename",
    "true_label",
    "calibrated_probability",
    "checkpoint_sha256",
    "settings_sha256",
}

RESULT_FIELDS = (
    "model_kind",
    "disease",
    "seed",
    "n_eyes",
    "n_patients",
    "n_positive",
    "n_negative",
    "auroc",
    "ci_lower_95",
    "ci_upper_95",
    "bootstrap_valid",
    "bootstrap_attempts",
    "checkpoint_sha256",
    "settings_sha256",
)

SUMMARY_FIELDS = (
    "model_kind",
    "disease",
    "n_seeds",
    "mean_auroc",
    "sample_sd_auroc",
)


def expected_runs():
    return [
        (kind, disease, seed)
        for kind in MODEL_KINDS
        for disease in DISEASES
        for seed in SEEDS
    ]


def prediction_file_path(kind, disease, seed, input_dir):
    if (kind, disease, seed) not in expected_runs():
        raise ValueError("Invalid model/disease/seed combination")

    return input_dir / (
        f"{kind}_{disease}_seed_{seed}_test.csv"
    )


def sha256_file(path):
    digest = hashlib.sha256()

    with path.open("rb") as stream:
        for chunk in iter(
            lambda: stream.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def normalize_sha256(value, description):
    if not isinstance(value, str):
        raise ValueError(f"Invalid SHA-256: {description}")

    value = value.lower()

    if (
        len(value) != 64
        or any(c not in "0123456789abcdef" for c in value)
    ):
        raise ValueError(f"Invalid SHA-256: {description}")

    return value


def validate_source_manifest(input_dir):
    """Verify that SCRUM-75 completed all 12 prediction runs."""
    path = input_dir / "run_manifest.json"

    if not path.is_file():
        raise FileNotFoundError(
            f"SCRUM-75 manifest missing: {path}"
        )

    with path.open(encoding="utf-8") as stream:
        manifest = json.load(stream)

    if not isinstance(manifest, dict):
        raise ValueError("Invalid SCRUM-75 manifest")

    if manifest.get("task") != "SCRUM-75":
        raise ValueError("Incorrect source task")

    if manifest.get("split") != "test":
        raise ValueError("Incorrect source split")

    if manifest.get("status") != "completed":
        raise ValueError(
            "SCRUM-75 has not completed successfully"
        )

    if not manifest.get("completed_at_utc"):
        raise ValueError("Missing completion timestamp")

    if (
        type(manifest.get("test_eyes")) is not int
        or manifest["test_eyes"] != EXPECTED_TEST_EYES
    ):
        raise ValueError("Incorrect internal-test eye count")

    if (
        type(manifest.get("test_patients")) is not int
        or manifest["test_patients"] != EXPECTED_TEST_PATIENTS
    ):
        raise ValueError("Incorrect internal-test patient count")

    for field, expected in (
        ("model_kinds", MODEL_KINDS),
        ("diseases", DISEASES),
        ("seeds", SEEDS),
    ):
        actual = manifest.get(field)

        if (
            not isinstance(actual, list)
            or len(actual) != len(expected)
            or set(actual) != set(expected)
        ):
            raise ValueError(
                f"Incorrect manifest configuration: {field}"
            )

    settings_hash = normalize_sha256(
        manifest.get("settings_sha256"),
        "manifest settings",
    )

    checkpoints = manifest.get("checkpoints")

    if not isinstance(checkpoints, dict) or not checkpoints:
        raise ValueError("Missing checkpoint records")

    checkpoint_hashes = {
        normalize_sha256(value, str(name))
        for name, value in checkpoints.items()
    }

    outputs = manifest.get("outputs")

    if not isinstance(outputs, list) or len(outputs) != 12:
        raise ValueError(
            "SCRUM-75 must contain exactly 12 outputs"
        )

    expected = set(expected_runs())
    seen = set()
    source_hashes = {}

    for entry in outputs:
        if not isinstance(entry, dict):
            raise ValueError("Invalid output entry")

        kind = entry.get("model_kind")
        disease = entry.get("disease")
        seed = entry.get("seed")

        if type(seed) is not int:
            raise ValueError("Invalid output seed")

        run = (kind, disease, seed)

        if run not in expected or run in seen:
            raise ValueError(
                f"Unexpected or duplicate output: {run}"
            )

        seen.add(run)

        csv_path = prediction_file_path(
            kind, disease, seed, input_dir
        )

        if entry.get("filename") != csv_path.name:
            raise ValueError(
                f"Incorrect output filename: {run}"
            )

        if (
            type(entry.get("rows")) is not int
            or entry["rows"] != EXPECTED_TEST_EYES
        ):
            raise ValueError(
                f"Incorrect output row count: {run}"
            )

        recorded_hash = normalize_sha256(
            entry.get("sha256"),
            csv_path.name,
        )

        if not csv_path.is_file():
            raise FileNotFoundError(csv_path)

        actual_hash = sha256_file(csv_path)

        if actual_hash != recorded_hash:
            raise ValueError(
                f"Prediction CSV hash mismatch: {csv_path.name}"
            )

        source_hashes[csv_path.name] = actual_hash

    if seen != expected:
        raise ValueError("Incomplete SCRUM-75 outputs")

    return {
        "manifest_sha256": sha256_file(path),
        "settings_sha256": settings_hash,
        "checkpoint_hashes": checkpoint_hashes,
        "source_hashes": source_hashes,
    }


def load_prediction_csv(path, kind, disease, seed):
    """Validate one prediction file and its patient-eye records."""
    with path.open(newline="", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)

        if not reader.fieldnames:
            raise ValueError(f"Missing CSV header: {path}")

        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError(f"Duplicate CSV columns: {path}")

        missing = REQUIRED_COLUMNS.difference(reader.fieldnames)

        if missing:
            raise ValueError(
                f"Missing CSV columns in {path}: {sorted(missing)}"
            )

        raw_rows = list(reader)

    if len(raw_rows) != EXPECTED_TEST_EYES:
        raise ValueError(
            f"Expected {EXPECTED_TEST_EYES} eyes in {path}"
        )

    parsed = {}
    checkpoint_hashes = set()
    settings_hashes = set()

    for line, row in enumerate(raw_rows, start=2):
        if (
            row["model_kind"] != kind
            or row["disease"] != disease
            or row["seed"] != str(seed)
        ):
            raise ValueError(
                f"Run metadata mismatch at {path}:{line}"
            )

        patient_id = row["patient_id"].strip()
        eye = row["eye"].strip()
        filename = row["filename"].strip()

        if not patient_id or not eye or not filename:
            raise ValueError(
                f"Missing patient/eye/filename at {path}:{line}"
            )

        key = (patient_id, eye)

        if key in parsed:
            raise ValueError(
                f"Duplicate patient-eye key at {path}:{line}"
            )

        if row["true_label"] not in ("0", "1"):
            raise ValueError(
                f"Invalid label at {path}:{line}"
            )

        try:
            probability = float(
                row["calibrated_probability"]
            )
        except (TypeError, ValueError) as exc:
            raise ValueError(
                f"Invalid probability at {path}:{line}"
            ) from exc

        if (
            not math.isfinite(probability)
            or not 0 <= probability <= 1
        ):
            raise ValueError(
                f"Out-of-range probability at {path}:{line}"
            )

        checkpoint_hash = normalize_sha256(
            row["checkpoint_sha256"],
            f"{path}:{line} checkpoint",
        )

        settings_hash = normalize_sha256(
            row["settings_sha256"],
            f"{path}:{line} settings",
        )

        checkpoint_hashes.add(checkpoint_hash)
        settings_hashes.add(settings_hash)

        parsed[key] = (
            filename,
            int(row["true_label"]),
            probability,
        )

    if (
        len({patient for patient, _ in parsed})
        != EXPECTED_TEST_PATIENTS
    ):
        raise ValueError(
            f"Incorrect patient count in {path}"
        )

    if (
        len(checkpoint_hashes) != 1
        or len(settings_hashes) != 1
    ):
        raise ValueError(
            f"Inconsistent hashes in {path}"
        )

    if {row[1] for row in parsed.values()} != {0, 1}:
        raise ValueError(
            f"Both label classes required in {path}"
        )

    return (
        parsed,
        next(iter(checkpoint_hashes)),
        next(iter(settings_hashes)),
    )


def prepare_data(input_dir, source):
    """Verify all runs use matching patient-eye and image records."""
    datasets = {}
    baseline_keys = None
    filename_reference = None
    disease_references = {}

    for kind, disease, seed in expected_runs():
        path = prediction_file_path(
            kind, disease, seed, input_dir
        )

        parsed, checkpoint_hash, settings_hash = (
            load_prediction_csv(
                path, kind, disease, seed
            )
        )

        if (
            sha256_file(path)
            != source["source_hashes"][path.name]
        ):
            raise ValueError(
                f"Source CSV changed: {path}"
            )

        if settings_hash != source["settings_sha256"]:
            raise ValueError(
                f"Settings hash mismatch: {path}"
            )

        if checkpoint_hash not in source["checkpoint_hashes"]:
            raise ValueError(
                f"Unknown checkpoint hash: {path}"
            )

        keys = set(parsed)

        if baseline_keys is None:
            baseline_keys = keys
        elif keys != baseline_keys:
            raise ValueError(
                f"Patient-eye membership differs: {path}"
            )

        filenames = {
            key: row[0]
            for key, row in parsed.items()
        }

        if filename_reference is None:
            filename_reference = filenames
        elif filenames != filename_reference:
            raise ValueError(
                f"Image filenames differ: {path}"
            )

        metadata = {
            key: (row[0], row[1])
            for key, row in parsed.items()
        }

        if disease not in disease_references:
            disease_references[disease] = metadata
        elif metadata != disease_references[disease]:
            raise ValueError(
                f"Inconsistent {disease} labels: {path}"
            )

        datasets[(kind, disease, seed)] = {
            "rows": parsed,
            "checkpoint_sha256": checkpoint_hash,
            "settings_sha256": settings_hash,
        }

    return datasets


def make_arrays(datasets):
    """Align all predictions to identical patient-eye ordering."""
    keys = sorted(
        next(iter(datasets.values()))["rows"]
    )

    patient_ids = np.asarray([
        key[0] for key in keys
    ])

    arrays = {}

    for run, dataset in datasets.items():
        rows = dataset["rows"]

        labels = np.asarray(
            [rows[key][1] for key in keys],
            dtype=np.int8,
        )

        probabilities = np.asarray(
            [rows[key][2] for key in keys],
            dtype=np.float64,
        )

        arrays[run] = (labels, probabilities)

    return patient_ids, arrays


def bootstrap_patient_indices(
    patient_ids,
    labels_by_disease,
    replicates,
    seed,
    max_attempts,
):
    """Resample patients with replacement, retaining all their eyes.

    The same accepted samples are shared across every model,
    disease, and training seed.

    The attempt limit applies globally to the procedure.
    """
    if replicates < 1 or max_attempts < replicates:
        raise ValueError(
            "Invalid bootstrap configuration"
        )

    patients, inverse = np.unique(
        patient_ids,
        return_inverse=True,
    )

    groups = [
        np.flatnonzero(inverse == i)
        for i in range(len(patients))
    ]

    rng = np.random.default_rng(seed)

    samples = []
    attempts = 0

    while (
        len(samples) < replicates
        and attempts < max_attempts
    ):
        attempts += 1

        chosen = rng.integers(
            0,
            len(patients),
            size=len(patients),
        )

        indices = np.concatenate([
            groups[i] for i in chosen
        ])

        valid = all(
            np.unique(labels[indices]).size == 2
            for labels in labels_by_disease.values()
        )

        if valid:
            samples.append(indices)

    if len(samples) != replicates:
        raise RuntimeError(
            f"Only {len(samples)} valid samples "
            f"after {attempts} attempts; "
            "confidence intervals withheld"
        )

    return samples, attempts


def compute_results(
    datasets,
    *,
    replicates=BOOTSTRAP_REPLICATES,
    seed=BOOTSTRAP_RANDOM_SEED,
    max_attempts=MAX_BOOTSTRAP_ATTEMPTS,
):
    patient_ids, arrays = make_arrays(datasets)

    label_reference = {
        disease: arrays[
            ("single", disease, SEEDS[0])
        ][0]
        for disease in DISEASES
    }

    samples, attempts = bootstrap_patient_indices(
        patient_ids,
        label_reference,
        replicates,
        seed,
        max_attempts,
    )

    results = []

    for kind, disease, train_seed in expected_runs():
        run = (kind, disease, train_seed)

        labels, probabilities = arrays[run]

        point_auc = float(
            roc_auc_score(labels, probabilities)
        )

        bootstrap_aucs = np.asarray([
            float(
                roc_auc_score(
                    labels[indices],
                    probabilities[indices],
                )
            )
            for indices in samples
        ])

        low, high = np.percentile(
            bootstrap_aucs,
            [2.5, 97.5],
        )

        results.append({
            "model_kind": kind,
            "disease": disease,
            "seed": train_seed,
            "n_eyes": len(labels),
            "n_patients": len(np.unique(patient_ids)),
            "n_positive": int(labels.sum()),
            "n_negative": int(len(labels) - labels.sum()),
            "auroc": point_auc,
            "ci_lower_95": float(low),
            "ci_upper_95": float(high),
            "bootstrap_valid": len(samples),
            "bootstrap_attempts": attempts,
            "checkpoint_sha256": datasets[run][
                "checkpoint_sha256"
            ],
            "settings_sha256": datasets[run][
                "settings_sha256"
            ],
        })

    summary = []

    for kind in MODEL_KINDS:
        for disease in DISEASES:
            values = np.asarray([
                row["auroc"]
                for row in results
                if (
                    row["model_kind"] == kind
                    and row["disease"] == disease
                )
            ])

            if len(values) != len(SEEDS):
                raise ValueError(
                    f"Missing seeds: {kind}/{disease}"
                )

            summary.append({
                "model_kind": kind,
                "disease": disease,
                "n_seeds": len(values),
                "mean_auroc": float(values.mean()),
                "sample_sd_auroc": float(
                    values.std(ddof=1)
                ),
            })

    return results, summary, attempts


def write_csv(path, fieldnames, rows):
    with path.open(
        "w",
        newline="",
        encoding="utf-8",
    ) as stream:
        writer = csv.DictWriter(
            stream,
            fieldnames=fieldnames,
        )

        writer.writeheader()
        writer.writerows(rows)


def run_synthetic_smoke_test():
    """Synthetic-only bootstrap, reproducibility, and AUROC checks."""
    rng = np.random.default_rng(7)

    patient_ids = np.repeat(
        np.asarray([
            f"P{i:03d}" for i in range(24)
        ]),
        2,
    )

    cataract = np.tile(
        [0, 1, 0, 1],
        12,
    )

    glaucoma = np.tile(
        [1, 0, 0, 1],
        12,
    )

    labels = {
        "cataract": cataract,
        "glaucoma": glaucoma,
    }

    samples, attempts = bootstrap_patient_indices(
        patient_ids,
        labels,
        replicates=40,
        seed=42,
        max_attempts=200,
    )

    assert len(samples) == 40
    assert 40 <= attempts <= 200

    for indices in samples:
        counts = np.bincount(
            indices,
            minlength=len(patient_ids),
        )

        assert np.all(
            counts[::2] == counts[1::2]
        ), "Patient eyes not kept together"

        assert len(indices) == len(patient_ids)

        for disease_labels in labels.values():
            assert np.unique(
                disease_labels[indices]
            ).size == 2

    repeated, repeated_attempts = (
        bootstrap_patient_indices(
            patient_ids,
            labels,
            replicates=40,
            seed=42,
            max_attempts=200,
        )
    )

    assert attempts == repeated_attempts

    for first, second in zip(samples, repeated):
        assert np.array_equal(first, second)

    scores = np.clip(
        0.15
        + 0.7 * cataract
        + rng.normal(
            0,
            0.08,
            len(cataract),
        ),
        0,
        1,
    )

    auc = float(
        roc_auc_score(cataract, scores)
    )

    assert 0 <= auc <= 1

    bootstrap_aucs = np.asarray([
        float(
            roc_auc_score(
                cataract[indices],
                scores[indices],
            )
        )
        for indices in samples
    ])

    low, high = np.percentile(
        bootstrap_aucs,
        [2.5, 97.5],
    )

    assert (
        np.isfinite(low)
        and np.isfinite(high)
        and 0 <= low <= high <= 1
    )

    print(
        "Synthetic smoke test passed "
        f"(AUROC={auc:.4f}; bootstrap=40)."
    )
    print("Bootstrap reproducibility verified.")
    print("Synthetic percentile CI verified.")
    print("No internal-test files were read or written.")


def publish_results(results, summary, source, attempts):
    """Stage outputs before publishing the final results directory."""
    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Refusing overwrite: {OUTPUT_DIR}"
        )

    OUTPUT_DIR.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    manifest = {
        "task": "SCRUM-76",
        "status": "completed",
        "created_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_task": "SCRUM-75",
        "source_manifest_sha256": source[
            "manifest_sha256"
        ],
        "source_csv_sha256": source[
            "source_hashes"
        ],
        "source_settings_sha256": source[
            "settings_sha256"
        ],
        "bootstrap_method": (
            "patient-cluster percentile; "
            "shared samples across all runs"
        ),
        "bootstrap_replicates": BOOTSTRAP_REPLICATES,
        "bootstrap_random_seed": BOOTSTRAP_RANDOM_SEED,
        "bootstrap_max_attempts": MAX_BOOTSTRAP_ATTEMPTS,
        "bootstrap_actual_attempts": attempts,
        "test_eyes": EXPECTED_TEST_EYES,
        "test_patients": EXPECTED_TEST_PATIENTS,
        "per_seed_rows": len(results),
        "summary_rows": len(summary),
        "methodology_status": (
            "Draft; internal Task 13 approval required"
        ),
    }

    with tempfile.TemporaryDirectory(
        prefix=".internal_auc_ci_",
        dir=OUTPUT_DIR.parent,
    ) as temporary:
        staging = Path(temporary) / "complete"
        staging.mkdir()

        write_csv(
            staging / "per_seed_auc_ci.csv",
            RESULT_FIELDS,
            results,
        )

        write_csv(
            staging / "seed_summary.csv",
            SUMMARY_FIELDS,
            summary,
        )

        (
            staging / "analysis_manifest.json"
        ).write_text(
            json.dumps(
                manifest,
                indent=2,
                allow_nan=False,
            ) + "\n",
            encoding="utf-8",
        )

        # Confirm source files have not changed during analysis.
        if (
            sha256_file(INPUT_DIR / "run_manifest.json")
            != source["manifest_sha256"]
        ):
            raise RuntimeError(
                "SCRUM-75 manifest changed during analysis"
            )

        for filename, expected_hash in (
            source["source_hashes"].items()
        ):
            if (
                sha256_file(INPUT_DIR / filename)
                != expected_hash
            ):
                raise RuntimeError(
                    f"Source CSV changed: {filename}"
                )

        if OUTPUT_DIR.exists():
            raise FileExistsError(
                f"Output directory already exists: {OUTPUT_DIR}"
            )

        # Same-filesystem directory rename publishes all
        # completed files together. Existing output is never
        # intentionally overwritten.
        staging.rename(OUTPUT_DIR)

    print(
        f"Saved SCRUM-76 analysis to {OUTPUT_DIR}"
    )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__
    )

    actions = parser.add_mutually_exclusive_group(
        required=True
    )

    actions.add_argument(
        "--smoke-test",
        action="store_true",
        help="Run synthetic-only checks",
    )

    actions.add_argument(
        "--run",
        action="store_true",
        help="Analyze real internal-test predictions",
    )

    parser.add_argument(
        "--confirm-internal-test-analysis",
        action="store_true",
        help=(
            "Explicit confirmation required for real analysis; "
            "team approval is also required"
        ),
    )

    args = parser.parse_args()

    if args.smoke_test:
        run_synthetic_smoke_test()
        return

    if not args.confirm_internal_test_analysis:
        parser.error(
            "Real analysis requires "
            "--confirm-internal-test-analysis "
            "and prior team approval"
        )

    if OUTPUT_DIR.exists():
        raise FileExistsError(
            f"Output already exists: {OUTPUT_DIR}"
        )

    source = validate_source_manifest(INPUT_DIR)

    datasets = prepare_data(
        INPUT_DIR,
        source,
    )

    results, summary, attempts = compute_results(
        datasets
    )

    publish_results(
        results,
        summary,
        source,
        attempts,
    )


if __name__ == "__main__":
    main()
