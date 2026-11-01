"""Tests for backend/results.py (how the app turns a score into a result).

Run from the repo folder:  python -m pytest tests/test_results.py
"""
import sys
from pathlib import Path

import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "scripts"))
from backend.results import condition_result, overall_result  # noqa: E402
from select_calibration_settings import decision_metrics  # noqa: E402


@pytest.mark.parametrize("score, expected", [
    (0.75, "uncertain"),   # exactly threshold + margin
    (0.25, "uncertain"),   # exactly threshold - margin
    (0.5, "uncertain"),
    (0.76, "refer"),
    (0.24, "no_concern"),
])
def test_margin_edges(score, expected):
    assert condition_result(score, 0.5, 0.25) == expected


def test_matches_frozen_rule():
    # The app must call a score uncertain exactly when the frozen rule does.
    threshold, margin = 0.4, 0.125
    for score in np.r_[np.linspace(0, 1, 401), threshold - margin, threshold + margin]:
        # decision_metrics needs both labels, so score the same value twice.
        frozen = decision_metrics([score, score], [1, 0], threshold, margin)
        app = condition_result(float(score), threshold, margin)
        assert (app == "uncertain") == (frozen["uncertain_count"] == 2)
        if app != "uncertain":
            assert (app == "refer") == (frozen["ordinary_referral_count"] == 2)


def test_overall_result():
    assert overall_result(["no_concern", "no_concern"]) == "no_concern"
    assert overall_result(["no_concern", "uncertain"]) == "refer"
    assert overall_result(["refer", "no_concern"]) == "refer"
