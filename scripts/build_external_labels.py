"""Build test-only label files for the four external datasets."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXTERNAL_DIR = PROJECT_ROOT / "data" / "External"
OUTPUT_DIR = PROJECT_ROOT / "labels" / "external"

import csv 

ORIGA_LABELS = EXTERNAL_DIR / "ORIGA" / "glaucoma.csv"

with ORIGA_LABELS.open(newline="" , encoding="utf-8-sig") as file:
    rows = list(csv.DictReader(file))

print (f"ORIGA rows: {len(rows)}")
print ("First row:" , rows[0])    

glaucoma_count = sum(int(row["Glaucoma"]) for row in rows )
print (f"Glaucoma cases: {glaucoma_count}")