# ---------------------------------------------------------
# TASK 11 - GLAUCOMA-ONLY ABLATION TRAINING
# ---------------------------------------------------------
#
# Trains the glaucoma-only ablation model using three
# training seeds: 42, 43, and 44.
#
# IMPORTANT:
# - Uses the existing Task 7 split from eye_labels_task7.csv.
# - Does NOT create a new train/validation split.
# - Training split is used to learn model weights.
# - Validation split is used for AUROC and early stopping.
# - Internal test, holdout, and external datasets are NOT used.
#
# Agreed Task 11 settings:
# - Seeds: 42, 43, 44
# - Maximum epochs: 30
# - Early stopping patience: 5 epochs
# - Selection metric: validation glaucoma AUROC
# - Learning rate: 1e-4
# - Batch size: 8
# - Best checkpoint is saved, not simply the final epoch.
# ---------------------------------------------------------

from pathlib import Path
import csv

import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader

from glaucoma_model import GlaucomaNet
from fundus_dataset import (
    FundusDataset,
    get_train_transform,
    get_validation_transform,
)

from dual.config import set_seed


# ---------------------------------------------------------
# Task 11 settings
# ---------------------------------------------------------

LABELS_CSV = Path("labels/eye_labels_task7.csv")
IMAGE_DIR = Path("Preprocessed/ODIR")

CHECKPOINT_DIR = Path("checkpoints/task11/glaucoma")
RESULTS_CSV = Path("checkpoints/task11/glaucoma_results.csv")

SEEDS = [42, 43, 44]

BATCH_SIZE = 8
MAX_EPOCHS = 30
LEARNING_RATE = 1e-4
PATIENCE = 5


# ---------------------------------------------------------
# Calculate glaucoma class weight from TRAIN split only
# ---------------------------------------------------------

def calculate_glaucoma_weight(labels_csv):
    labels = pd.read_csv(labels_csv)

    train_labels = labels[
        labels["split"] == "train"
    ].copy()

    if len(train_labels) == 0:
        raise ValueError(
            "No training rows found in label file."
        )

    glaucoma_positive = int(
        train_labels["glaucoma"].sum()
    )

    glaucoma_negative = (
        len(train_labels) - glaucoma_positive
    )

    if glaucoma_positive == 0:
        raise ValueError(
            "No positive glaucoma examples "
            "in training split."
        )

    return glaucoma_negative / glaucoma_positive


# ---------------------------------------------------------
# Train one epoch
# ---------------------------------------------------------

def train_one_epoch(
    model,
    loader,
    optimizer,
    loss_fn,
    device,
):
    model.train()

    total_loss = 0.0
    batches_processed = 0

    for batch in loader:
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

        total_loss += loss.item()
        batches_processed += 1

    if batches_processed == 0:
        raise RuntimeError(
            "No training batches were processed."
        )

    return total_loss / batches_processed


# ---------------------------------------------------------
# Validate and calculate glaucoma AUROC
# ---------------------------------------------------------

def validate(
    model,
    loader,
    loss_fn,
    device,
):
    model.eval()

    total_loss = 0.0
    batches_processed = 0

    all_targets = []
    all_probabilities = []

    with torch.no_grad():

        for batch in loader:
            images = batch["image"].to(device)

            targets = (
                batch["glaucoma"]
                .to(device)
                .unsqueeze(1)
            )

            logits = model(images)

            loss = loss_fn(
                logits,
                targets,
            )

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

            total_loss += loss.item()
            batches_processed += 1

    if batches_processed == 0:
        raise RuntimeError(
            "No validation batches were processed."
        )

    validation_loss = (
        total_loss / batches_processed
    )

    validation_auroc = roc_auc_score(
        all_targets,
        all_probabilities,
    )

    return validation_loss, validation_auroc


# ---------------------------------------------------------
# Save summary of each completed run
# ---------------------------------------------------------

def save_result(
    seed,
    best_epoch,
    best_auroc,
    checkpoint_path,
):
    RESULTS_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    file_exists = RESULTS_CSV.exists()

    with RESULTS_CSV.open(
        "a",
        newline="",
        encoding="utf-8",
    ) as file:

        writer = csv.writer(file)

        if not file_exists:
            writer.writerow(
                [
                    "model_type",
                    "seed",
                    "best_epoch",
                    "best_validation_auroc",
                    "checkpoint",
                    "learning_rate",
                    "batch_size",
                    "max_epochs",
                    "patience",
                ]
            )

        writer.writerow(
            [
                "glaucoma_only",
                seed,
                best_epoch,
                f"{best_auroc:.6f}",
                str(checkpoint_path),
                LEARNING_RATE,
                BATCH_SIZE,
                MAX_EPOCHS,
                PATIENCE,
            ]
        )


# ---------------------------------------------------------
# Train one complete seed run
# ---------------------------------------------------------

def train_seed(seed, device):

    print()
    print("=" * 60)
    print(f"Glaucoma-only training | Seed {seed}")
    print("=" * 60)

    # Changes training randomness only.
    # The dataset split already exists in the Task 7 CSV.
    set_seed(seed)

    # -----------------------------------------------------
    # Existing Task 7 train and validation splits
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

    # Generator makes shuffled training order reproducible
    # for the current Task 11 seed.
    generator = torch.Generator()
    generator.manual_seed(seed)

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        num_workers=0,
        generator=generator,
    )

    validation_loader = DataLoader(
        validation_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        num_workers=0,
    )

    # -----------------------------------------------------
    # Glaucoma class imbalance
    # -----------------------------------------------------

    glaucoma_weight = calculate_glaucoma_weight(
        LABELS_CSV
    )

    print(
        f"Glaucoma positive weight: "
        f"{glaucoma_weight:.4f}"
    )

    glaucoma_pos_weight = torch.tensor(
        [glaucoma_weight],
        dtype=torch.float32,
        device=device,
    )

    loss_fn = nn.BCEWithLogitsLoss(
        pos_weight=glaucoma_pos_weight
    )

    # -----------------------------------------------------
    # Glaucoma-only model
    # -----------------------------------------------------

    model = GlaucomaNet(
        pretrained=True
    ).to(device)

    optimizer = torch.optim.Adam(
        model.parameters(),
        lr=LEARNING_RATE,
    )

    # -----------------------------------------------------
    # Best-model tracking / early stopping
    # -----------------------------------------------------

    best_auroc = float("-inf")
    best_epoch = 0
    epochs_without_improvement = 0

    CHECKPOINT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    checkpoint_path = (
        CHECKPOINT_DIR
        / f"glaucoma_seed_{seed}_best.pt"
    )

    # -----------------------------------------------------
    # Training
    # -----------------------------------------------------

    for epoch in range(1, MAX_EPOCHS + 1):

        train_loss = train_one_epoch(
            model=model,
            loader=train_loader,
            optimizer=optimizer,
            loss_fn=loss_fn,
            device=device,
        )

        validation_loss, validation_auroc = validate(
            model=model,
            loader=validation_loader,
            loss_fn=loss_fn,
            device=device,
        )

        print(
            f"Epoch {epoch}/{MAX_EPOCHS} | "
            f"Train loss: {train_loss:.4f} | "
            f"Validation loss: {validation_loss:.4f} | "
            f"Validation AUROC: {validation_auroc:.4f}"
        )

        # -------------------------------------------------
        # Save whenever validation AUROC reaches a new best
        # -------------------------------------------------

        if validation_auroc > best_auroc:

            best_auroc = validation_auroc
            best_epoch = epoch
            epochs_without_improvement = 0

            torch.save(
                {
                    "model_type": "glaucoma_only",
                    "seed": seed,
                    "epoch": epoch,
                    "validation_auroc": validation_auroc,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict":
                        optimizer.state_dict(),
                    "learning_rate": LEARNING_RATE,
                    "batch_size": BATCH_SIZE,
                    "max_epochs": MAX_EPOCHS,
                    "patience": PATIENCE,
                },
                checkpoint_path,
            )

            print(
                f"  New best model saved: "
                f"AUROC {best_auroc:.4f}"
            )

        else:
            epochs_without_improvement += 1

            print(
                "  No AUROC improvement "
                f"({epochs_without_improvement}/"
                f"{PATIENCE})"
            )

        # -------------------------------------------------
        # Early stopping
        # -------------------------------------------------

        if epochs_without_improvement >= PATIENCE:

            print(
                f"Early stopping after epoch {epoch}."
            )

            break

    # -----------------------------------------------------
    # Record this seed's best result
    # -----------------------------------------------------

    save_result(
        seed=seed,
        best_epoch=best_epoch,
        best_auroc=best_auroc,
        checkpoint_path=checkpoint_path,
    )

    print()
    print(
        f"Seed {seed} complete | "
        f"Best epoch: {best_epoch} | "
        f"Best validation AUROC: {best_auroc:.4f}"
    )

    print(
        "Best checkpoint:",
        checkpoint_path,
    )


# ---------------------------------------------------------
# Main Task 11 glaucoma pipeline
# ---------------------------------------------------------

def main():

    print("TASK 11 - GLAUCOMA-ONLY ABLATION")
    print("--------------------------------")

    if not LABELS_CSV.exists():
        raise FileNotFoundError(
            f"Label file not found: {LABELS_CSV}"
        )

    if not IMAGE_DIR.exists():
        raise FileNotFoundError(
            "ODIR preprocessed image directory "
            f"not found: {IMAGE_DIR}"
        )

    device = torch.device(
        "cuda" if torch.cuda.is_available() else "cpu"
    )

    print("Device:", device)
    print("Label file:", LABELS_CSV)
    print("Image directory:", IMAGE_DIR)
    print("Seeds:", SEEDS)
    print("Maximum epochs:", MAX_EPOCHS)
    print("Early stopping patience:", PATIENCE)
    print("Selection metric: validation glaucoma AUROC")

    for seed in SEEDS:
        train_seed(
            seed=seed,
            device=device,
        )

    print()
    print("--------------------------------")
    print(
        "All glaucoma-only Task 11 runs completed."
    )


if __name__ == "__main__":
    main()