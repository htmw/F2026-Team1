from pathlib import Path
import cv2
import random
import numpy as np

# IMAGE_DIR = Path("Preprocessed Images")
IMAGE_DIR = Path("Preprocessed/ODIR")
OUTPUT = Path("preprocessing_check.jpg")

SAMPLE_SIZE = 20
SEED = 42

extensions = {".jpg", ".jpeg", ".png", ".bmp"}

files = [
    p for p in IMAGE_DIR.iterdir()
    if p.suffix.lower() in extensions
]

random.seed(SEED)
samples = random.sample(files, SAMPLE_SIZE)

tiles = []

for path in samples:
    image = cv2.imread(str(path))

    if image is None:
        continue

    image = cv2.resize(image, (256, 256))

    # Space for filename
    tile = np.zeros((290, 256, 3), dtype=np.uint8)
    tile[:256, :] = image

    cv2.putText(
        tile,
        path.name,
        (5, 278),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )

    tiles.append(tile)

# 5 columns x 4 rows
rows = []

for i in range(0, len(tiles), 5):
    rows.append(np.hstack(tiles[i:i + 5]))

contact_sheet = np.vstack(rows)

cv2.imwrite(str(OUTPUT), contact_sheet)

print("Created:", OUTPUT)
print("\nRandom images checked:")

for path in samples:
    print(path.name)