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
# - calculate weighted BCE loss
# - backpropagate and update model weights
# - run validation
# - calculate validation AUROC
#
# Only a few batches are used so this can be checked locally.
# Internal test, holdout, and external datasets are NOT used.
# ---------------------------------------------------------

from pathlib import Path
import sys

import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader, Subset

# Allow imports from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent))

from glaucoma_model import GlaucomaNet
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

# 5 batches x 8 images = 40 images
SMOKE_IMAGES = 40

LEARNING_RATE = 1e-4


def get_glaucoma_weight():
    labels = pd.read_csv(LABELS_CSV)

    train_labels = labels[
        labels["split"] == "train"
    ]

    positive = int(
        train_labels["glaucoma"].sum()
    )

    negative = len(train_labels) - positive

    if positive == 0:
        raise ValueError(
            "No glaucoma-positive training examples."
        )

    return negative / positive


def main():

    print("TASK 11 - GLAUCOMA SMOKE TEST")
    print("--------------------------------")

    set_seed(SEED)

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)

    # -----------------------------------------------------
    # Full datasets still read the existing Task 7 split.
    # Subset only limits how many rows this smoke test runs.
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
    # Small training subset: first 40 training images
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
    # Small validation subset containing both classes.
    #
    # This is ONLY for the smoke test so that AUROC can be
    # verified. Real Task 11 training still evaluates the
    # complete natural validation split of 1,024 images.
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
    # Same glaucoma weighting used by real training
    # -----------------------------------------------------

    glaucoma_weight = get_glaucoma_weight()

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
    # Same model and optimizer as Task 11.
    #
    # pretrained=False is used only for this local smoke
    # test. Real Task 11 training uses pretrained=True.
    # -----------------------------------------------------

    model = GlaucomaNet(
        pretrained=False
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
    )

    # -----------------------------------------------------
    # Small training pass
    # -----------------------------------------------------

    model.train()

    train_batches = 0

    for batch in train_loader:

        images = batch["image"].to(device)

        targets = (
            batch["glaucoma"]
            .to(device)
            .unsqueeze(1)
        )

        optimizer.zero_grad()

        logits = model(images)

        loss = loss_fn(
            logits,
            targets,
        )

        loss.backward()
        optimizer.step()

        train_batches += 1

        print(
            f"Training batch {train_batches} "
            f"loss: {loss.item():.4f}"
        )

    # -----------------------------------------------------
    # Small validation pass
    # -----------------------------------------------------

    model.eval()

    validation_batches = 0
    all_targets = []
    all_probabilities = []

    with torch.no_grad():

        for batch in validation_loader:

            images = batch["image"].to(device)

            targets = (
                batch["glaucoma"]
                .to(device)
                .unsqueeze(1)
            )

            logits = model(images)

            probabilities = torch.sigmoid(logits)

            all_targets.extend(
                targets
                .squeeze(1)
                .cpu()
                .numpy()
                .tolist()
            )

            all_probabilities.extend(
                probabilities
                .squeeze(1)
                .cpu()
                .numpy()
                .tolist()
            )

            validation_batches += 1

    # -----------------------------------------------------
    # AUROC
    # -----------------------------------------------------

    unique_targets = set(all_targets)

    if len(unique_targets) != 2:
        raise RuntimeError(
            "Smoke validation subset does not "
            "contain both glaucoma classes."
        )

    validation_auroc = roc_auc_score(
        all_targets,
        all_probabilities,
    )

    print(
        f"Smoke validation AUROC: "
        f"{validation_auroc:.4f}"
    )

    # -----------------------------------------------------
    # Final checks
    # -----------------------------------------------------

    print("--------------------------------")

    print(
        "Training batches:",
        train_batches,
    )

    print(
        "Validation batches:",
        validation_batches,
    )

    assert train_batches == 5
    assert validation_batches == 5

    print(
        "Glaucoma Task 11 smoke test passed."
    )


if __name__ == "__main__":
    main()