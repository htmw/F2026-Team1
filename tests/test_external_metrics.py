"""Check external statistics on synthetic labels and predictions."""

from pathlib import Path
import sys

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from external_metrics import calculate_metrics, bootstrap_indices, add_intervals


def metrics(y, z, **overrides):
    settings = dict(scale=1, offset=0, threshold=0.5, margin=0)
    settings.update(overrides)
    return calculate_metrics(y, z, **settings)


def test_perfect_ranking_and_confusion():
    rows, bins = metrics([0, 0, 1, 1], [-3, -2, 2, 3])
    for row in rows:
        assert (row['tp'], row['tn'], row['fp'], row['fn']) == (2, 2, 0, 0)
        assert row['auroc'] == row['average_precision'] == 1
        assert row['sensitivity'] == row['specificity'] == 1
    assert sum(b['count'] for b in bins['raw']) == 4
    assert any(b['mean_probability'] is None for b in bins['raw'])


def test_ties_and_all_uncertain():
    rows, _ = metrics([0, 1], [0, 0], margin=0.1)
    assert rows[0]['auroc'] == 0.5
    assert rows[1]['uncertain_count'] == 2
    assert rows[1]['coverage'] == 0
    assert rows[1]['retained_error'] is None
    assert rows[1]['referral_count'] == 2


def test_ranking_survives_sigmoid_rounding():
    rows, _ = metrics([0, 1], [100, 101])
    assert rows[0]['auroc'] == 1


def test_uncertain_referral_rescues_below_threshold_positive():
    rows, _ = metrics([1, 0], [-0.1, -3], margin=0.05)
    assert (rows[0]['tp'], rows[0]['fp'], rows[0]['tn'], rows[0]['fn']) == (0, 0, 1, 1)
    assert (rows[1]['tp'], rows[1]['fp'], rows[1]['tn'], rows[1]['fn']) == (1, 0, 1, 0)
    assert rows[1]['ordinary_referral_count'] == 0
    assert rows[1]['uncertain_count'] == 1


def test_zero_referrals_and_single_class_are_explicit():
    rows, _ = metrics([0, 0], [-3, -2])
    assert rows[1]['ppv'] is None
    assert rows[1]['ppv_reason'] == 'Zero denominator'
    assert rows[1]['sensitivity'] is None
    assert rows[1]['auroc'] is None
    with pytest.raises(ValueError, match='both binary classes'):
        bootstrap_indices([0, 0])


@pytest.mark.parametrize('z', [[float('nan'), 0], [0, float('inf')], []])
def test_invalid_logits_rejected(z):
    with pytest.raises(ValueError):
        metrics([0, 1], z)


def test_calibration_overflow_is_rejected():
    with pytest.raises(FloatingPointError):
        metrics([0, 1], [1e308, -1e308], scale=10)


def test_log_loss_is_stable_for_large_correct_logits():
    rows, _ = metrics([1, 0], [1000, -1000])
    assert rows[0]['log_loss_raw'] == 0


def test_bootstrap_reproducibility_and_undefined_intervals():
    y, z = np.array([0, 0, 1, 1]), np.array([-4, -3, -2, -1])
    draws, attempts = bootstrap_indices(y, replicates=30)
    other, other_attempts = bootstrap_indices(y, replicates=30)
    assert attempts == other_attempts
    assert all(np.array_equal(a, b) for a, b in zip(draws, other))
    assert all(len(np.unique(y[d])) == 2 for d in draws)
    rows, _ = metrics(y, z)
    add_intervals(rows, y, z, dict(scale=1, offset=0, threshold=0.5, margin=0), draws)
    assert rows[1]['auroc_ci_low'] == rows[1]['auroc_ci_high'] == 1
    assert rows[1]['ppv_ci_valid'] == 0
    assert rows[1]['ppv_ci_low'] is None


def test_empty_bootstrap_rejected():
    rows, _ = metrics([0, 1], [-1, 1])
    with pytest.raises(ValueError, match='require bootstrap samples'):
        add_intervals(rows, [0, 1], [-1, 1], {}, [])


@pytest.mark.parametrize('index', [[0, 4], [-1, 0], [0.5, 1], [], [[0, 1]]])
def test_invalid_bootstrap_indices_rejected(index):
    rows, _ = metrics([0, 1], [-1, 1])
    with pytest.raises(ValueError, match='Invalid bootstrap indices'):
        add_intervals(rows, [0, 1], [-1, 1], dict(scale=1, offset=0, threshold=.5, margin=0), [index])
