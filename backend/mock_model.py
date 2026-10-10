"""MOCK model: stands in for the trained DUAL model until Sprint 3 (SCRUM-64).

The scores are made up. They are repeatable (the same photo always gets the
same scores), so the screens can be built and tested, but they mean nothing.
Heatmaps carry a "MOCK" label so they are never mistaken for Grad-CAM.

To plug in the real model, replace predict(), calibrate() and heatmap() and
keep their inputs and outputs the same. Nothing else in the back end changes.
"""
import hashlib

import cv2
import numpy as np

VERSION = "v0-mock"
CONDITIONS = ("cataract", "glaucoma")

# Example values until Task 12 fits the real ones on the
# validation split. They are stored with the model version, never hard-coded in the app.
THRESHOLDS = {"cataract": 0.35, "glaucoma": 0.50}
UNCERTAIN_MARGIN = 0.05


def _rng(image, condition):
    digest = hashlib.sha256(image.tobytes() + condition.encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], "big"))


def predict(image):
    """image: the 512 x 512 BGR photo from crop_fundus. Returns a raw score (0 to 1) per condition."""
    return {c: round(float(_rng(image, c).beta(1.3, 2.5)), 3) for c in CONDITIONS}


def calibrate(condition, raw_score):
    """Task 12 fits calibration on the validation split. Until then the score passes through."""
    return raw_score


def heatmap(image, condition):
    """Fake Grad-CAM: a smooth blob in a repeatable place, blended over the photo."""
    rng = _rng(image, condition)
    h, w = image.shape[:2]
    cx, cy = rng.uniform(0.3, 0.7) * w, rng.uniform(0.3, 0.7) * h
    yy, xx = np.mgrid[0:h, 0:w]
    blob = np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * (0.12 * w) ** 2))
    colour = cv2.applyColorMap((blob * 255).astype(np.uint8), cv2.COLORMAP_JET)
    out = cv2.addWeighted(image, 0.6, colour, 0.4, 0)
    cv2.putText(out, "MOCK", (12, 36), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255, 255, 255), 2, cv2.LINE_AA)
    return out
