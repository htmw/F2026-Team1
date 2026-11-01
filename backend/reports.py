
"""PDF exports for screenings and patients."""

from io import BytesIO

from fpdf import FPDF

from . import service


LABELS = {
    "no_concern": "No concern",
    "refer": "Refer",
    "uncertain": "Uncertain, refer",
}

EYES = {
    "right": "Right eye (OD)",
    "left": "Left eye (OS)",
}


def _text(value):
    """Convert values to text supported by standard PDF fonts."""
    if value is None:
        return "-"

    return str(value).encode(
        "latin-1",
        errors="replace",
    ).decode("latin-1")


def _date(value):
    """Format stored timestamps for display."""
    return _text(value).replace("T", " ")[:16]


def _pdf(title):
    """Create a PDF with the DUAL header."""

    pdf = FPDF()

    pdf.set_auto_page_break(
        auto=True,
        margin=15,
    )

    pdf.add_page()

    pdf.set_font("Helvetica", "B", 16)

    pdf.cell(
        0,
        10,
        _text(title),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_font("Helvetica", "I", 9)

    pdf.multi_cell(
        0,
        5,
        (
            "DUAL: triage, not diagnosis. "
            "Dummy data for a student project."
        ),
    )

    pdf.ln(4)

    return pdf


def _line(pdf, label, value, bold=False):
    """Write a labeled field, wrapping long values."""

    pdf.set_font("Helvetica", "B", 10)

    pdf.cell(
        45,
        6,
        _text(label),
    )

    pdf.set_font(
        "Helvetica",
        "B" if bold else "",
        10,
    )

    pdf.multi_cell(
        0,
        6,
        _text(value),
        new_x="LMARGIN",
        new_y="NEXT",
    )


def _version(version):
    """Format model version metadata."""

    if version is None:
        return "-"

    text = version["id"]

    if version["commit"]:
        text += f" ({version['commit']})"

    if version["is_mock"]:
        text += (
            " - mock model, "
            "scores are not real"
        )

    return text


def _section_heading(pdf, title):
    """Write a section heading."""

    pdf.ln(4)

    pdf.set_font("Helvetica", "B", 12)

    pdf.cell(
        0,
        8,
        _text(title),
        new_x="LMARGIN",
        new_y="NEXT",
    )


def _table_header(pdf, columns, font_size=10):
    """Render a bordered table header."""

    pdf.set_font(
        "Helvetica",
        "B",
        font_size,
    )

    for heading, width in columns:
        pdf.cell(
            width,
            7,
            _text(heading),
            border=1,
        )

    pdf.ln()


def _table_row(pdf, cells, widths, font_size=9):
    """Render one bordered table row."""

    if pdf.get_y() + 7 > pdf.page_break_trigger:
        pdf.add_page()

    pdf.set_font(
        "Helvetica",
        "",
        font_size,
    )

    for value, width in zip(cells, widths):
        text = _text(value)

        # Keep each value inside its table cell.
        while (
            text
            and pdf.get_string_width(text) > width - 4
        ):
            text = text[:-1]

        pdf.cell(
            width,
            7,
            text,
            border=1,
        )

    pdf.ln()


def _screening_images(pdf, screening):
    """Embed the processed photograph and available heatmaps."""

    image = screening.get("image")

    if image is None:
        return

    # Keep images together on one page.
    if pdf.get_y() + 85 > pdf.page_break_trigger:
        pdf.add_page()

    pdf.ln(3)

    y = pdf.get_y()

    image_id = image["id"]

    photo_bytes = service.storage_download(
        "processed-images",
        f"{image_id}_512.jpg",
    )

    pdf.image(
        BytesIO(photo_bytes),
        x=10,
        y=y,
        w=55,
    )

    for index, condition in enumerate(
        screening["conditions"]
    ):
        heatmap_id = condition.get("heatmap_id")

        if heatmap_id is None:
            continue

        heatmap_bytes = service.storage_download(
            "heatmaps",
            f"{heatmap_id}.jpg",
        )

        pdf.image(
            BytesIO(heatmap_bytes),
            x=70 + 60 * index,
            y=y,
            w=55,
        )

    pdf.set_y(y + 57)

    pdf.set_font(
        "Helvetica",
        "",
        8,
    )

    for label in (
        "Photo (preprocessed)",
        "Heatmap: cataract",
        "Heatmap: glaucoma",
    ):
        pdf.cell(
            60,
            5,
            label,
        )

    pdf.ln()

    pdf.multi_cell(
        0,
        4,
        (
            "Heatmaps show which areas most "
            "influenced a score. They are a "
            "visual aid, not proof, and never "
            "show where disease is."
        ),
    )


def _screening_block(pdf, screening, with_images):
    """Render details for one screening."""

    _line(
        pdf,
        "Screening",
        screening["id"],
    )

    _line(
        pdf,
        "Date and time",
        _date(screening["created_at"]),
    )

    _line(
        pdf,
        "Eye",
        EYES[screening["eye"]],
    )

    if screening["skipped"]:
        reason = (
            screening.get("skip_reason")
            or "No reason provided"
        )

        _line(
            pdf,
            "Result",
            f"Not screened ({reason})",
            bold=True,
        )

        return

    _line(
        pdf,
        "Overall result",
        LABELS[screening["overall_result"]],
        bold=True,
    )

    _line(
        pdf,
        "Image quality check",
        screening["image"][
            "quality_status"
        ].capitalize(),
    )

    _line(
        pdf,
        "Model version",
        _version(
            screening["model_version"]
        ),
    )

    pdf.ln(2)

    columns = (
        ("Condition", 35),
        ("Result", 40),
        ("Calibrated", 30),
        ("Raw", 25),
        ("Threshold", 30),
    )

    _table_header(pdf, columns)

    widths = [width for _, width in columns]

    for condition in screening["conditions"]:
        cells = (
            condition["condition"].capitalize(),
            LABELS[condition["result"]],
            f"{condition['calibrated_score']:.2f}",
            f"{condition['raw_score']:.2f}",
            f"{condition['threshold']:.2f} (example)",
        )

        _table_row(
            pdf,
            cells,
            widths,
            font_size=10,
        )

    if with_images:
        _screening_images(
            pdf,
            screening,
        )


def screening_pdf(screening):
    """Generate a complete screening summary PDF."""

    pdf = _pdf("Screening summary")

    patient = screening["patient"]

    _line(
        pdf,
        "Patient",
        (
            f"{patient['full_name']} "
            f"- {patient['id']}"
        ),
    )

    _screening_block(
        pdf,
        screening,
        with_images=not screening["skipped"],
    )

    return bytes(pdf.output())


def patient_pdf(detail, screenings):
    """Generate a patient dossier PDF."""

    pdf = _pdf("Patient dossier")

    patient = detail["patient"]

    _line(
        pdf,
        "Patient",
        (
            f"{patient['full_name']} "
            f"- {patient['id']}"
        ),
    )

    _line(
        pdf,
        "Age, sex",
        (
            f"{patient['age']}, "
            f"{patient['sex']}"
        ),
    )

    last_encounter = (
        detail["last_encounter"] or "-"
    )

    _line(
        pdf,
        "Last encounter",
        _date(last_encounter),
    )

    # Latest screening for each eye.
    for eye in ("right", "left"):
        screening = detail["latest"][eye]

        _section_heading(
            pdf,
            f"Latest: {EYES[eye]}",
        )

        if screening is None:
            pdf.set_font(
                "Helvetica",
                "",
                10,
            )

            pdf.cell(
                0,
                6,
                "Not screened yet",
                new_x="LMARGIN",
                new_y="NEXT",
            )

        else:
            _screening_block(
                pdf,
                screening,
                with_images=False,
            )

    _section_heading(
        pdf,
        "All screenings",
    )

    columns = (
        ("Screening", 28),
        ("Date", 32),
        ("Eye", 32),
        ("Overall", 30),
        ("Cataract", 32),
        ("Glaucoma", 32),
    )

    _table_header(
        pdf,
        columns,
        font_size=9,
    )

    widths = [
        width
        for _, width in columns
    ]

    for screening in screenings:
        cells = (
            screening["id"],
            _date(screening["created_at"]),
            EYES[screening["eye"]],
            (
                "Not screened"
                if screening["skipped"]
                else LABELS[
                    screening["overall_result"]
                ]
            ),
            LABELS.get(
                screening["cataract"],
                "-",
            ),
            LABELS.get(
                screening["glaucoma"],
                "-",
            ),
        )

        _table_row(
            pdf,
            cells,
            widths,
            font_size=9,
        )

    return bytes(pdf.output())
