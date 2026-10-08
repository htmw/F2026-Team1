# ---------------------------------------------------------
# TASK 11 - CATARACT-ONLY ABLATION TRAINING
# ---------------------------------------------------------
#
# Trains the cataract-only ablation model using three
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
# - Selection metric: validation cataract AUROC
# - Learning rate: 1e-4
# - Batch size: 8
# - Best checkpoint is saved, not simply the final epoch.
# ---------------------------------------------------------

from pathlib import Path
import subprocess

import pandas as pd
import torch
import torch.nn as nn
from sklearn.metrics import roc_auc_score
from torch.utils.data import DataLoader

from cataract_model import CataractOnlyNet
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

CHECKPOINT_DIR = Path("checkpoints/task11/cataract")
RESULTS_CSV = Path("results/task11/cataract_results.csv")
HISTORY_CSV = Path(
    "results/task11/cataract_training_history.csv"
)

SEEDS = [42, 43, 44]

BATCH_SIZE = 8
MAX_EPOCHS = 30
LEARNING_RATE = 1e-4
PATIENCE = 5


# ---------------------------------------------------------
# Get current Git commit hash
# ---------------------------------------------------------

def get_git_commit_hash():
    try:
        result = subprocess.run(
            [
                "git",
                "rev-parse",
                "HEAD",
            ],
            capture_output=True,
            text=True,
            check=True,
        )

        return result.stdout.strip()

    except (
        subprocess.CalledProcessError,
        FileNotFoundError,
    ):
        return "unknown"


# ---------------------------------------------------------
# Calculate cataract class weight from TRAIN split only
# ---------------------------------------------------------

def calculate_cataract_weight(labels_csv):
    labels = pd.read_csv(labels_csv)

    train_labels = labels[
        labels["split"] == "train"
    ].copy()

    if len(train_labels) == 0:
        raise ValueError(
            "No training rows found in label file."
        )

    cataract_positive = int(
        train_labels["cataract"].sum()
    )

    cataract_negative = (
        len(train_labels) - cataract_positive
    )

    if cataract_positive == 0:
        raise ValueError(
            "No positive cataract examples "
            "in training split."
        )

    return cataract_negative / cataract_positive


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
            batch["cataract"]
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
# Validate and calculate cataract AUROC
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
                batch["cataract"]
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
# Save per-epoch training history
# ---------------------------------------------------------

def save_training_history(
    seed,
    epoch,
    train_loss,
    validation_loss,
    validation_auroc,
    git_commit,
):
    HISTORY_CSV.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    columns = [
        "model_type",
        "seed",
        "epoch",
        "train_loss",
        "validation_loss",
        "validation_auroc",
        "git_commit",
    ]

    new_history = {
        "model_type": "cataract_only",
        "seed": seed,
        "epoch": epoch,
        "train_loss": f"{train_loss:.6f}",
        "validation_loss": f"{validation_loss:.6f}",
        "validation_auroc": f"{validation_auroc:.6f}",
        "git_commit": git_commit,
    }

    if HISTORY_CSV.exists():
        history = pd.read_csv(
            HISTORY_CSV
        )

        history = history[
            ~(
                (history["seed"] == seed)
                & (history["epoch"] == epoch)
            )
        ]

        history = pd.concat(
            [
                history,
                pd.DataFrame([new_history]),
            ],
            ignore_index=True,
        )

    else:
        history = pd.DataFrame(
            [new_history],
            columns=columns,
        )

    history = history.sort_values(
        by=[
            "seed",
            "epoch",
        ]
    ).reset_index(drop=True)

    history.to_csv(
        HISTORY_CSV,
        index=False,
    )


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

    columns = [
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

    new_result = {
        "model_type": "cataract_only",
        "seed": seed,
        "best_epoch": best_epoch,
        "best_validation_auroc": f"{best_auroc:.6f}",
        "checkpoint": str(checkpoint_path),
        "learning_rate": LEARNING_RATE,
        "batch_size": BATCH_SIZE,
        "max_epochs": MAX_EPOCHS,
        "patience": PATIENCE,
    }

    if RESULTS_CSV.exists():
        results = pd.read_csv(
            RESULTS_CSV
        )

        results = results[
            results["seed"] != seed
        ]

        results = pd.concat(
            [
                results,
                pd.DataFrame([new_result]),
            ],
            ignore_index=True,
        )

    else:
        results = pd.DataFrame(
            [new_result],
            columns=columns,
        )

    results = results.sort_values(
        by="seed"
    ).reset_index(drop=True)

    results.to_csv(
        RESULTS_CSV,
        index=False,
    )


# ---------------------------------------------------------
# Train one complete seed run
# ---------------------------------------------------------

def train_seed(seed):
    print()
    print("=" * 60)
    print(
        f"Task 11 Cataract-Only - Seed {seed}"
    )
    print("=" * 60)

    # Changes training randomness only.
    # The dataset split already exists in the Task 7 CSV.
    set_seed(seed)

    device = torch.device(
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print("Device:", device)

    git_commit = get_git_commit_hash()

    print(
        "Git commit:",
        git_commit,
    )

    # Clear previous training history for this seed before
    # starting a fresh run. This prevents stale epoch rows
    # from an older, longer run remaining after a shorter rerun.
    if HISTORY_CSV.exists():
        history = pd.read_csv(HISTORY_CSV)
        history = history[
            history["seed"] != seed
        ]
        history.to_csv(
            HISTORY_CSV,
            index=False,
        )

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

    print(
        "Training images:",
        len(train_dataset),
    )

    print(
        "Validation images:",
        len(validation_dataset),
    )

    # -----------------------------------------------------
    # DataLoaders
    # -----------------------------------------------------

    # Makes shuffled training order reproducible
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
    # Cataract class imbalance
    # -----------------------------------------------------

    cataract_weight = calculate_cataract_weight(
        LABELS_CSV
    )

    print(
        f"Cataract positive weight: "
        f"{cataract_weight:.4f}"
    )

    cataract_pos_weight = torch.tensor(
        [cataract_weight],
        dtype=torch.float32,
        device=device,
    )

    loss_fn = nn.BCEWithLogitsLoss(
        pos_weight=cataract_pos_weight
    )

    # -----------------------------------------------------
    # Cataract-only model
    # -----------------------------------------------------

    model = CataractOnlyNet(
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
        / f"cataract_seed_{seed}_best.pt"
    )

    # -----------------------------------------------------
    # Training
    # -----------------------------------------------------

    for epoch in range(
        1,
        MAX_EPOCHS + 1,
    ):
        train_loss = train_one_epoch(
            model=model,
            loader=train_loader,
            optimizer=optimizer,
            loss_fn=loss_fn,
            device=device,
        )

        (
            validation_loss,
            validation_auroc,
        ) = validate(
            model=model,
            loader=validation_loader,
            loss_fn=loss_fn,
            device=device,
        )

        print(
            f"Epoch {epoch}/{MAX_EPOCHS} | "
            f"Train loss: {train_loss:.4f} | "
            f"Validation loss: "
            f"{validation_loss:.4f} | "
            f"Validation cataract AUROC: "
            f"{validation_auroc:.6f}"
        )

        # -------------------------------------------------
        # Record per-epoch metrics
        # -------------------------------------------------

        save_training_history(
            seed=seed,
            epoch=epoch,
            train_loss=train_loss,
            validation_loss=validation_loss,
            validation_auroc=validation_auroc,
            git_commit=git_commit,
        )

        # -------------------------------------------------
        # Save whenever validation AUROC reaches a new best
        # -------------------------------------------------

        if validation_auroc > best_auroc:
            best_auroc = validation_auroc
            best_epoch = epoch
            epochs_without_improvement = 0

            # Save model state only.
            # Optimizer state is intentionally excluded.
            torch.save(
                {
                    "model_type": "cataract_only",
                    "seed": seed,
                    "epoch": epoch,
                    "validation_auroc":
                        float(validation_auroc),
                    "model_state_dict":
                        model.state_dict(),
                    "learning_rate":
                        LEARNING_RATE,
                    "batch_size":
                        BATCH_SIZE,
                    "max_epochs":
                        MAX_EPOCHS,
                    "patience":
                        PATIENCE,
                },
                checkpoint_path,
            )

            print(
                f"  New best model saved: "
                f"AUROC {best_auroc:.6f}"
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

        if (
            epochs_without_improvement
            >= PATIENCE
        ):
            print(
                f"Early stopping after "
                f"epoch {epoch}."
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
        f"Best validation cataract AUROC: "
        f"{best_auroc:.6f}"
    )

    print(
        "Best checkpoint:",
        checkpoint_path,
    )


# ---------------------------------------------------------
# Main Task 11 cataract pipeline
# ---------------------------------------------------------

def main():
    print(
        "TASK 11 - CATARACT-ONLY ABLATION"
    )
    print("--------------------------------")

    if not LABELS_CSV.exists():
        raise FileNotFoundError(
            f"Label file not found: "
            f"{LABELS_CSV}"
        )

    if not IMAGE_DIR.exists():
        raise FileNotFoundError(
            "ODIR preprocessed image directory "
            f"not found: {IMAGE_DIR}"
        )

    print("Seeds:", SEEDS)
    print("Learning rate:", LEARNING_RATE)
    print("Batch size:", BATCH_SIZE)
    print("Maximum epochs:", MAX_EPOCHS)
    print(
        "Early stopping patience:",
        PATIENCE,
    )
    print(
        "Selection metric: "
        "validation cataract AUROC"
    )

    for seed in SEEDS:
        train_seed(seed)

    print()
    print("--------------------------------")
    print(
        "All cataract-only "
        "Task 11 runs completed."
    )


if __name__ == "__main__":
    main()