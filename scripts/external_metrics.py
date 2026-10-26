"""Metrics for frozen external evaluation, independent of image inference."""

import numpy as np
from sklearn.metrics import average_precision_score, roc_auc_score


def probabilities(logits):
    """Convert finite logits to float64 probabilities without overflow."""
    z = np.asarray(logits, dtype=np.float64)
    if z.ndim != 1 or not len(z) or not np.isfinite(z).all():
        raise ValueError("Expected a nonempty finite logit vector")
    return np.exp(-np.logaddexp(0, -z))


def reliability_bins(p, y):
    """Use ten fixed bins, including probability one in the last bin."""
    bins = np.minimum((p * 10).astype(int), 9)
    records = []
    for i in range(10):
        mask = bins == i
        count = int(mask.sum())
        records.append(dict(lower=i / 10, upper=(i + 1) / 10, count=count,
                            mean_probability=float(p[mask].mean()) if count else None,
                            positive_fraction=float(y[mask].mean()) if count else None))
    return records


def calculate_metrics(y, raw, scale, offset, threshold, margin):
    """Return ranking, calibration and both referral policies on all images."""
    y, raw = np.asarray(y), np.asarray(raw, dtype=np.float64)
    if y.ndim != 1 or y.shape != raw.shape or not np.isin(y, [0, 1]).all():
        raise ValueError("Labels must be binary and aligned with logits")
    if not np.isfinite([scale, offset, threshold, margin]).all() or scale <= 0:
        raise ValueError("Invalid calibration settings")
    if not 0 <= threshold <= 1 or margin < 0:
        raise ValueError("Invalid threshold or margin")
    before = probabilities(raw)
    with np.errstate(over="raise", invalid="raise"):
        adjusted = scale * raw + offset
    if not np.isfinite(adjusted).all():
        raise ValueError("Calibration produced non-finite logits")
    p = probabilities(adjusted)
    uncertain = np.abs(p - threshold) <= margin
    binary = p >= threshold
    bins = {"raw": reliability_bins(before, y), "calibrated": reliability_bins(p, y)}
    both = len(np.unique(y)) == 2
    common = dict(n=len(y), positives=int(y.sum()), negatives=int((y == 0).sum()),
                  prevalence=float(y.mean()),
                  auroc=float(roc_auc_score(y, raw)) if both else None,
                  average_precision=float(average_precision_score(y, raw)) if both else None,
                  ranking_reason=None if both else "Only one label class")
    for name, scores, logits in (("raw", before, raw), ("calibrated", p, adjusted)):
        common[f"brier_{name}"] = float(np.mean((scores - y) ** 2))
        signed_logits = np.where(y == 1, -logits, logits)
        common[f"log_loss_{name}"] = float(np.mean(np.logaddexp(0, signed_logits)))
        common[f"ece_{name}"] = sum(
            b["count"] / len(y) * abs(b["mean_probability"] - b["positive_fraction"])
            for b in bins[name] if b["count"])
    result = []
    for policy in ("threshold_only", "final_referral"):
        u = uncertain if policy == "final_referral" else np.zeros(len(y), dtype=bool)
        referred = binary | u
        tp, fp = int((referred & (y == 1)).sum()), int((referred & (y == 0)).sum())
        tn, fn = int((~referred & (y == 0)).sum()), int((~referred & (y == 1)).sum())
        row = dict(common, policy=policy, tp=tp, fp=fp, tn=tn, fn=fn)
        for name, numerator, denominator in (
            ("sensitivity", tp, tp + fn), ("specificity", tn, tn + fp),
            ("ppv", tp, tp + fp), ("npv", tn, tn + fn),
        ):
            row[name] = numerator / denominator if denominator else None
            row[name + "_reason"] = None if denominator else "Zero denominator"
        row["balanced_accuracy"] = ((row["sensitivity"] + row["specificity"]) / 2
                                    if both else None)
        retained = ~u
        row.update(uncertain_count=int(u.sum()), uncertain_rate=float(u.mean()),
                   ordinary_referral_count=int((binary & ~u).sum()),
                   referral_count=int(referred.sum()), referral_rate=float(referred.mean()),
                   no_concern_count=int((~referred).sum()), coverage=float(retained.mean()),
                   retained_count=int(retained.sum()),
                   retained_positives=int(y[retained].sum()),
                   retained_negatives=int((y[retained] == 0).sum()),
                   retained_error=float(np.mean(binary[retained] != y[retained]))
                   if retained.any() else None,
                   retained_error_reason=None if retained.any() else "No retained decisions")
        result.append(row)
    return result, bins


def bootstrap_indices(y, replicates=2000, seed=42, max_attempts=10000):
    """Generate reusable image-level resamples, rejecting single-class draws."""
    y = np.asarray(y)
    if y.ndim != 1 or set(np.unique(y)) != {0, 1}:
        raise ValueError("Bootstrap requires both binary classes")
    if replicates < 1 or max_attempts < replicates:
        raise ValueError("Invalid bootstrap counts")
    rng = np.random.default_rng(seed)
    draws, attempts = [], 0
    while len(draws) < replicates and attempts < max_attempts:
        index = rng.integers(0, len(y), len(y))
        attempts += 1
        if len(np.unique(y[index])) == 2:
            draws.append(index)
    if len(draws) != replicates:
        raise ValueError("Insufficient valid bootstrap samples")
    return draws, attempts


CI_METRICS = ("auroc", "average_precision", "sensitivity", "specificity", "ppv", "npv",
              "brier_raw", "brier_calibrated", "referral_rate", "uncertain_rate")


def add_intervals(rows, y, raw, settings, draws):
    """Add percentile intervals without refitting any model settings."""
    if not len(draws):
        raise ValueError("Confidence intervals require bootstrap samples")
    y, raw = np.asarray(y), np.asarray(raw)
    if y.ndim != 1 or y.shape != raw.shape or not np.isin(y, [0, 1]).all():
        raise ValueError("Bootstrap labels and logits must be aligned binary vectors")
    samples = [{key: [] for key in CI_METRICS} for _ in rows]
    for index in draws:
        index = np.asarray(index)
        if (index.ndim != 1 or index.size == 0
                or not np.issubdtype(index.dtype, np.integer)
                or np.any(index < 0) or np.any(index >= len(y))):
            raise ValueError("Invalid bootstrap indices")
        metrics, _ = calculate_metrics(y[index], raw[index], **settings)
        for store, metrics_row in zip(samples, metrics, strict=True):
            for key in CI_METRICS:
                if metrics_row[key] is not None:
                    store[key].append(metrics_row[key])
    for row, store in zip(rows, samples, strict=True):
        for key, values in store.items():
            enough = len(values) >= int(np.ceil(0.95 * len(draws)))
            lo, hi = np.quantile(values, [0.025, 0.975]) if enough else (None, None)
            row.update({key + "_ci_low": float(lo) if lo is not None else None,
                        key + "_ci_high": float(hi) if hi is not None else None,
                        key + "_ci_valid": len(values),
                        key + "_ci_reason": None if enough else "Fewer than 95% valid replicates"})
    return rows
