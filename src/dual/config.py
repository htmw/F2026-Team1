"""Shared settings for all DUAL code. Import from here; never redefine them elsewhere."""
import os
import random

# One seed for the whole project. Do not change it after the Task 7 split is made.
SEED = 42


def set_seed(seed: int = SEED) -> None:
    """Make random choices repeatable in Python, NumPy and PyTorch."""
    import numpy as np
    import torch

    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed_all(seed)
