"""Upload check for the DUAL app: is this photo screenable at all?

The check blocks only photos that cannot be screened:
    unreadable   the file is not an image that can be opened
    too_dark     the photo is almost completely black
    not_fundus   no round, reddish fundus area is found (for example a screenshot or a document)

It does NOT block dark, hazy, washed-out or blurry fundus photos. On ODIR
training photos those are often the diseased eyes (a cataract makes the photo
hazy), so they go to the model and get "Uncertain, refer" when the model is
not confident (Task 12).

The app expects a full fundus photo with the camera's dark or white border
(every ODIR training photo has one). A tight crop with no border fails as
not_fundus. The check runs only in the app, never in the evaluation pipeline,
so it does not change which test images are scored.

Thresholds were set on ODIR training photos only; no validation, test or external
data was used.
"""
import cv2
import numpy as np

MAX_SIDE = 1024          # work on a resized copy for speed
DARK_P99 = 15            # 99th percentile brightness below this = almost black
BORDER_TOL = 25          # how far a pixel must differ from the border colour
MIN_AREA_FRAC = 0.05     # fundus must cover at least this share of the photo (lowest training photo: 0.077)
MIN_FILL = 0.45          # fundus outline must fill this share of its enclosing circle (lowest training photo: 0.485)
MIN_RED_BLUE = 0.95      # a fundus is redder than it is blue (lowest training photo: 1.01)

REASONS = {
    "unreadable": "This file can't be opened as a photo",
    "too_dark": "Photo too dark to screen",
    "not_fundus": "This doesn't look like a fundus photo",
}


def _load(photo):
    """Accept a file path or raw bytes (as uploaded)."""
    if isinstance(photo, (bytes, bytearray)):
        if not photo:
            return None
        img = cv2.imdecode(np.frombuffer(photo, np.uint8), cv2.IMREAD_COLOR)
    else:
        img = cv2.imread(str(photo), cv2.IMREAD_COLOR)
    return img


def _resize(img):
    h, w = img.shape[:2]
    s = MAX_SIDE / max(h, w)
    if s < 1:
        img = cv2.resize(img, (round(w * s), round(h * s)), interpolation=cv2.INTER_AREA)
    return img


def _fundus_region(gray):
    """Mask of everything that differs from the border colour (black or white)."""
    h, w = gray.shape
    edge = np.concatenate([gray[0, :], gray[-1, :], gray[:, 0], gray[:, -1]])
    border = float(np.median(edge))
    blurred = cv2.GaussianBlur(gray, (9, 9), 0)
    mask = (np.abs(blurred.astype(np.int16) - border) > BORDER_TOL).astype(np.uint8) * 255
    k = max(5, (min(h, w) // 60) | 1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, np.ones((k, k), np.uint8))
    return mask


def measure(img):
    """The numbers the decision is based on."""
    img = _resize(img)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape
    p99 = float(np.percentile(gray, 99))
    mask = _fundus_region(gray)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return {"p99": p99, "area_frac": 0.0, "fill": 0.0, "red_blue": 0.0}
    # convex hull: dark fundus edges fade into the border, the hull bridges those gaps
    hull = cv2.convexHull(max(contours, key=cv2.contourArea))
    region = np.zeros_like(gray)
    cv2.drawContours(region, [hull], -1, 255, -1)
    inside = region > 0
    area = float(inside.sum())
    # enclosing circle, clipped to the photo (many fundus cameras cut the circle top and bottom)
    (cx, cy), r = cv2.minEnclosingCircle(hull)
    circle = np.zeros_like(gray)
    cv2.circle(circle, (round(cx), round(cy)), round(r), 255, -1)
    circle_area = float((circle > 0).sum())
    blue, _, red = [ch[inside].astype(np.float32).mean() for ch in cv2.split(img)]
    return {
        "p99": p99,
        "area_frac": area / (h * w),
        "fill": area / circle_area if circle_area else 0.0,
        "red_blue": float(red / (blue + 1e-6)),
    }


def check(photo):
    """Return (status, reason). status is "passed" or "failed"; reason is None when passed."""
    img = _load(photo)
    if img is None or img.size == 0:
        return "failed", "unreadable"
    m = measure(img)
    if m["p99"] < DARK_P99:
        return "failed", "too_dark"
    if m["red_blue"] < MIN_RED_BLUE:
        return "failed", "not_fundus"
    if m["area_frac"] < MIN_AREA_FRAC or m["fill"] < MIN_FILL:
        return "failed", "not_fundus"
    return "passed", None
