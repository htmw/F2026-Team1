"""Build test-only label files for the four external datasets."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_DIR = PROJECT_ROOT / "data" / "External"
OUTPUT_DIR = PROJECT_ROOT / "labels" / "external"

import csv 

# ORIGA: build test-only labels from folder names

ORIGA_LABELS = EXTERNAL_DIR / "ORIGA" / "glaucoma.csv"

with ORIGA_LABELS.open(newline="" , encoding="utf-8-sig") as file:
    rows = list(csv.DictReader(file))

print (f"ORIGA rows: {len(rows)}")
print ("First row:" , rows[0])    

glaucoma_count = sum(int(row["Glaucoma"]) for row in rows )
print (f"Glaucoma cases: {glaucoma_count}")


# Stop if the counts don't match the expected dataset.
if len(rows) != 650 or glaucoma_count != 168:
    raise ValueError("Unexpected ORIGA counts")

OUTPUT_DIR.mkdir(parents = True, exist_ok = True)
output_file = OUTPUT_DIR / "origa_labels.csv"

with output_file.open("w", newline="", encoding= "utf-8") as file:
    writer = csv.DictWriter(file, fieldnames = ["filename", "glaucoma", "split"],)

    writer.writeheader()

    for row in rows:
        writer.writerow({"filename": row["Filename"], "glaucoma": int(row["Glaucoma"]), "split": "test",})

print(f"Saved: {output_file}")    


# DRISHTI-GS: build test-only labels from folder names

DRISHTI_DIR = EXTERNAL_DIR / "DRISHTI-GS"
drishti_rows = []

for path in sorted(DRISHTI_DIR.rglob("*.png")):
    if path.parent.parent.name.lower() != "images":
        continue

    folder_label = path.parent.name.lower()

    if folder_label not in {"glaucoma", "normal"}:
        raise ValueError(f"Unexpected folder: {path.parent}")

    drishti_rows.append({
        "filename": path.name,
        "glaucoma": int(folder_label == "glaucoma"),
        "split": "test",
    })

print(f"DRISHTI images: {len(drishti_rows)}")
print(
    "DRISHTI glaucoma cases:",
    sum(row["glaucoma"] for row in drishti_rows),
)

# ********** Check DRISHTI-GS folder labels against the spreadsheet *********

from openpyxl import load_workbook

spreadsheet = next(
    DRISHTI_DIR.rglob("Notching___Image__level_decisions.xlsx")
)
workbook = load_workbook(spreadsheet, read_only=True, data_only=True)
sheet = workbook["Sheet1"]

reference_labels = {}

for image_id, _, _, diagnosis in sheet.iter_rows(
    min_row=2, max_col=4, values_only=True
):
    if diagnosis in {"G", "N"}:
        reference_labels[int(image_id)] = int(diagnosis == "G")

workbook.close()

for row in drishti_rows:
    image_id = int(Path(row["filename"]).stem.split("_")[-1])

    if image_id not in reference_labels:
        raise ValueError(f"Missing spreadsheet label: {row['filename']}")

    if row["glaucoma"] != reference_labels[image_id]:
        raise ValueError(f"Label mismatch: {row['filename']}")

print(f"Spreadsheet check passed for {len(drishti_rows)} images.")