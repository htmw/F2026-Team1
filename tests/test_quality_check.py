"""Tests for scripts/quality_check.py (the upload check for the DUAL app).

Run from the repo folder:  python -m pytest tests/test_quality_check.py
"""
import sys
from pathlib import Path

import cv2
import numpy as np
import pytest

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "scripts"))
import quality_check as qc  # noqa: E402

ODIR = REPO / "data/Internal/ODIR-5K/Training Images"


def png(img):
    return cv2.imencode(".png", img)[1].tobytes()


def fundus_like(h=1000, w=1500, brightness=1.0, border=0, cut=False):
    """A reddish disc on a plain border, like a fundus camera photo."""
    img = np.full((h, w, 3), border, np.uint8)
    r = int(h * (0.6 if cut else 0.45))
    colour = tuple(int(c * brightness) for c in (40, 90, 180))  # BGR: red dominant
    cv2.circle(img, (w // 2, h // 2), r, colour, -1)
    return img


# Photos that must pass: the check must not turn away real fundus photos


def test_fundus_like_photo_passes():
    assert qc.check(png(fundus_like())) == ("passed", None)


def test_circle_cut_top_and_bottom_passes():
    # many fundus cameras cut the circle at the top and bottom
    assert qc.check(png(fundus_like(cut=True))) == ("passed", None)


def test_white_border_passes():
    assert qc.check(png(fundus_like(border=255))) == ("passed", None)


def test_dim_hazy_photo_passes():
    # dark or hazy photos are often diseased eyes; they go to the model, not rejected
    assert qc.check(png(fundus_like(brightness=0.25))) == ("passed", None)


def test_blurry_photo_passes():
    img = cv2.GaussianBlur(fundus_like(), (61, 61), 0)
    assert qc.check(png(img)) == ("passed", None)


@pytest.mark.skipif(not ODIR.exists(), reason="ODIR images not available")
def test_real_odir_training_photos_pass():
    for name in ["0_left.jpg", "0_right.jpg", "2166_left.jpg", "1260_right.jpg"]:
        # 2166_left is a washed-out cataract photo, 1260_right one of the darkest glaucoma photos
        assert qc.check(ODIR / name) == ("passed", None), name


# Uploads that must fail


def test_unreadable_bytes_fail():
    assert qc.check(b"this is not a photo") == ("failed", "unreadable")


def test_empty_file_fails():
    assert qc.check(b"") == ("failed", "unreadable")


def test_truncated_jpeg_fails():
    ok, data = cv2.imencode(".jpg", fundus_like())
    assert qc.check(data.tobytes()[:500]) == ("failed", "unreadable")


def test_almost_black_photo_fails():
    img = (fundus_like() * 0.04).astype(np.uint8)
    assert qc.check(png(img)) == ("failed", "too_dark")


@pytest.mark.parametrize("value", [255, 128])
def test_blank_photo_fails(value):
    assert qc.check(png(np.full((800, 1200, 3), value, np.uint8))) == ("failed", "not_fundus")


def test_text_document_fails():
    img = np.full((1000, 1500, 3), 255, np.uint8)
    cv2.putText(img, "Patient report", (100, 500), cv2.FONT_HERSHEY_SIMPLEX, 4, (0, 0, 0), 8)
    assert qc.check(png(img)) == ("failed", "not_fundus")


def test_random_noise_fails():
    img = np.random.default_rng(0).integers(0, 256, (800, 1200, 3), dtype=np.uint8)
    assert qc.check(png(img)) == ("failed", "not_fundus")


def test_blue_photo_fails():
    # a fundus is always redder than it is blue
    img = fundus_like()
    img[:] = np.where(img > 0, np.array([180, 90, 40], np.uint8), img)
    assert qc.check(png(img)) == ("failed", "not_fundus")


def test_tight_crop_without_border_fails():
    # the app expects the full photo with the camera border; every ODIR training photo has one
    img = np.full((600, 600, 3), (40, 90, 180), np.uint8)
    assert qc.check(png(img)) == ("failed", "not_fundus")


def test_reason_texts_exist_for_every_reason():
    assert set(qc.REASONS) == {"unreadable", "too_dark", "not_fundus"}
