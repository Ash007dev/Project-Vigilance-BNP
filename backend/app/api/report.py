from datetime import datetime
from io import BytesIO
from uuid import uuid4

import pandas as pd
from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    KeepTogether,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.db.database import engine
from app.detection.engine import AMLDetectionEngine
from app.risk.engine import RiskEngine


router = APIRouter()


# =========================================================
# REPORT CONFIGURATION
# =========================================================

MAX_REPORT_TRANSACTIONS = 500


# =========================================================
# PDF HEADER / FOOTER
# =========================================================

def add_page_header_footer(canvas, document):
    canvas.saveState()

    width, height = A4

    # Header
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.HexColor("#475569"))
    canvas.drawString(
        18 * mm,
        height - 12 * mm,
        "PROJECT VIGILANCE",
    )

    canvas.setFont("Helvetica", 7)
    canvas.drawRightString(
        width - 18 * mm,
        height - 12 * mm,
        "AML INVESTIGATION REPORT",
    )

    # Header line
    canvas.setStrokeColor(colors.HexColor("#CBD5E1"))
    canvas.setLineWidth(0.5)
    canvas.line(
        18 * mm,
        height - 15 * mm,
        width - 18 * mm,
        height - 15 * mm,
    )

    # Footer line
    canvas.line(
        18 * mm,
        15 * mm,
        width - 18 * mm,
        15 * mm,
    )

    # Footer
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#64748B"))

    canvas.drawString(
        18 * mm,
        9 * mm,
        "AI-assisted analysis | Final compliance decisions remain with authorized investigators",
    )

    canvas.drawRightString(
        width - 18 * mm,
        9 * mm,
        f"Page {document.page}",
    )

    canvas.restoreState()


# =========================================================
# HELPERS
# =========================================================

def safe_text(value):
    if value is None:
        return "-"

    if pd.isna(value):
        return "-"

    return str(value)


def format_amount(value):
    if value is None:
        return "-"

    try:
        return f"{float(value):,.2f}"
    except Exception:
        return str(value)


def format_timestamp(value):
    if value is None:
        return "-"

    try:
        timestamp = pd.to_datetime(value)
        return timestamp.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return str(value)


def classify_color(risk_level):
    risk_level = str(risk_level).upper()

    if risk_level == "CRITICAL":
        return colors.HexColor("#DC2626")

    if risk_level == "HIGH":
        return colors.HexColor("#EA580C")

    if risk_level == "MEDIUM":
        return colors.HexColor("#D97706")

    return colors.HexColor("#16A34A")


def build_styles():
    styles = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#0F172A"),
            alignment=TA_CENTER,
            spaceAfter=8,
        ),

        "subtitle": ParagraphStyle(
            "ReportSubtitle",
            parent=styles["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#64748B"),
            alignment=TA_CENTER,
            spaceAfter=20,
        ),

        "section": ParagraphStyle(
            "Section",
            parent=styles["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=colors.HexColor("#0F172A"),
            spaceBefore=10,
            spaceAfter=8,
        ),

        "subsection": ParagraphStyle(
            "Subsection",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceBefore=6,
            spaceAfter=5,
        ),

        "body": ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=13,
            textColor=colors.HexColor("#334155"),
            spaceAfter=6,
        ),

        "small": ParagraphStyle(
            "Small",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=7,
            leading=9,
            textColor=colors.HexColor("#64748B"),
        ),

        "table": ParagraphStyle(
            "Table",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=6.7,
            leading=8,
            textColor=colors.HexColor("#1E293B"),
        ),

        "table_header": ParagraphStyle(
            "TableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=6.7,
            leading=8,
            textColor=colors.white,
        ),

        "risk": ParagraphStyle(
            "Risk",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=14,
            leading=18,
            alignment=TA_CENTER,
        ),

        "bullet": ParagraphStyle(
            "Bullet",
            parent=styles["BodyText"],
            fontName="Helvetica",
            fontSize=8.8,
            leading=13,
            leftIndent=12,
            firstLineIndent=-8,
            textColor=colors.HexColor("#334155"),
            spaceAfter=4,
        ),
    }


# =========================================================
# LOAD INVESTIGATION DATA
# =========================================================

def load_report_data(account: str):

    # -----------------------------------------------------
    # Run detection + risk
    # -----------------------------------------------------

    detection_engine = AMLDetectionEngine()

    detection_results = detection_engine.run_all()

    risk_engine = RiskEngine(detection_results)

    risk_scores = risk_engine.calculate()

    selected_entity = None

    for item in risk_scores:
        if item.get("account") == account:
            selected_entity = item
            break

    if selected_entity is None:
        raise HTTPException(
            status_code=404,
            detail=f"No risk information found for account: {account}",
        )

    # -----------------------------------------------------
    # Load transactions
    # -----------------------------------------------------

    query = """
        SELECT
            transaction_id,
            timestamp,
            sender_account,
            receiver_account,
            amount,
            currency,
            channel,
            ip_address,
            device_id,
            country,
            city,
            crypto_flag,
            crypto_wallet
        FROM transactions
        WHERE
            sender_account = %(account)s
            OR receiver_account = %(account)s
            OR crypto_wallet = %(account)s
        ORDER BY timestamp ASC
    """

    with engine.connect() as connection:
        transactions_df = pd.read_sql(
            query,
            connection,
            params={"account": account},
        )

    if transactions_df.empty:
        transactions = []
    else:
        transactions_df = transactions_df.drop_duplicates(
            subset=["transaction_id"],
            keep="first",
        )

        total_transaction_count = len(transactions_df)

        transactions = transactions_df.head(
            MAX_REPORT_TRANSACTIONS
        ).to_dict("records")

    if transactions_df.empty:
        total_transaction_count = 0

    # -----------------------------------------------------
    # Relationships
    # -----------------------------------------------------

    accounts = set()
    devices = set()
    ips = set()
    wallets = set()

    for row in transactions:
        sender = safe_text(row.get("sender_account"))
        receiver = safe_text(row.get("receiver_account"))
        device = safe_text(row.get("device_id"))
        ip = safe_text(row.get("ip_address"))
        wallet = safe_text(row.get("crypto_wallet"))

        if sender != "-" and sender != account:
            accounts.add(sender)

        if receiver != "-" and receiver != account:
            accounts.add(receiver)

        if device != "-":
            devices.add(device)

        if ip != "-":
            ips.add(ip)

        if wallet != "-":
            wallets.add(wallet)

    return {
        "entity": selected_entity,
        "transactions": transactions,
        "total_transaction_count": total_transaction_count,
        "relationships": {
            "accounts": sorted(accounts),
            "devices": sorted(devices),
            "ips": sorted(ips),
            "wallets": sorted(wallets),
        },
    }


# =========================================================
# BUILD PDF
# =========================================================

def build_report_pdf(account: str):

    report_data = load_report_data(account)

    entity = report_data["entity"]

    transactions = report_data["transactions"]

    total_transaction_count = report_data[
        "total_transaction_count"
    ]

    relationships = report_data["relationships"]

    risk_score = entity["risk_score"]

    risk_level = entity["risk_level"]

    patterns = entity.get("patterns", [])

    reasons = entity.get("reasons", [])

    report_id = (
        f"VIG-{datetime.now().strftime('%Y%m%d')}-"
        f"{uuid4().hex[:8].upper()}"
    )

    generated_at = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    styles = build_styles()

    buffer = BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=18 * mm,
        leftMargin=18 * mm,
        topMargin=22 * mm,
        bottomMargin=22 * mm,
        title=f"Project Vigilance Investigation Report - {account}",
        author="Project Vigilance",
    )

    story = []

    # =====================================================
    # COVER / TITLE
    # =====================================================

    story.append(Spacer(1, 8 * mm))

    story.append(
        Paragraph(
            "PROJECT VIGILANCE",
            styles["title"],
        )
    )

    story.append(
        Paragraph(
            "AML INVESTIGATION REPORT",
            styles["subtitle"],
        )
    )

    story.append(
        HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor("#CBD5E1"),
            spaceBefore=4,
            spaceAfter=15,
        )
    )

    # Report metadata

    metadata = [
        [
            Paragraph("<b>Report ID</b>", styles["table"]),
            Paragraph(report_id, styles["table"]),
            Paragraph("<b>Generated</b>", styles["table"]),
            Paragraph(generated_at, styles["table"]),
        ],
        [
            Paragraph("<b>Entity</b>", styles["table"]),
            Paragraph(safe_text(account), styles["table"]),
            Paragraph("<b>Investigation Type</b>", styles["table"]),
            Paragraph(
                "Suspicious Account Investigation",
                styles["table"],
            ),
        ],
    ]

    metadata_table = Table(
        metadata,
        colWidths=[
            28 * mm,
            58 * mm,
            35 * mm,
            53 * mm,
        ],
    )

    metadata_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, -1),
                    colors.HexColor("#F1F5F9"),
                ),
                (
                    "BACKGROUND",
                    (2, 0),
                    (2, -1),
                    colors.HexColor("#F1F5F9"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor("#E2E8F0"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7,
                ),
            ]
        )
    )

    story.append(metadata_table)

    story.append(Spacer(1, 10))

    # =====================================================
    # EXECUTIVE SUMMARY
    # =====================================================

    story.append(
        Paragraph(
            "1. Executive Summary",
            styles["section"],
        )
    )

    summary_text = (
        f"Account <b>{safe_text(account)}</b> was identified "
        f"for investigation with a risk score of "
        f"<b>{risk_score}/100</b> and a risk classification "
        f"of <b>{safe_text(risk_level)}</b>. "
        f"The analysis identified {len(patterns)} suspicious "
        f"activity pattern(s) and {total_transaction_count} "
        f"unique transaction(s) associated with the entity."
    )

    story.append(
        Paragraph(
            summary_text,
            styles["body"],
        )
    )

    # =====================================================
    # RISK ASSESSMENT
    # =====================================================

    story.append(
        Paragraph(
            "2. Risk Assessment",
            styles["section"],
        )
    )

    risk_table = Table(
        [
            [
                Paragraph(
                    "<b>Risk Score</b>",
                    styles["table"],
                ),
                Paragraph(
                    f"{risk_score} / 100",
                    styles["risk"],
                ),
                Paragraph(
                    "<b>Risk Classification</b>",
                    styles["table"],
                ),
                Paragraph(
                    safe_text(risk_level),
                    styles["risk"],
                ),
            ]
        ],
        colWidths=[
            35 * mm,
            45 * mm,
            45 * mm,
            49 * mm,
        ],
    )

    risk_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (0, 0),
                    colors.HexColor("#F1F5F9"),
                ),
                (
                    "BACKGROUND",
                    (2, 0),
                    (2, 0),
                    colors.HexColor("#F1F5F9"),
                ),
                (
                    "TEXTCOLOR",
                    (3, 0),
                    (3, 0),
                    classify_color(risk_level),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor("#E2E8F0"),
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "MIDDLE",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    story.append(risk_table)

    # =====================================================
    # DETECTED PATTERNS
    # =====================================================

    story.append(
        Paragraph(
            "3. Detected AML Patterns",
            styles["section"],
        )
    )

    if patterns:

        pattern_rows = [
            [
                Paragraph("Pattern", styles["table_header"]),
                Paragraph("Risk Contribution", styles["table_header"]),
            ]
        ]

        for reason in reasons:

            pattern = reason.get("pattern", "-")

            points = reason.get("points", 0)

            pattern_rows.append(
                [
                    Paragraph(
                        safe_text(pattern),
                        styles["table"],
                    ),
                    Paragraph(
                        f"+{points}",
                        styles["table"],
                    ),
                ]
            )

        pattern_table = Table(
            pattern_rows,
            colWidths=[
                125 * mm,
                49 * mm,
            ],
            repeatRows=1,
        )

        pattern_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#334155"),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.3,
                        colors.HexColor("#CBD5E1"),
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor("#F8FAFC"),
                        ],
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        6,
                    ),
                ]
            )
        )

        story.append(pattern_table)

    else:

        story.append(
            Paragraph(
                "No AML patterns were identified for this entity.",
                styles["body"],
            )
        )

    # =====================================================
    # WHY FLAGGED
    # =====================================================

    story.append(
        Paragraph(
            "4. Investigation Evidence and Reasons",
            styles["section"],
        )
    )

    if reasons:

        for reason in reasons:

            pattern = safe_text(
                reason.get("pattern")
            )

            points = reason.get("points", 0)

            explanation = safe_text(
                reason.get("reason")
            )

            story.append(
                KeepTogether(
                    [
                        Paragraph(
                            f"<b>{pattern}</b> "
                            f"(Risk contribution: +{points})",
                            styles["subsection"],
                        ),
                        Paragraph(
                            f"• {explanation}",
                            styles["bullet"],
                        ),
                    ]
                )
            )

    else:

        story.append(
            Paragraph(
                "No specific risk reasons were available.",
                styles["body"],
            )
        )

    # =====================================================
    # RELATIONSHIP SUMMARY
    # =====================================================

    story.append(
        Paragraph(
            "5. Relationship and Network Evidence",
            styles["section"],
        )
    )

    relationship_data = [
        [
            Paragraph("Entity Type", styles["table_header"]),
            Paragraph("Count", styles["table_header"]),
            Paragraph("Examples", styles["table_header"]),
        ],
        [
            Paragraph("Connected Accounts", styles["table"]),
            Paragraph(
                str(len(relationships["accounts"])),
                styles["table"],
            ),
            Paragraph(
                ", ".join(
                    relationships["accounts"][:8]
                )
                or "-",
                styles["table"],
            ),
        ],
        [
            Paragraph("Devices", styles["table"]),
            Paragraph(
                str(len(relationships["devices"])),
                styles["table"],
            ),
            Paragraph(
                ", ".join(
                    relationships["devices"][:8]
                )
                or "-",
                styles["table"],
            ),
        ],
        [
            Paragraph("IP Addresses", styles["table"]),
            Paragraph(
                str(len(relationships["ips"])),
                styles["table"],
            ),
            Paragraph(
                ", ".join(
                    relationships["ips"][:8]
                )
                or "-",
                styles["table"],
            ),
        ],
        [
            Paragraph("Crypto Wallets", styles["table"]),
            Paragraph(
                str(len(relationships["wallets"])),
                styles["table"],
            ),
            Paragraph(
                ", ".join(
                    relationships["wallets"][:8]
                )
                or "-",
                styles["table"],
            ),
        ],
    ]

    relationship_table = Table(
        relationship_data,
        colWidths=[
            42 * mm,
            20 * mm,
            112 * mm,
        ],
        repeatRows=1,
    )

    relationship_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor("#334155"),
                ),
                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [
                        colors.white,
                        colors.HexColor("#F8FAFC"),
                    ],
                ),
                (
                    "VALIGN",
                    (0, 0),
                    (-1, -1),
                    "TOP",
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    6,
                ),
            ]
        )
    )

    story.append(relationship_table)

    # =====================================================
    # TRANSACTION EVIDENCE
    # =====================================================

    story.append(
        Paragraph(
            "6. Transaction Evidence",
            styles["section"],
        )
    )

    if total_transaction_count > MAX_REPORT_TRANSACTIONS:

        story.append(
            Paragraph(
                f"The entity is associated with "
                f"{total_transaction_count:,} unique transactions. "
                f"For report readability, the table below contains "
                f"the first {MAX_REPORT_TRANSACTIONS:,} transactions "
                f"in chronological order.",
                styles["small"],
            )
        )

        story.append(Spacer(1, 5))

    if transactions:

        transaction_rows = [
            [
                Paragraph("Transaction ID", styles["table_header"]),
                Paragraph("Timestamp", styles["table_header"]),
                Paragraph("Sender", styles["table_header"]),
                Paragraph("Receiver", styles["table_header"]),
                Paragraph("Amount", styles["table_header"]),
                Paragraph("Currency", styles["table_header"]),
                Paragraph("Channel", styles["table_header"]),
            ]
        ]

        for tx in transactions:

            transaction_rows.append(
                [
                    Paragraph(
                        safe_text(
                            tx.get("transaction_id")
                        ),
                        styles["table"],
                    ),
                    Paragraph(
                        format_timestamp(
                            tx.get("timestamp")
                        ),
                        styles["table"],
                    ),
                    Paragraph(
                        safe_text(
                            tx.get("sender_account")
                        ),
                        styles["table"],
                    ),
                    Paragraph(
                        safe_text(
                            tx.get("receiver_account")
                        ),
                        styles["table"],
                    ),
                    Paragraph(
                        format_amount(
                            tx.get("amount")
                        ),
                        styles["table"],
                    ),
                    Paragraph(
                        safe_text(
                            tx.get("currency")
                        ),
                        styles["table"],
                    ),
                    Paragraph(
                        safe_text(
                            tx.get("channel")
                        ),
                        styles["table"],
                    ),
                ]
            )

        transaction_table = Table(
            transaction_rows,
            colWidths=[
                27 * mm,
                27 * mm,
                27 * mm,
                27 * mm,
                22 * mm,
                18 * mm,
                26 * mm,
            ],
            repeatRows=1,
        )

        transaction_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#334155"),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.25,
                        colors.HexColor("#CBD5E1"),
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor("#F8FAFC"),
                        ],
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        4,
                    ),
                ]
            )
        )

        story.append(transaction_table)

    else:

        story.append(
            Paragraph(
                "No transactions were found for this entity.",
                styles["body"],
            )
        )

    # =====================================================
    # TIMELINE
    # =====================================================

    story.append(
        Paragraph(
            "7. Investigation Timeline",
            styles["section"],
        )
    )

    if transactions:

        timeline_rows = [
            [
                Paragraph("Time", styles["table_header"]),
                Paragraph("Event", styles["table_header"]),
                Paragraph("Transaction", styles["table_header"]),
                Paragraph("Amount", styles["table_header"]),
            ]
        ]

        for tx in transactions[:100]:

            sender = safe_text(
                tx.get("sender_account")
            )

            receiver = safe_text(
                tx.get("receiver_account")
            )

            transaction_id = safe_text(
                tx.get("transaction_id")
            )

            event = (
                f"{sender} → {receiver}"
            )

            timeline_rows.append(
                [
                    Paragraph(
                        format_timestamp(
                            tx.get("timestamp")
                        ),
                        styles["table"],
                    ),
                    Paragraph(
                        event,
                        styles["table"],
                    ),
                    Paragraph(
                        transaction_id,
                        styles["table"],
                    ),
                    Paragraph(
                        format_amount(
                            tx.get("amount")
                        ),
                        styles["table"],
                    ),
                ]
            )

        timeline_table = Table(
            timeline_rows,
            colWidths=[
                35 * mm,
                65 * mm,
                48 * mm,
                29 * mm,
            ],
            repeatRows=1,
        )

        timeline_table.setStyle(
            TableStyle(
                [
                    (
                        "BACKGROUND",
                        (0, 0),
                        (-1, 0),
                        colors.HexColor("#334155"),
                    ),
                    (
                        "GRID",
                        (0, 0),
                        (-1, -1),
                        0.3,
                        colors.HexColor("#CBD5E1"),
                    ),
                    (
                        "ROWBACKGROUNDS",
                        (0, 1),
                        (-1, -1),
                        [
                            colors.white,
                            colors.HexColor("#F8FAFC"),
                        ],
                    ),
                    (
                        "VALIGN",
                        (0, 0),
                        (-1, -1),
                        "TOP",
                    ),
                    (
                        "TOPPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                    (
                        "BOTTOMPADDING",
                        (0, 0),
                        (-1, -1),
                        5,
                    ),
                ]
            )
        )

        story.append(timeline_table)

    else:

        story.append(
            Paragraph(
                "No timeline events available.",
                styles["body"],
            )
        )

    # =====================================================
    # ANALYST OBSERVATIONS
    # =====================================================

    story.append(
        PageBreak()
    )

    story.append(
        Paragraph(
            "8. Analyst Observations",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            "Investigators may record additional observations, "
            "context, supporting evidence, or follow-up findings "
            "in this section.",
            styles["body"],
        )
    )

    observation_rows = []

    for _ in range(8):

        observation_rows.append(
            [
                Paragraph(
                    " ",
                    styles["body"],
                )
            ]
        )

    observation_table = Table(
        observation_rows,
        colWidths=[174 * mm],
        rowHeights=[10 * mm] * 8,
    )

    observation_table.setStyle(
        TableStyle(
            [
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.HexColor("#CBD5E1"),
                ),
                (
                    "INNERGRID",
                    (0, 0),
                    (-1, -1),
                    0.3,
                    colors.HexColor("#E2E8F0"),
                ),
            ]
        )
    )

    story.append(observation_table)

    # =====================================================
    # RECOMMENDED INVESTIGATION ACTIONS
    # =====================================================

    story.append(
        Paragraph(
            "9. Recommended Investigation Actions",
            styles["section"],
        )
    )

    actions = [
        "Review the supporting transaction evidence and detected AML patterns.",
        "Trace connected accounts and relationships using the investigation graph.",
        "Review shared device and IP relationships where applicable.",
        "Validate the identified activity against available customer and KYC information.",
        "Record analyst observations and supporting evidence before making any compliance determination.",
    ]

    for action in actions:

        story.append(
            Paragraph(
                f"• {action}",
                styles["bullet"],
            )
        )

    # =====================================================
    # AI SECTION
    # =====================================================

    story.append(
        Paragraph(
            "10. AI-Assisted Analysis",
            styles["section"],
        )
    )

    story.append(
        Paragraph(
            "AI-assisted explanation is available within the "
            "Project Vigilance investigation interface. "
            "The report currently records the deterministic "
            "risk score, detected patterns and supporting "
            "evidence independently of AI generation.",
            styles["body"],
        )
    )

    story.append(
        Paragraph(
            "AI explanation can be reviewed separately by the "
            "investigator when required.",
            styles["small"],
        )
    )

    # =====================================================
    # DISCLAIMER
    # =====================================================

    story.append(
        Paragraph(
            "11. Disclaimer",
            styles["section"],
        )
    )

    disclaimer = (
        "This report is generated by Project Vigilance as "
        "investigator decision-support. Risk scores, pattern "
        "detections and AI-generated explanations are intended "
        "to assist investigation and should be validated using "
        "appropriate evidence and organizational procedures. "
        "The output does not constitute a final compliance, "
        "legal or regulatory determination. Final decisions "
        "remain with authorized investigators and compliance "
        "personnel."
    )

    disclaimer_table = Table(
        [
            [
                Paragraph(
                    disclaimer,
                    styles["body"],
                )
            ]
        ],
        colWidths=[174 * mm],
    )

    disclaimer_table.setStyle(
        TableStyle(
            [
                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor("#FFF7ED"),
                ),
                (
                    "BOX",
                    (0, 0),
                    (-1, -1),
                    0.7,
                    colors.HexColor("#FED7AA"),
                ),
                (
                    "LEFTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "RIGHTPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    10,
                ),
            ]
        )
    )

    story.append(disclaimer_table)

    # =====================================================
    # BUILD
    # =====================================================

    document.build(
        story,
        onFirstPage=add_page_header_footer,
        onLaterPages=add_page_header_footer,
    )

    buffer.seek(0)

    return buffer, report_id


# =========================================================
# API
# =========================================================

@router.get("/report/{account}")
def generate_investigation_report(account: str):

    try:

        buffer, report_id = build_report_pdf(
            account
        )

        filename = (
            f"Project_Vigilance_"
            f"{account}_Investigation_Report.pdf"
        )

        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={
                "Content-Disposition": (
                    f'attachment; filename="{filename}"'
                ),
                "X-Report-ID": report_id,
            },
        )

    except HTTPException:
        raise

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=f"Report generation failed: {str(exc)}",
        )