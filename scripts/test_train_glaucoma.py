# ---------------------------------------------------------
# TASK 11 - GLAUCOMA-ONLY TRAINING SMOKE TEST
# ---------------------------------------------------------
#
# This is NOT full Task 11 training.
#
# It checks that the glaucoma-only pipeline can:
# - read the existing Task 7 train/validation splits
# - load preprocessed ODIR images
# - run the glaucoma-only model
# - use the real Task 11 train_one_epoch function
# - calculate weighted BCE loss
# - backpropagate and update model weights
# - use the real Task 11 validate function
# - calculate validation loss and AUROC
#
# Only a small subset is used so this can be checked locally.
# Internal test, holdout, and external datasets are NOT used.
# ---------------------------------------------------------

from pathlib import Path
import sys

import torch
import torch.nn as nn
from torch.utils.data import DataLoader, Subset

# Allow imports from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from glaucoma_model import GlaucomaNet
from train_glaucoma import (
    calculate_glaucoma_weight,
    train_one_epoch,
    validate,
)
from fundus_dataset import (
    FundusDataset,
    get_train_transform,
    get_validation_transform,
)

from dual.config import set_seed


LABELS_CSV = Path("labels/eye_labels_task7.csv")
IMAGE_DIR = Path("Preprocessed/ODIR")

SEED = 42
BATCH_SIZE = 8
SMOKE_IMAGES = 40
LEARNING_RATE = 1e-4


def main():

    print("TASK 11 - GLAUCOMA SMOKE TEST")
    print("--------------------------------")

    set_seed(SEED)

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)

    # -----------------------------------------------------
    # Read the existing Task 7 train and validation splits
    # -----------------------------------------------------

    train_dataset = FundusDataset(
        labels_csv=LABELS_CSV,
        image_dir=IMAGE_DIR,
        split="train",
        transform=get_train_transform(),
    )

    validation_dataset = FundusDataset(
        labels_csv=LABELS_CSV,
        image_dir=IMAGE_DIR,
        split="validation",
        transform=get_validation_transform(),
    )

    print(
        "Full training split:",
        len(train_dataset),
    )

    print(
        "Full validation split:",
        len(validation_dataset),
    )

    # -----------------------------------------------------
    # Small training subset
    # -----------------------------------------------------

    train_subset = Subset(
        train_dataset,
        range(
            min(
                SMOKE_IMAGES,
                len(train_dataset),
            )
        ),
    )

    # -----------------------------------------------------
    # Small validation subset containing both classes
    #
    # This is only for the smoke test so AUROC can be
    # calculated. Real Task 11 training evaluates the
    # complete validation split.
    # -----------------------------------------------------

    positive_indices = []
    negative_indices = []

    for index in range(len(validation_dataset)):

        sample = validation_dataset[index]

        glaucoma_label = int(
            sample["glaucoma"].item()
        )

        if glaucoma_label == 1:
            positive_indices.append(index)
        else:
            negative_indices.append(index)

        if (
            len(positive_indices) >= 20
            and len(negative_indices) >= 20
        ):
            break

    if (
        len(positive_indices) < 20
        or len(negative_indices) < 20
    ):
        raise RuntimeError(
            "Could not create smoke validation subset "
            "with both glaucoma classes."
        )

    validation_indices = (
        positive_indices[:20]
        + negative_indices[:20]
    )

    validation_subset = Subset(
        validation_dataset,
        validation_indices,
    )

    print(
        "Smoke validation positives:",
        20,
    )

    print(
        "Smoke validation negatives:",
        20,
    )

    # -----------------------------------------------------
    # DataLoaders
    # -----------------------------------------------------

    train_loader = DataLoader(
        train_subset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    validation_loader = DataLoader(
        validation_subset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    # -----------------------------------------------------
    # Use the same class-weight calculation as real training
    # -----------------------------------------------------

    glaucoma_weight = calculate_glaucoma_weight(
        LABELS_CSV
    )

    print(
        f"Glaucoma positive weight: "
        f"{glaucoma_weight:.4f}"
    )

    pos_weight = torch.tensor(
        [glaucoma_weight],
        dtype=torch.float32,
        device=device,
    )

    loss_fn = nn.BCEWithLogitsLoss(
        pos_weight=pos_weight
    )

    # -----------------------------------------------------
    # Model and optimizer
    #
    # pretrained=False avoids downloading ImageNet weights
    # during the local smoke test. Real Task 11 training
    # uses pretrained=True.
    # -----------------------------------------------------

    model = GlaucomaNet(
        pretrained=False
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
    )

    # -----------------------------------------------------
    # Call the ACTUAL Task 11 training function
    # -----------------------------------------------------

    train_loss = train_one_epoch(
        model=model,
        loader=train_loader,
        optimizer=optimizer,
        loss_fn=loss_fn,
        device=device,
    )

    print(
        f"Smoke training loss: "
        f"{train_loss:.4f}"
    )

    # -----------------------------------------------------
    # Call the ACTUAL Task 11 validation function
    # -----------------------------------------------------

    validation_loss, validation_auroc = validate(
        model=model,
        loader=validation_loader,
        loss_fn=loss_fn,
        device=device,
    )

    print(
        f"Smoke validation loss: "
        f"{validation_loss:.4f}"
    )

    print(
        f"Smoke validation AUROC: "
        f"{validation_auroc:.4f}"
    )

    # -----------------------------------------------------
    # Final checks
    # -----------------------------------------------------

    expected_train_batches = (
        len(train_loader)
    )

    expected_validation_batches = (
        len(validation_loader)
    )

    print("--------------------------------")

    print(
        "Training batches:",
        expected_train_batches,
    )

    print(
        "Validation batches:",
        expected_validation_batches,
    )

    assert expected_train_batches == 5
    assert expected_validation_batches == 5

    assert train_loss >= 0
    assert validation_loss >= 0
    assert 0.0 <= validation_auroc <= 1.0

    print(
        "Glaucoma Task 11 smoke test passed."
    )


if __name__ == "__main__":
    main()