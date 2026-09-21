import pandas as pd
import numpy as np
from pathlib import Path

INPUT = Path("eye_labels_task6.csv")
OUTPUT = Path("eye_labels_task7.csv")

SEED = 42


def main():
    df = pd.read_csv(INPUT)

    # Start with no split assigned.
    df["split"] = ""

    # --------------------------------
    # 1. Set aside unusable eyes
    # --------------------------------
    df.loc[df["exclusion"] == 1, "split"] = "excluded"

    # --------------------------------
    # 2. Set aside suspected glaucoma
    # --------------------------------
    df.loc[
        (df["suspected_glaucoma"] == 1) &
        (df["split"] == ""),
        "split"
    ] = "suspected_glaucoma_holdout"

    # --------------------------------
    # 3. Set aside media-opacity eyes
    # --------------------------------
    df.loc[
        (df["media_opacity"] == 1) &
        (df["split"] == ""),
        "split"
    ] = "media_opacity_holdout"

    # --------------------------------
    # 4. Find remaining patients
    # --------------------------------
    available = df[df["split"] == ""].copy()

    patient_summary = (
        available
        .groupby("patient_id")
        .agg(
            cataract=("cataract", "max"),
            glaucoma=("glaucoma", "max")
        )
        .reset_index()
    )

    # --------------------------------
    # 5. Find dual-disease patient
    # --------------------------------
    dual = patient_summary[
        (patient_summary["cataract"] == 1) &
        (patient_summary["glaucoma"] == 1)
    ]

    if len(dual) != 1:
        raise ValueError(
            f"Expected exactly 1 dual-disease patient, found {len(dual)}"
        )

    dual_patient = dual.iloc[0]["patient_id"]

    print("Dual-disease patient:", dual_patient)
    print("Forcing this patient into training.")

    # Remove dual patient before normal splitting.
    patient_summary = patient_summary[
        patient_summary["patient_id"] != dual_patient
    ].copy()

    # --------------------------------
    # 6. Create stratification group
    # --------------------------------
    # 0 = neither
    # 1 = cataract
    # 2 = glaucoma
    patient_summary["stratum"] = (
        patient_summary["cataract"] +
        2 * patient_summary["glaucoma"]
    )

    rng = np.random.default_rng(SEED)

    train_patients = []
    val_patients = []
    test_patients = []

    # --------------------------------
    # 7. Split each disease stratum
    # --------------------------------
    for _, group in patient_summary.groupby("stratum"):

        ids = group["patient_id"].to_numpy()
        rng.shuffle(ids)

        n = len(ids)

        n_train = round(n * 0.70)
        n_val = round(n * 0.15)

        train_patients.extend(ids[:n_train])
        val_patients.extend(
            ids[n_train:n_train + n_val]
        )
        test_patients.extend(
            ids[n_train + n_val:]
        )

    # Force special dual-disease patient into train.
    train_patients.append(dual_patient)

    # --------------------------------
    # 8. Assign splits
    # --------------------------------
    df.loc[
        (df["patient_id"].isin(train_patients)) &
        (df["split"] == ""),
        "split"
    ] = "train"

    df.loc[
        (df["patient_id"].isin(val_patients)) &
        (df["split"] == ""),
        "split"
    ] = "validation"

    df.loc[
        (df["patient_id"].isin(test_patients)) &
        (df["split"] == ""),
        "split"
    ] = "test"

    # --------------------------------
    # 9. Patient leakage check
    # --------------------------------
    normal = df[
        df["split"].isin(
            ["train", "validation", "test"]
        )
    ]

    patient_split_counts = (
        normal.groupby("patient_id")["split"].nunique()
    )

    leakage = patient_split_counts[
        patient_split_counts > 1
    ]

    if len(leakage) > 0:
        raise ValueError(
            "ERROR: Patient leakage detected!"
        )

    # --------------------------------
    # 10. Save
    # --------------------------------
    df.to_csv(OUTPUT, index=False)

    # --------------------------------
    # Verification output
    # --------------------------------
    print("\n----- Task 7 Verification -----")

    print("\nSplit counts:")
    print(df["split"].value_counts())

    print("\nDisease counts:")

    for split in ["train", "validation", "test"]:

        part = df[df["split"] == split]

        print(
            f"{split}: "
            f"eyes={len(part)}, "
            f"cataract={int(part['cataract'].sum())}, "
            f"glaucoma={int(part['glaucoma'].sum())}"
        )

    print("\nPatient leakage:", len(leakage))

    print(
        "Dual-disease patient in train:",
        dual_patient in train_patients
    )

    print("--------------------------------")
    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    main()