"""Turn calibrated scores into results.

Per condition: at or above the threshold is Refer, below is No concern, and too
close to call is Uncertain, refer. The real uncertain rule comes from Task 12;
for now a score within the margin of the threshold counts as uncertain.
Per eye: Refer if any condition is Refer or Uncertain, otherwise No concern.
"""


def condition_result(score, threshold, margin):
    if abs(score - threshold) < margin:
        return "uncertain"
    return "refer" if score >= threshold else "no_concern"


def flag_reason(score, threshold, result):
    """One plain sentence for the Screening record ("why flagged").

    The score keeps all 3 decimals, so the sentence never rounds it differently
    from the number stored next to it.
    """
    if result == "uncertain":
        return f"Score {score:.3f} is too close to the threshold {threshold:.2f} to call, so refer."
    if result == "refer":
        return f"Score {score:.3f} is at or above the threshold {threshold:.2f}."
    return f"Score {score:.3f} is below the threshold {threshold:.2f}."


def overall_result(results):
    return "refer" if any(r in ("refer", "uncertain") for r in results) else "no_concern"
