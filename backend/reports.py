
"""PDF exports for screenings and patients."""

from io import BytesIO

from fpdf import FPDF

from . import db, service


LABELS = {
    "no_concern": "No concern",
    "refer": "Refer",
    "uncertain": "Uncertain, refer",
}

EYES = {
    "right": "Right eye (OD)",
    "left": "Left eye (OS)",
}


def _pdf(title):
    pdf = FPDF()

    pdf.set_auto_page_break(
        True,
        margin=15,
    )

    pdf.add_page()

    pdf.set_font(
        "Helvetica",
        "B",
        16,
    )

    pdf.cell(
        0,
        10,
        title,
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_font(
        "Helvetica",
        "I",
        9,
    )

    pdf.cell(
        0,
        5,
        (
            "DUAL: triage, not diagnosis. "
            "Dummy data for a student project."
        ),
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.ln(4)
    return pdf


def _line(pdf, label, value, bold=False):
    pdf.set_font(
        "Helvetica",
        "B",
        10,
    )

    pdf.cell(
        45,
        6,
        label,
    )

    pdf.set_font(
        "Helvetica",
        "B" if bold else "",
        10,
    )

    pdf.cell(
        0,
        6,
        str(value),
        new_x="LMARGIN",
        new_y="NEXT",
    )


def _version(version):
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


def _screening_block(pdf, screening, with_images):
    _line(
        pdf,
        "Screening",
        screening["id"],
    )

    _line(
        pdf,
        "Date and time",
        screening["created_at"].replace(
            "T", " "
        )[:16],
    )

    _line(
        pdf,
        "Eye",
        EYES[screening["eye"]],
    )

    if screening["skipped"]:
        _line(
            pdf,
            "Result",
            (
                "Not screened "
                f"({screening['skip_reason']})"
            ),
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

    pdf.set_font(
        "Helvetica",
        "B",
        10,
    )

    columns = (
        ("Condition", 35),
        ("Result", 40),
        ("Calibrated", 30),
        ("Raw", 25),
        ("Threshold", 30),
    )

    for heading, width in columns:
        pdf.cell(
            width,
            7,
            heading,
            border=1,
        )

    pdf.ln()

    pdf.set_font(
        "Helvetica",
        "",
        10,
    )

    for condition in screening["conditions"]:
        cells = (
            (
                condition["condition"].capitalize(),
                35,
            ),
            (
                LABELS[condition["result"]],
                40,
            ),
            (
                f"{condition['calibrated_score']:.2f}",
                30,
            ),
            (
                f"{condition['raw_score']:.2f}",
                25,
            ),
            (
                f"{condition['threshold']:.2f} (example)",
                30,
            ),
        )

        for text, width in cells:
            pdf.cell(
                width,
                7,
                text,
                border=1,
            )

        pdf.ln()

    if with_images:
        pdf.ln(3)
        y = pdf.get_y()

        # Original SQLite/local-storage code:
        #
        # photo = (
        #     db.STORAGE
        #     / "images"
        #     / f"{screening['image']['id']}_512.jpg"
        # )
        #
        # pdf.image(
        #     str(photo),
        #     x=10,
        #     y=y,
        #     w=55,
        # )
        #
        # for i, condition in enumerate(
        #     screening["conditions"]
        # ):
        #     heatmap_path = (
        #         db.STORAGE
        #         / "heatmaps"
        #         / f"{condition['heatmap_id']}.jpg"
        #     )
        #
        #     pdf.image(
        #         str(heatmap_path),
        #         x=70 + 60 * i,
        #         y=y,
        #         w=55,
        #     )

        # Supabase Storage implementation

        image_id = screening["image"]["id"]

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
            heatmap_id = condition["heatmap_id"]

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

        pdf.cell(
            60,
            5,
            "Photo (preprocessed)",
        )

        pdf.cell(
            60,
            5,
            "Heatmap: cataract",
        )

        pdf.cell(
            60,
            5,
            "Heatmap: glaucoma",
            new_x="LMARGIN",
            new_y="NEXT",
        )

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


def screening_pdf(screening):
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
        last_encounter.replace(
            "T", " "
        )[:16],
    )

    for eye in ("right", "left"):
        screening = detail["latest"][eye]

        pdf.ln(4)

        pdf.set_font(
            "Helvetica",
            "B",
            12,
        )

        pdf.cell(
            0,
            8,
            f"Latest: {EYES[eye]}",
            new_x="LMARGIN",
            new_y="NEXT",
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

    pdf.ln(4)

    pdf.set_font(
        "Helvetica",
        "B",
        12,
    )

    pdf.cell(
        0,
        8,
        "All screenings",
        new_x="LMARGIN",
        new_y="NEXT",
    )

    pdf.set_font(
        "Helvetica",
        "B",
        10,
    )

    widths = (
        30, 35, 35,
        30, 30, 30,
    )

    headings = (
        "Screening",
        "Date",
        "Eye",
        "Overall",
        "Cataract",
        "Glaucoma",
    )

    for heading, width in zip(
        headings,
        widths,
    ):
        pdf.cell(
            width,
            7,
            heading,
            border=1,
        )

    pdf.ln()

    pdf.set_font(
        "Helvetica",
        "",
        9,
    )

    for screening in screenings:
        cells = (
            screening["id"],
            screening["created_at"].replace(
                "T", " "
            )[:16],
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

        for text, width in zip(
            cells,
            widths,
        ):
            pdf.cell(
                width,
                7,
                text,
                border=1,
            )

        pdf.ln()

    return bytes(pdf.output())
