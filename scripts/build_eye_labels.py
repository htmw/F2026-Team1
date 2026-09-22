import pandas as pd
import re
from pathlib import Path

# INPUT = Path("data.xlsx")
# OUTPUT = Path("eye_labels_task6.csv")
BASE_DIR = Path(__file__).resolve().parent.parent

INPUT = BASE_DIR / "labels" / "data.xlsx"
OUTPUT = BASE_DIR / "labels" / "eye_labels_task6.csv"


def has_phrase(text, phrase):
    """Case-insensitive whole-phrase matching."""
    text = "" if pd.isna(text) else str(text).lower().strip()

    return re.search(
        r"(?<!\w)" + re.escape(phrase.lower()) + r"(?!\w)",
        text
    ) is not None


def make_eye_row(row, eye):

    side = "Left" if eye == "left" else "Right"

    diagnosis = str(
        row[f"{side}-Diagnostic Keywords"]
    ).strip()

    filename = str(
        row[f"{side}-Fundus"]
    ).strip()

    # -----------------------------
    # Disease labels
    # -----------------------------

    cataract = has_phrase(
        diagnosis,
        "cataract"
    )

    suspected_glaucoma = has_phrase(
        diagnosis,
        "suspected glaucoma"
    )

    # Suspected glaucoma must NOT
    # count as confirmed glaucoma.
    glaucoma = (
        has_phrase(diagnosis, "glaucoma")
        and not suspected_glaucoma
    )

    # -----------------------------
    # Special flags
    # -----------------------------

    media_opacity = has_phrase(
        diagnosis,
        "refractive media opacity"
    )

    # 426 total:
    # 405 lens dust + 21 low image quality
    image_quality_flag = (
        has_phrase(diagnosis, "lens dust")
        or
        has_phrase(diagnosis, "low image quality")
    )

    # -----------------------------
    # Unusable / exclusion
    # -----------------------------

    # 21 low-quality eyes
    low_quality = has_phrase(
        diagnosis,
        "low image quality"
    )

    # Remaining 9 unusable eyes:
    # 5 optic disk photographically invisible
    # 2 anterior segment image
    # 1 image offset
    # 1 no fundus image
    other_unusable = (
        has_phrase(
            diagnosis,
            "optic disk photographically invisible"
        )
        or
        has_phrase(
            diagnosis,
            "anterior segment image"
        )
        or
        has_phrase(
            diagnosis,
            "image offset"
        )
        or
        has_phrase(
            diagnosis,
            "no fundus image"
        )
    )

    exclusion = low_quality or other_unusable

    # Split will be assigned in Task 7.
    split = ""

    return {
        "patient_id": row["ID"],
        "eye": eye,
        "filename": filename,
        "diagnosis_text": diagnosis,
        "cataract": int(cataract),
        "glaucoma": int(glaucoma),
        "suspected_glaucoma": int(suspected_glaucoma),
        "media_opacity": int(media_opacity),
        "image_quality_flag": int(image_quality_flag),
        "exclusion": int(exclusion),
        "split": split
    }


def main():

    # Read original spreadsheet.
    # Never modify data.xlsx.
    df = pd.read_excel(INPUT)

    rows = []

    # One row per eye.
    for _, row in df.iterrows():

        rows.append(
            make_eye_row(row, "left")
        )

        rows.append(
            make_eye_row(row, "right")
        )

    labels = pd.DataFrame(rows)

    labels.to_csv(
        OUTPUT,
        index=False
    )

    # -----------------------------
    # Task 6 verification
    # -----------------------------

    print("----- Task 6 Verification -----")

    print(
        "Rows:",
        len(labels)
    )

    print(
        "Cataract:",
        int(labels["cataract"].sum())
    )

    print(
        "Glaucoma:",
        int(labels["glaucoma"].sum())
    )

    print(
        "Suspected glaucoma:",
        int(labels["suspected_glaucoma"].sum())
    )

    print(
        "Media opacity:",
        int(labels["media_opacity"].sum())
    )

    print(
        "Image quality flags:",
        int(labels["image_quality_flag"].sum())
    )

    print(
        "Excluded:",
        int(labels["exclusion"].sum())
    )

    print("-------------------------------")
    print(f"Created: {OUTPUT}")


if __name__ == "__main__":
    main()