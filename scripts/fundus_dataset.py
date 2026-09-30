from pathlib import Path

import pandas as pd
import torch
from PIL import Image
from torch.utils.data import Dataset
from torchvision import transforms


# ImageNet normalization because the shared ResNet-50
# uses ImageNet pretrained weights.
IMAGENET_MEAN = [0.485, 0.456, 0.406]
IMAGENET_STD = [0.229, 0.224, 0.225]


def get_train_transform():
    """
    Transform used only for the training split.
    Includes image augmentation required by Task 10.
    """
    return transforms.Compose([
        transforms.RandomHorizontalFlip(p=0.5),
        transforms.RandomRotation(degrees=10),
        transforms.ToTensor(),
        transforms.Normalize(
            mean=IMAGENET_MEAN,
            std=IMAGENET_STD
        ),
    ])


def get_validation_transform():
    """
    Validation images are not randomly augmented.
    """
    return transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize(
            mean=IMAGENET_MEAN,
            std=IMAGENET_STD
        ),
    ])


class FundusDataset(Dataset):
    """
    Loads ODIR fundus images and labels through
    the project label CSV.

    The dataset never reads labels from data.xlsx
    or from diagnosis_text.
    """

    def __init__(
        self,
        labels_csv,
        image_dir,
        split,
        transform=None
    ):
        self.labels_csv = Path(labels_csv)
        self.image_dir = Path(image_dir)
        self.split = split
        self.transform = transform

        labels = pd.read_csv(self.labels_csv)

        required_columns = {
            "filename",
            "cataract",
            "glaucoma",
            "split"
        }

        missing = required_columns - set(labels.columns)

        if missing:
            raise ValueError(
                f"Missing required label columns: {sorted(missing)}"
            )

        # Use only the requested split.
        self.labels = labels[
            labels["split"] == split
        ].reset_index(drop=True)

        if len(self.labels) == 0:
            raise ValueError(
                f"No rows found for split '{split}'."
            )

    def __len__(self):
        return len(self.labels)

    def __getitem__(self, index):
        row = self.labels.iloc[index]

        image_path = self.image_dir / row["filename"]

        if not image_path.exists():
            raise FileNotFoundError(
                f"Image not found: {image_path}"
            )

        image = Image.open(image_path).convert("RGB")

        if self.transform is not None:
            image = self.transform(image)

        cataract = torch.tensor(
            float(row["cataract"]),
            dtype=torch.float32
        )

        glaucoma = torch.tensor(
            float(row["glaucoma"]),
            dtype=torch.float32
        )

        return {
            "image": image,
            "cataract": cataract,
            "glaucoma": glaucoma,
            "filename": row["filename"]
        }