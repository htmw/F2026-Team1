"""PDF exports: one screening (Export summary) and one patient (Export Dossier)."""
from fpdf import FPDF

from . import db

LABELS = {"no_concern": "No concern", "refer": "Refer", "uncertain": "Uncertain, refer"}
EYES = {"right": "Right eye (OD)", "left": "Left eye (OS)"}


def _pdf(title):
    pdf = FPDF()
    pdf.set_auto_page_break(True, margin=15)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 5, "DUAL: triage, not diagnosis. Dummy data for a student project.", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    return pdf


def _line(pdf, label, value, bold=False):
    pdf.set_font("Helvetica", "B", 10)
    pdf.cell(45, 6, label)
    pdf.set_font("Helvetica", "B" if bold else "", 10)
    pdf.cell(0, 6, str(value), new_x="LMARGIN", new_y="NEXT")


def _version(v):
    if v is None:
        return "-"
    text = v["id"] + (f" ({v['commit']})" if v["commit"] else "")
    return text + (" - mock model, scores are not real" if v["is_mock"] else "")


def _screening_block(pdf, s, with_images):
    _line(pdf, "Screening", s["id"])
    _line(pdf, "Date and time", s["created_at"].replace("T", " ")[:16])
    _line(pdf, "Eye", EYES[s["eye"]])
    if s["skipped"]:
        _line(pdf, "Result", f"Not screened ({s['skip_reason']})", bold=True)
        return
    _line(pdf, "Overall result", LABELS[s["overall_result"]], bold=True)
    _line(pdf, "Image quality check", s["image"]["quality_status"].capitalize())
    _line(pdf, "Model version", _version(s["model_version"]))
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    for head, w in (("Condition", 35), ("Result", 40), ("Calibrated", 30), ("Raw", 25), ("Threshold", 30)):
        pdf.cell(w, 7, head, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 10)
    for c in s["conditions"]:
        for text, w in ((c["condition"].capitalize(), 35), (LABELS[c["result"]], 40),
                        (f"{c['calibrated_score']:.2f}", 30), (f"{c['raw_score']:.2f}", 25),
                        (f"{c['threshold']:.2f} (example)", 30)):
            pdf.cell(w, 7, text, border=1)
        pdf.ln()
    if with_images:
        pdf.ln(3)
        y = pdf.get_y()
        photo = db.STORAGE / "images" / f"{s['image']['id']}_512.jpg"
        pdf.image(str(photo), x=10, y=y, w=55)
        for i, c in enumerate(s["conditions"]):
            pdf.image(str(db.STORAGE / "heatmaps" / f"{c['heatmap_id']}.jpg"), x=70 + 60 * i, y=y, w=55)
        pdf.set_y(y + 57)
        pdf.set_font("Helvetica", "", 8)
        pdf.cell(60, 5, "Photo (preprocessed)")
        pdf.cell(60, 5, "Heatmap: cataract")
        pdf.cell(60, 5, "Heatmap: glaucoma", new_x="LMARGIN", new_y="NEXT")
        pdf.multi_cell(0, 4, "Heatmaps show which areas most influenced a score. "
                             "They are a visual aid, not proof, and never show where disease is.")


def screening_pdf(s):
    pdf = _pdf("Screening summary")
    p = s["patient"]
    _line(pdf, "Patient", f"{p['full_name']} - {p['id']}")
    _screening_block(pdf, s, with_images=not s["skipped"])
    return bytes(pdf.output())


def patient_pdf(detail, screenings):
    pdf = _pdf("Patient dossier")
    p = detail["patient"]
    _line(pdf, "Patient", f"{p['full_name']} - {p['id']}")
    _line(pdf, "Age, sex", f"{p['age']}, {p['sex']}")
    _line(pdf, "Last encounter", (detail["last_encounter"] or "-").replace("T", " ")[:16])
    for eye in ("right", "left"):
        s = detail["latest"][eye]
        pdf.ln(4)
        pdf.set_font("Helvetica", "B", 12)
        pdf.cell(0, 8, f"Latest: {EYES[eye]}", new_x="LMARGIN", new_y="NEXT")
        if s is None:
            pdf.set_font("Helvetica", "", 10)
            pdf.cell(0, 6, "Not screened yet", new_x="LMARGIN", new_y="NEXT")
        else:
            _screening_block(pdf, s, with_images=False)
    pdf.ln(4)
    pdf.set_font("Helvetica", "B", 12)
    pdf.cell(0, 8, "All screenings", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "B", 10)
    widths = (30, 35, 35, 30, 30, 30)
    for head, w in zip(("Screening", "Date", "Eye", "Overall", "Cataract", "Glaucoma"), widths):
        pdf.cell(w, 7, head, border=1)
    pdf.ln()
    pdf.set_font("Helvetica", "", 9)
    for s in screenings:
        cells = (s["id"], s["created_at"].replace("T", " ")[:16], EYES[s["eye"]],
                 "Not screened" if s["skipped"] else LABELS[s["overall_result"]],
                 LABELS.get(s["cataract"], "-"), LABELS.get(s["glaucoma"], "-"))
        for text, w in zip(cells, widths):
            pdf.cell(w, 7, text, border=1)
        pdf.ln()
    return bytes(pdf.output())
