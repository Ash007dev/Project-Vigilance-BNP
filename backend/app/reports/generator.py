"""Build AML report payloads, HTML pages, and PDF downloads."""

from io import BytesIO
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

from .schemas import FlaggedCasesReport, IndividualReport, OverviewReport


class PDFBackendUnavailable(RuntimeError):
    """Raised when the optional PDF library cannot be loaded."""


BASE_DIR = Path(__file__).resolve().parent
env = Environment(
    loader=FileSystemLoader(BASE_DIR / "templates"),
    autoescape=select_autoescape(["html", "xml"]),
)


def report_payload(snapshot: dict, account: dict, transactions: list[dict]) -> dict:
    """Return the data used by the browser's investigation report."""
    return {
        "snapshot_id": snapshot["snapshot_id"],
        "account_id": account["account_id"],
        "score": account["score"],
        "risk": account["risk"],
        "indicators": account["indicators"],
        "transactions": transactions,
        "pattern_status": snapshot["pattern_status"],
        "audit": snapshot["audit"],
        "limitations": snapshot["limitations"],
    }


def generate_overview_report(data: OverviewReport) -> str:
    return env.get_template("overview_report.html").render(**data.model_dump())


def generate_flagged_cases_report(data: FlaggedCasesReport) -> str:
    return env.get_template("flagged_cases_report.html").render(**data.model_dump())


def generate_individual_report(data: IndividualReport) -> str:
    return env.get_template("individual_report.html").render(**data.model_dump())


def _pdf_bytes(title: str, lines: list[str]) -> bytes:
    """Create a small, readable PDF from report text."""
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
    except ImportError as exc:  # pragma: no cover - dependency is installed in normal runs
        raise PDFBackendUnavailable(
            "PDF generation is unavailable. Install backend requirements first."
        ) from exc

    output = BytesIO()
    document = canvas.Canvas(output, pagesize=A4)
    width, height = A4
    y = height - 48

    document.setTitle(title)
    document.setFont("Helvetica-Bold", 16)
    document.drawString(48, y, title)
    y -= 28
    document.setFont("Helvetica", 9)

    for line in lines:
        safe_line = str(line).encode("latin-1", "replace").decode("latin-1")
        for start in range(0, len(safe_line) or 1, 100):
            if y < 48:
                document.showPage()
                document.setFont("Helvetica", 9)
                y = height - 48
            document.drawString(48, y, safe_line[start : start + 100])
            y -= 14

    document.save()
    return output.getvalue()


def generate_overview_report_pdf(data: OverviewReport) -> bytes:
    lines = [
        f"Report ID: {data.report_id}",
        f"Total transactions: {data.total_transactions}",
        f"Flagged transactions: {data.flagged_transactions}",
        f"Unflagged transactions: {data.unflagged_transactions}",
    ]
    lines.extend(
        f"{tx.transaction_id}: {tx.sender_account} -> {tx.receiver_account}, "
        f"{tx.currency} {tx.amount:.2f}, {tx.status}"
        for tx in data.transactions
    )
    return _pdf_bytes("Transaction Overview", lines)


def generate_flagged_cases_report_pdf(data: FlaggedCasesReport) -> bytes:
    lines = [f"Report ID: {data.report_id}", f"Total cases: {data.total_cases}"]
    lines.extend(
        f"{case.case_id}: {case.account_id}, score {case.risk_score:.1f}, "
        f"{case.risk_level}, {case.primary_reason}"
        for case in data.cases
    )
    return _pdf_bytes("Flagged Cases", lines)


def generate_individual_report_pdf(data: IndividualReport) -> bytes:
    lines = [
        f"Report ID: {data.report_id}",
        f"Case ID: {data.case_id}",
        f"Account: {data.account_id}",
        f"Risk: {data.risk_score:.1f} ({data.risk_level})",
        f"Summary: {data.investigation_summary}",
        *[f"Indicator: {item}" for item in data.risk_indicators],
        *[f"Evidence: {item}" for item in data.supporting_evidence],
        *[f"Recommendation: {item}" for item in data.recommendations],
    ]
    return _pdf_bytes("Investigation Report", lines)
