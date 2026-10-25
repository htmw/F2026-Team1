"""Numerical helpers for frozen external evaluation."""

import numpy as np


def probabilities(logits):
    """Convert finite logits to float64 probabilities without overflow."""
    z = np.asarray(logits, dtype=np.float64)
    if z.ndim != 1 or not len(z) or not np.isfinite(z).all():
        raise ValueError("Expected a nonempty finite logit vector")
    return np.exp(-np.logaddexp(0, -z))


