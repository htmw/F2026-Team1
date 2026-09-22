import pandas as pd
import numpy as np
from pathlib import Path

from dual.config import SEED


# ---------------------------------------------------------
# File paths
# ---------------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent.parent

INPUT = BASE_DIR / "labels" / "eye_labels_task6.csv"
OUTPUT = BASE_DIR / "labels" / "eye_labels_task7.csv"


def main():

    # ---------------------------------------------------------
    # Load Task 6 labels
    # ---------------------------------------------------------

    labels = pd.read_csv(INPUT)

    # Start with a clean split column
    labels["split"] = ""


    # ---------------------------------------------------------
    # Low-quality eyes -> holdout
    # ---------------------------------------------------------

    low_quality_mask = labels["diagnosis_text"].str.lower().str.contains(
        "low image quality",
        na=False
    )

    labels.loc[
        low_quality_mask,
        "split"
    ] = "holdout"


    # ---------------------------------------------------------
    # Suspected glaucoma -> holdout
    # ---------------------------------------------------------

    labels.loc[
        (labels["suspected_glaucoma"] == 1) &
        (labels["split"] == ""),
        "split"
    ] = "holdout"


    # ---------------------------------------------------------
    # Media opacity -> holdout
    # ---------------------------------------------------------

    labels.loc[
        (labels["media_opacity"] == 1) &
        (labels["split"] == ""),
        "split"
    ] = "holdout"


    # ---------------------------------------------------------
    # Remaining unusable images -> excluded
    # ---------------------------------------------------------

    labels.loc[
        (labels["exclusion"] == 1) &
        (labels["split"] == ""),
        "split"
    ] = "excluded"


    # ---------------------------------------------------------
    # Find patients eligible for train/validation/test
    # ---------------------------------------------------------

    eligible = labels[
        labels["split"] == ""
    ].copy()

    patient_summary = (
        eligible.groupby("patient_id")
        .agg(
            cataract=("cataract", "max"),
            glaucoma=("glaucoma", "max")
        )
        .reset_index()
    )


    # ---------------------------------------------------------
    # Find the patient who has both diseases
    # ---------------------------------------------------------

    dual_patients = patient_summary[
        (patient_summary["cataract"] == 1) &
        (patient_summary["glaucoma"] == 1)
    ]["patient_id"].tolist()

    if len(dual_patients) != 1:
        raise ValueError(
            f"Expected exactly 1 dual-disease patient, "
            f"but found {len(dual_patients)}: {dual_patients}"
        )

    dual_patient = dual_patients[0]

    print("Dual-disease patient:", dual_patient)
    print("Forcing this patient into training.")


    # ---------------------------------------------------------
    # Force dual-disease patient into train
    # ---------------------------------------------------------

    labels.loc[
        (labels["patient_id"] == dual_patient) &
        (labels["split"] == ""),
        "split"
    ] = "train"


    # Remove that patient before normal random splitting
    patient_summary = patient_summary[
        patient_summary["patient_id"] != dual_patient
    ].copy()


    # ---------------------------------------------------------
    # Create disease stratification groups
    #
    # 0 = neither
    # 1 = cataract
    # 2 = glaucoma
    # ---------------------------------------------------------

    patient_summary["stratum"] = (
        patient_summary["cataract"]
        + 2 * patient_summary["glaucoma"]
    )


    # ---------------------------------------------------------
    # Patient-level 70 / 15 / 15 split
    # ---------------------------------------------------------

    rng = np.random.default_rng(SEED)

    train_patients = []
    validation_patients = []
    test_patients = []

    for _, group in patient_summary.groupby("stratum"):

        ids = group["patient_id"].to_numpy().copy()

        rng.shuffle(ids)

        n = len(ids)

        n_train = round(n * 0.70)
        n_validation = round(n * 0.15)

        train_patients.extend(
            ids[:n_train]
        )

        validation_patients.extend(
            ids[n_train:n_train + n_validation]
        )

        test_patients.extend(
            ids[n_train + n_validation:]
        )


    # ---------------------------------------------------------
    # Assign normal split names
    # ---------------------------------------------------------

    labels.loc[
        (labels["patient_id"].isin(train_patients)) &
        (labels["split"] == ""),
        "split"
    ] = "train"

    labels.loc[
        (labels["patient_id"].isin(validation_patients)) &
        (labels["split"] == ""),
        "split"
    ] = "validation"

    labels.loc[
        (labels["patient_id"].isin(test_patients)) &
        (labels["split"] == ""),
        "split"
    ] = "test"


    # ---------------------------------------------------------
    # Verify every row has a split
    # ---------------------------------------------------------

    unassigned = int(
        (labels["split"] == "").sum()
    )

    if unassigned != 0:
        raise ValueError(
            f"{unassigned} rows were not assigned a split."
        )


    # ---------------------------------------------------------
    # Check patient leakage
    # ---------------------------------------------------------

    normal = labels[
        labels["split"].isin(
            ["train", "validation", "test"]
        )
    ]

    patient_split_counts = (
        normal.groupby("patient_id")["split"]
        .nunique()
    )

    leakage_count = int(
        (patient_split_counts > 1).sum()
    )


    # ---------------------------------------------------------
    # Verify dual-disease patient is in train
    # ---------------------------------------------------------

    dual_in_train = (
        labels.loc[
            labels["patient_id"] == dual_patient,
            "split"
        ] == "train"
    ).all()


    # ---------------------------------------------------------
    # Verify allowed split names
    # ---------------------------------------------------------

    allowed_splits = {
        "train",
        "validation",
        "test",
        "holdout",
        "excluded"
    }

    actual_splits = set(
        labels["split"].unique()
    )

    unexpected_splits = (
        actual_splits - allowed_splits
    )

    if unexpected_splits:
        raise ValueError(
            f"Unexpected split names: {unexpected_splits}"
        )


    # ---------------------------------------------------------
    # Print verification
    # ---------------------------------------------------------

    print("\n----- Task 7 Verification -----")

    print("\nSplit counts:")
    print(labels["split"].value_counts())


    print("\nDisease counts by normal split:")

    for split_name in [
        "train",
        "validation",
        "test"
    ]:

        subset = labels[
            labels["split"] == split_name
        ]

        print(
            f"{split_name}: "
            f"eyes={len(subset)}, "
            f"cataract={int(subset['cataract'].sum())}, "
            f"glaucoma={int(subset['glaucoma'].sum())}"
        )


    # ---------------------------------------------------------
    # Holdout checks
    # ---------------------------------------------------------

    print("\nHoldout checks:")

    low_quality_holdout = labels[
        low_quality_mask &
        (labels["split"] == "holdout")
    ]

    suspected_holdout = labels[
        (labels["suspected_glaucoma"] == 1) &
        (labels["split"] == "holdout")
    ]

    media_holdout = labels[
        (labels["media_opacity"] == 1) &
        (labels["split"] == "holdout")
    ]

    print(
        "Low-quality eyes in holdout:",
        len(low_quality_holdout)
    )

    print(
        "Suspected glaucoma eyes in holdout:",
        len(suspected_holdout)
    )

    print(
        "Media-opacity eyes in holdout:",
        len(media_holdout)
    )


    print("\nPatient leakage:", leakage_count)

    print(
        "Dual-disease patient in train:",
        dual_in_train
    )

    print(
        "Split names:",
        sorted(actual_splits)
    )

    print("--------------------------------")


    # ---------------------------------------------------------
    # Save regenerated Task 7 file
    # ---------------------------------------------------------

    labels.to_csv(
        OUTPUT,
        index=False
    )

    print(f"\nCreated: {OUTPUT}")


if __name__ == "__main__":
    main()