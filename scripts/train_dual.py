
# ---------------------------------------------------------
# TASK 10 - FULL TRAINING PIPELINE
# ---------------------------------------------------------
#
# This is the full Task 10 training code.
#
# It trains the DUAL model using the complete ODIR training
# split (4,807 images) and then validates it using the complete
# ODIR validation split (1,024 images).
#
# The training DataLoader uses shuffle=True, so all 4,807
# training images are processed in shuffled batches.
#
# This script automatically uses CUDA/GPU when available.
# If CUDA is not available, it falls back to CPU; however,
# full training is expected to be much faster on a GPU.
#
# This is different from test_train_dual.py, which only runs
# a small number of batches to verify that the Task 10
# training and validation pipeline works correctly.
#
# ODIR internal test, holdout, and external datasets are NOT
# used in this Task 10 training pipeline.
# ---------------------------------------------------------from pathlib import Path

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
# Project settings
# ---------------------------------------------------------

set_seed()

LABELS_CSV = Path("labels/eye_labels_task7.csv")
IMAGE_DIR = Path("Preprocessed/ODIR")

BATCH_SIZE = 8
EPOCHS = 1
LEARNING_RATE = 1e-4


# ---------------------------------------------------------
# Calculate class weights from TRAIN split only
# ---------------------------------------------------------

def calculate_positive_weights(labels_csv):
    labels = pd.read_csv(labels_csv)

    train_labels = labels[
        labels["split"] == "train"
    ].copy()

    if len(train_labels) == 0:
        raise ValueError("No training rows found in label file.")

    cataract_positive = int(train_labels["cataract"].sum())
    glaucoma_positive = int(train_labels["glaucoma"].sum())

    cataract_negative = len(train_labels) - cataract_positive
    glaucoma_negative = len(train_labels) - glaucoma_positive

    if cataract_positive == 0:
        raise ValueError(
            "No positive cataract examples in training split."
        )

    if glaucoma_positive == 0:
        raise ValueError(
            "No positive glaucoma examples in training split."
        )

    cataract_weight = (
        cataract_negative / cataract_positive
    )

    glaucoma_weight = (
        glaucoma_negative / glaucoma_positive
    )

    return cataract_weight, glaucoma_weight


# ---------------------------------------------------------
# One training epoch
# ---------------------------------------------------------

def train_one_epoch(
    model,
    loader,
    optimizer,
    cataract_loss_fn,
    glaucoma_loss_fn,
    device,
):
    model.train()

    total_loss = 0.0
    batches_processed = 0

    for batch in loader:
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

        cataract_logits, glaucoma_logits = model(images)

        cataract_loss = cataract_loss_fn(
            cataract_logits,
            cataract_targets,
        )

        glaucoma_loss = glaucoma_loss_fn(
            glaucoma_logits,
            glaucoma_targets,
        )

        loss = cataract_loss + glaucoma_loss

        loss.backward()
        optimizer.step()

        total_loss += loss.item()
        batches_processed += 1

    if batches_processed == 0:
        raise RuntimeError(
            "No training batches were processed."
        )

    return total_loss / batches_processed


# ---------------------------------------------------------
# Validation
# ---------------------------------------------------------

def validate(
    model,
    loader,
    cataract_loss_fn,
    glaucoma_loss_fn,
    device,
):
    model.eval()

    total_loss = 0.0
    batches_processed = 0

    with torch.no_grad():

        for batch in loader:
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

            cataract_logits, glaucoma_logits = model(images)

            cataract_loss = cataract_loss_fn(
                cataract_logits,
                cataract_targets,
            )

            glaucoma_loss = glaucoma_loss_fn(
                glaucoma_logits,
                glaucoma_targets,
            )

            loss = cataract_loss + glaucoma_loss

            total_loss += loss.item()
            batches_processed += 1

    if batches_processed == 0:
        raise RuntimeError(
            "No validation batches were processed."
        )

    return total_loss / batches_processed


# ---------------------------------------------------------
# Main Task 10 training pipeline
# ---------------------------------------------------------

def main():

    print("DUAL Task 10 training pipeline")
    print("--------------------------------")

    if not LABELS_CSV.exists():
        raise FileNotFoundError(
            f"Label file not found: {LABELS_CSV}"
        )

    if not IMAGE_DIR.exists():
        raise FileNotFoundError(
            f"ODIR preprocessed image directory not found: "
            f"{IMAGE_DIR}"
        )

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)
    print("Label file:", LABELS_CSV)
    print("Image directory:", IMAGE_DIR)

    # -----------------------------------------------------
    # Dataset
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

    print("Training images:", len(train_dataset))
    print(
        "Validation images:",
        len(validation_dataset),
    )

    # -----------------------------------------------------
    # DataLoaders
    # -----------------------------------------------------

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
    )

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
    # Shared pretrained ResNet + two binary heads
    # -----------------------------------------------------

    model = DualNet(
        pretrained=True
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
    )

    # -----------------------------------------------------
    # Training + validation
    # -----------------------------------------------------

    for epoch in range(EPOCHS):

        train_loss = train_one_epoch(
            model=model,
            loader=train_loader,
            optimizer=optimizer,
            cataract_loss_fn=cataract_loss_fn,
            glaucoma_loss_fn=glaucoma_loss_fn,
            device=device,
        )

        validation_loss = validate(
            model=model,
            loader=validation_loader,
            cataract_loss_fn=cataract_loss_fn,
            glaucoma_loss_fn=glaucoma_loss_fn,
            device=device,
        )

        print(
            f"Epoch {epoch + 1}/{EPOCHS} | "
            f"Train loss: {train_loss:.4f} | "
            f"Validation loss: {validation_loss:.4f}"
        )

    print("--------------------------------")
    print(
        "Task 10 training pipeline "
        "completed successfully."
    )


if __name__ == "__main__":
    main()