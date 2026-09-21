from pathlib import Path
import cv2
import numpy as np

TARGET_SIZE = 512

DATASETS = {
    "ODIR": Path("Training Images"),
    "ORIGA": Path("External/ORIGA"),
    "DRISHTI-GS": Path("External/DRISHTI-GS"),
    "ACRIMA": Path("External/ACRIMA"),
    "retina_dataset_2016": Path("External/retina_dataset_2016"),
}

OUTPUT_ROOT = Path("Preprocessed")


def crop_fundus(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(gray, (9, 9), 0)

    _, mask = cv2.threshold(
        blurred, 10, 255, cv2.THRESH_BINARY
    )

    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(
        mask, cv2.MORPH_CLOSE, kernel
    )

    contours, _ = cv2.findContours(
        mask,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    if contours:
        largest = max(contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(largest)

        image_area = image.shape[0] * image.shape[1]
        detected_area = w * h

        if detected_area >= image_area * 0.20:
            cx = x + w // 2
            cy = y + h // 2

            # Do not request a square larger than the image itself.
            side = min(
                max(w, h),
                image.shape[0],
                image.shape[1]
            )

            half = side // 2

            x1 = max(0, cx - half)
            y1 = max(0, cy - half)

            x1 = min(x1, image.shape[1] - side)
            y1 = min(y1, image.shape[0] - side)

            crop = image[
                y1:y1 + side,
                x1:x1 + side
            ]

            if crop.size > 0:
                return crop

    # Fallback: largest centered square.
    height, width = image.shape[:2]
    side = min(height, width)

    x1 = (width - side) // 2
    y1 = (height - side) // 2

    return image[
        y1:y1 + side,
        x1:x1 + side
    ]


def preprocess_image(input_path, output_path):
    image = cv2.imread(str(input_path))

    if image is None:
        return False

    cropped = crop_fundus(image)

    resized = cv2.resize(
        cropped,
        (TARGET_SIZE, TARGET_SIZE),
        interpolation=cv2.INTER_AREA
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    return cv2.imwrite(
        str(output_path),
        resized
    )


def get_images(folder):
    extensions = {
        ".jpg", ".jpeg", ".png", ".bmp",
        ".tif", ".tiff"
    }

    # rglob handles datasets that contain
    # images inside subfolders.
    return sorted([
        p for p in folder.rglob("*")
        if p.is_file()
        and p.suffix.lower() in extensions
    ])


def process_dataset(name, input_dir):
    print(f"\n===== {name} =====")

    if not input_dir.exists():
        print("ERROR: Folder not found:", input_dir)
        return

    files = get_images(input_dir)

    print("Images found:", len(files))

    output_dir = OUTPUT_ROOT / name

    processed = 0
    failed = []

    for index, input_path in enumerate(files, start=1):

        # Preserve subfolder structure if one exists.
        relative_path = input_path.relative_to(input_dir)
        output_path = output_dir / relative_path

        if preprocess_image(
            input_path,
            output_path
        ):
            processed += 1
        else:
            failed.append(str(relative_path))

        if index % 100 == 0:
            print(
                f"Processed {index}/{len(files)}"
            )

    print("\nVerification:")
    print("Found:", len(files))
    print("Processed:", processed)
    print("Failed:", len(failed))

    if failed:
        print("Failed files:")
        for file in failed:
            print(" -", file)


def main():
    OUTPUT_ROOT.mkdir(
        parents=True,
        exist_ok=True
    )

    for name, folder in DATASETS.items():
        process_dataset(name, folder)

    print("\n===== TASK 8 COMPLETE =====")
    print("All preprocessing runs finished.")


if __name__ == "__main__":
    main()