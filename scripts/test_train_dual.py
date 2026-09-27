from pathlib import Path

import pandas as pd
import torch
import torch.nn as nn
from torch.utils.data import DataLoader

from dual_model import DualNet
from fundus_dataset import (
    FundusDataset,
    get_train_transform,
    get_validation_transform,
)

from dual.config import set_seed


# ---------------------------------------------------------
# Task 10 Smoke Test Settings
# ---------------------------------------------------------

set_seed()

LABELS_CSV = Path("labels/eye_labels_task7.csv")
IMAGE_DIR = Path("Preprocessed/ODIR")

BATCH_SIZE = 8
LEARNING_RATE = 1e-4

# Training uses shuffle=True.
# Therefore, we only choose HOW MANY training batches
# we want to test.
#
# 5 batches x 8 images = 40 randomly shuffled
# training images.
TRAIN_BATCHES_TO_TEST = 5


# ---------------------------------------------------------
# Validation Batch Selection
# ---------------------------------------------------------
#
# Validation uses shuffle=False, so the batch numbers
# stay in a fixed order.
#
# Examples with BATCH_SIZE = 8:
#
# START_BATCH = 1, END_BATCH = 5
# -> batches 1-5
# -> validation images 1-40
#
# START_BATCH = 6, END_BATCH = 10
# -> batches 6-10
# -> validation images 41-80
#
# START_BATCH = 11, END_BATCH = 15
# -> batches 11-15
# -> validation images 81-120
#
# START_BATCH = 1, END_BATCH = 10
# -> batches 1-10
# -> validation images 1-80
#
# Change START_BATCH and END_BATCH below to select
# the validation batch range you want to test.
# ---------------------------------------------------------

START_BATCH = 6
END_BATCH = 10


# ---------------------------------------------------------
# Calculate class weights from TRAIN split only
# ---------------------------------------------------------

def calculate_positive_weights(labels_csv):
    labels = pd.read_csv(labels_csv)

    train_labels = labels[
        labels["split"] == "train"
    ].copy()

    if len(train_labels) == 0:
        raise ValueError(
            "No training rows found."
        )

    cataract_positive = int(
        train_labels["cataract"].sum()
    )

    glaucoma_positive = int(
        train_labels["glaucoma"].sum()
    )

    cataract_negative = (
        len(train_labels) - cataract_positive
    )

    glaucoma_negative = (
        len(train_labels) - glaucoma_positive
    )

    if cataract_positive == 0:
        raise ValueError(
            "No positive cataract examples."
        )

    if glaucoma_positive == 0:
        raise ValueError(
            "No positive glaucoma examples."
        )

    cataract_weight = (
        cataract_negative / cataract_positive
    )

    glaucoma_weight = (
        glaucoma_negative / glaucoma_positive
    )

    return cataract_weight, glaucoma_weight


# ---------------------------------------------------------
# Smoke-test TRAINING batches
# ---------------------------------------------------------

def test_training(
    model,
    loader,
    optimizer,
    cataract_loss_fn,
    glaucoma_loss_fn,
    device,
):
    model.train()

    print()
    print("Testing TRAINING pipeline...")

    batches_tested = 0
    images_tested = 0

    for batch_number, batch in enumerate(
        loader,
        start=1,
    ):
        images = batch["image"].to(device)

        cataract_targets = (
            batch["cataract"]
            .to(device)
            .unsqueeze(1)
        )

        glaucoma_targets = (
            batch["glaucoma"]
            .to(device)
            .unsqueeze(1)
        )

        optimizer.zero_grad()

        cataract_logits, glaucoma_logits = model(
            images
        )

        cataract_loss = cataract_loss_fn(
            cataract_logits,
            cataract_targets,
        )

        glaucoma_loss = glaucoma_loss_fn(
            glaucoma_logits,
            glaucoma_targets,
        )

        loss = cataract_loss + glaucoma_loss

        # Actual training step
        loss.backward()
        optimizer.step()

        batches_tested += 1
        images_tested += len(images)

        print(
            f"Training batch "
            f"{batch_number}/{TRAIN_BATCHES_TO_TEST} "
            f"| Images: {len(images)} "
            f"| Loss: {loss.item():.4f} "
            f"| PASS"
        )

        # Stop after selected number of training batches
        if batch_number >= TRAIN_BATCHES_TO_TEST:
            break

    if batches_tested == 0:
        raise RuntimeError(
            "No training batches were tested."
        )

    print(
        f"Training smoke test: PASS "
        f"| Batches tested: {batches_tested} "
        f"| Images tested: {images_tested}"
    )

    return batches_tested, images_tested


# ---------------------------------------------------------
# Smoke-test VALIDATION batches
# ---------------------------------------------------------

def test_validation(
    model,
    loader,
    cataract_loss_fn,
    glaucoma_loss_fn,
    device,
):
    model.eval()

    print()
    print("Testing VALIDATION pipeline...")

    batches_tested = 0
    images_tested = 0

    with torch.no_grad():

        for batch_number, batch in enumerate(
            loader,
            start=1,
        ):

            # Skip validation batches before START_BATCH
            if batch_number < START_BATCH:
                continue

            images = batch["image"].to(device)

            cataract_targets = (
                batch["cataract"]
                .to(device)
                .unsqueeze(1)
            )

            glaucoma_targets = (
                batch["glaucoma"]
                .to(device)
                .unsqueeze(1)
            )

            cataract_logits, glaucoma_logits = model(
                images
            )

            cataract_loss = cataract_loss_fn(
                cataract_logits,
                cataract_targets,
            )

            glaucoma_loss = glaucoma_loss_fn(
                glaucoma_logits,
                glaucoma_targets,
            )

            loss = cataract_loss + glaucoma_loss

            batches_tested += 1
            images_tested += len(images)

            print(
                f"Validation batch "
                f"{batch_number}/{END_BATCH} "
                f"| Images: {len(images)} "
                f"| Loss: {loss.item():.4f} "
                f"| PASS"
            )

            # Stop after END_BATCH
            if batch_number >= END_BATCH:
                break

    if batches_tested == 0:
        raise RuntimeError(
            "No validation batches were tested. "
            "Check START_BATCH and END_BATCH."
        )

    print(
        f"Validation smoke test: PASS "
        f"| Batches tested: {batches_tested} "
        f"| Images tested: {images_tested}"
    )

    return batches_tested, images_tested


# ---------------------------------------------------------
# Main Task 10 Smoke Test
# ---------------------------------------------------------

def main():

    print("DUAL Task 10 Smoke Test")
    print("--------------------------------")

    if not LABELS_CSV.exists():
        raise FileNotFoundError(
            f"Label file not found: {LABELS_CSV}"
        )

    if not IMAGE_DIR.exists():
        raise FileNotFoundError(
            f"Image directory not found: {IMAGE_DIR}"
        )

    # Check smoke-test settings
    if TRAIN_BATCHES_TO_TEST < 1:
        raise ValueError(
            "TRAIN_BATCHES_TO_TEST must be at least 1."
        )

    if START_BATCH < 1:
        raise ValueError(
            "START_BATCH must be at least 1."
        )

    if END_BATCH < START_BATCH:
        raise ValueError(
            "END_BATCH must be greater than or equal "
            "to START_BATCH."
        )

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)
    print("Label file:", LABELS_CSV)
    print("Image directory:", IMAGE_DIR)
    print("Batch size:", BATCH_SIZE)

    print(
        "Training batches to test:",
        TRAIN_BATCHES_TO_TEST,
    )

    print(
        "Validation batch range:",
        f"{START_BATCH}-{END_BATCH}",
    )

    # -----------------------------------------------------
    # Real ODIR train + validation datasets
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
        "Training images available:",
        len(train_dataset),
    )

    print(
        "Validation images available:",
        len(validation_dataset),
    )

    # -----------------------------------------------------
    # DataLoaders
    # -----------------------------------------------------

    # Training is shuffled.
    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
    )

    # Validation is NOT shuffled.
    # This keeps validation batch numbers fixed.
    validation_loader = DataLoader(
        validation_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    # -----------------------------------------------------
    # Class imbalance
    # -----------------------------------------------------

    cataract_weight, glaucoma_weight = (
        calculate_positive_weights(LABELS_CSV)
    )

    print(
        f"Cataract positive weight: "
        f"{cataract_weight:.4f}"
    )

    print(
        f"Glaucoma positive weight: "
        f"{glaucoma_weight:.4f}"
    )

    cataract_pos_weight = torch.tensor(
        [cataract_weight],
        dtype=torch.float32,
        device=device,
    )

    glaucoma_pos_weight = torch.tensor(
        [glaucoma_weight],
        dtype=torch.float32,
        device=device,
    )

    cataract_loss_fn = nn.BCEWithLogitsLoss(
        pos_weight=cataract_pos_weight
    )

    glaucoma_loss_fn = nn.BCEWithLogitsLoss(
        pos_weight=glaucoma_pos_weight
    )

    # -----------------------------------------------------
    # Shared pretrained ResNet-50 + two heads
    # -----------------------------------------------------

    model = DualNet(
        pretrained=True
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
    )

    # -----------------------------------------------------
    # Run training smoke test
    # -----------------------------------------------------

    training_batches, training_images = (
        test_training(
            model=model,
            loader=train_loader,
            optimizer=optimizer,
            cataract_loss_fn=cataract_loss_fn,
            glaucoma_loss_fn=glaucoma_loss_fn,
            device=device,
        )
    )

    # -----------------------------------------------------
    # Run validation smoke test
    # -----------------------------------------------------

    validation_batches, validation_images = (
        test_validation(
            model=model,
            loader=validation_loader,
            cataract_loss_fn=cataract_loss_fn,
            glaucoma_loss_fn=glaucoma_loss_fn,
            device=device,
        )
    )

    # -----------------------------------------------------
    # Final result
    # -----------------------------------------------------

    print()
    print("--------------------------------")
    print("TASK 10 SMOKE TEST PASSED")

    print(
        f"Training: {training_batches} batches, "
        f"{training_images} images."
    )

    print(
        f"Validation: {validation_batches} batches, "
        f"{validation_images} images."
    )

    print(
        "NOTE: This verifies the Task 10 training "
        "pipeline. It is not a full model training run."
    )


if __name__ == "__main__":
    main()