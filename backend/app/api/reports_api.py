"""Report generation endpoints.

Two ways to get a report out of this router:

1. Data-driven (works today, no other module required): POST the exact
   JSON shape from ``app.reports.schemas`` and get a PDF or HTML file
   back. This is the contract the frontend / any other service can
   build against right now.

2. Live convenience wrappers (``GET .../{account}`` etc.): these pull
   data from the existing detection/risk/investigation endpoints and
   format it as a report. They depend on ``AMLDetectionEngine`` /
   ``RiskEngine`` / the database layer, which are still being built
   out elsewhere in this codebase. Each one fails clearly (HTTP 503)
   with an explanation rather than crashing the process if those
   pieces aren't wired up yet -- once they are, these endpoints start
   working with no changes here.
"""
import logging
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse, Response

from app.reports.schemas import (
    FlaggedCase,
    FlaggedCasesReport,
    IndividualReport,
    OverviewReport,
    Transaction,
)
from app.reports.generator import (
    PDFBackendUnavailable,
    generate_flagged_cases_report,
    generate_flagged_cases_report_pdf,
    generate_individual_report,
    generate_individual_report_pdf,
    generate_overview_report,
    generate_overview_report_pdf,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reports", tags=["Reports"])

ReportFormat = Literal["pdf", "html"]


def _respond(html: str, pdf_bytes_fn, fmt: ReportFormat, filename: str):
    if fmt == "html":
        return HTMLResponse(content=html)

    try:
        pdf_bytes = pdf_bytes_fn()
    except PDFBackendUnavailable as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ============================================================
# 1. Data-driven endpoints -- accept the report payload directly
# ============================================================


@router.post("/overview")
def create_overview_report(
    data: OverviewReport,
    format: ReportFormat = Query("pdf"),
):
    """Generate the transaction overview report from a caller-supplied payload."""
    html = generate_overview_report(data)
    return _respond(
        html,
        lambda: generate_overview_report_pdf(data),
        format,
        f"{data.report_id}-overview.pdf",
    )


@router.post("/flagged-cases")
def create_flagged_cases_report(
    data: FlaggedCasesReport,
    format: ReportFormat = Query("pdf"),
):
    """Generate the flagged-cases queue report from a caller-supplied payload."""
    html = generate_flagged_cases_report(data)
    return _respond(
        html,
        lambda: generate_flagged_cases_report_pdf(data),
        format,
        f"{data.report_id}-flagged-cases.pdf",
    )


@router.post("/investigation")
def create_individual_report(
    data: IndividualReport,
    format: ReportFormat = Query("pdf"),
):
    """Generate a single-case investigation report from a caller-supplied payload."""
    html = generate_individual_report(data)
    return _respond(
        html,
        lambda: generate_individual_report_pdf(data),
        format,
        f"{data.report_id}-{data.case_id}.pdf",
    )


# ============================================================
# 2. Live convenience wrappers -- assemble the payload from the
#    rest of the platform, then render it the same way as above.
# ============================================================


def _risk_level_recommendations(risk_level: str, patterns: list[str]) -> list[str]:
    """Baseline, rule-based recommended actions by risk tier.

    This is a placeholder for the "Automated investigation workflow
    recommendations" advanced feature -- swap this out for an
    AI-generated recommendation once that's available; the report
    layer doesn't care where the strings come from.
    """
    base = {
        "critical": [
            "Escalate immediately for compliance review and freeze the account pending investigation.",
            "File a Suspicious Activity Report (SAR) if the activity cannot be explained.",
        ],
        "high": [
            "Open a formal investigation case.",
            "Request updated KYC and source-of-funds documentation.",
        ],
        "medium": [
            "Place the account under enhanced monitoring.",
            "Review the account's transaction history over the last 90 days.",
        ],
        "low": [
            "Continue routine monitoring.",
        ],
    }
    recommendations = list(base.get(risk_level.lower(), base["low"]))
    if "circular_flow" in patterns:
        recommendations.append("Trace the full circular-flow chain to identify the ultimate beneficiary.")
    if "mule_behavior" in patterns:
        recommendations.append("Verify whether the account holder is aware of / complicit in the fund movement.")
    if "crypto_offramp" in patterns:
        recommendations.append("Identify the receiving wallet/exchange and check it against known high-risk wallets.")
    return recommendations


@router.get("/investigation/{account}")
def get_investigation_report(
    account: str,
    format: ReportFormat = Query("pdf"),
):
    """Build an individual investigation report for one account from live data."""
    try:
        from app.api.investigation import get_investigation
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Investigation report is unavailable: the detection/risk "
                f"engine this endpoint depends on isn't implemented yet ({exc})."
            ),
        ) from exc

    try:
        investigation = get_investigation(account)
    except HTTPException:
        raise
    except Exception as exc:  # underlying engine not wired up yet
        logger.exception("Failed to assemble investigation for %s", account)
        raise HTTPException(
            status_code=503,
            detail=(
                "Investigation report is unavailable: the detection/risk "
                f"engine raised an error ({exc})."
            ),
        ) from exc

    entity = investigation["entity"]
    patterns = investigation.get("patterns", [])
    reasons = investigation.get("reasons", [])
    risk_level = entity["risk_level"]

    data = IndividualReport(
        case_id=f"CASE-{account}",
        account_id=account,
        risk_score=entity["risk_score"],
        risk_level=risk_level,
        investigation_summary=(
            f"Account {account} was assigned a risk score of "
            f"{entity['risk_score']:.1f}/100 ({risk_level}). "
            + (
                f"Detected pattern(s): {', '.join(patterns)}."
                if patterns
                else "No specific AML pattern was matched; score is behaviour-driven."
            )
        ),
        transactions=[
            Transaction(
                transaction_id=tx["transaction_id"],
                timestamp=str(tx["timestamp"]),
                sender_account=tx["sender_account"],
                receiver_account=tx["receiver_account"],
                amount=tx["amount"],
                currency=tx.get("currency") or "INR",
                channel=tx.get("channel"),
                country=tx.get("country"),
                city=tx.get("city"),
                status="flagged",
                flag_reason=reasons[0] if reasons else None,
            )
            for tx in investigation.get("transactions", [])
        ],
        risk_indicators=patterns or ["No specific pattern matched."],
        supporting_evidence=reasons or ["No supporting evidence recorded."],
        analyst_observations=[
            "Review generated automatically; awaiting analyst sign-off.",
        ],
        recommendations=_risk_level_recommendations(risk_level, patterns),
    )

    html = generate_individual_report(data)
    return _respond(
        html,
        lambda: generate_individual_report_pdf(data),
        format,
        f"{data.report_id}-{data.case_id}.pdf",
    )


@router.get("/flagged-cases")
def get_flagged_cases_report(
    format: ReportFormat = Query("pdf"),
    min_risk_score: float = Query(0, ge=0, le=100),
):
    """Build the flagged-cases report for every account currently at risk."""
    try:
        from app.api.risk import get_risk_scores
    except ImportError as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "Flagged-cases report is unavailable: the risk engine "
                f"this endpoint depends on isn't implemented yet ({exc})."
            ),
        ) from exc

    try:
        risk_result = get_risk_scores()
    except Exception as exc:
        logger.exception("Failed to assemble flagged cases")
        raise HTTPException(
            status_code=503,
            detail=f"Flagged-cases report is unavailable: the risk engine raised an error ({exc}).",
        ) from exc

    cases = []
    for item in risk_result.get("risk_scores", []):
        if item["risk_score"] <= min_risk_score:
            continue
        patterns = item.get("patterns", [])
        reasons = item.get("reasons", [])
        cases.append(
            FlaggedCase(
                case_id=f"CASE-{item['account']}",
                account_id=item["account"],
                risk_score=item["risk_score"],
                risk_level=item["risk_level"],
                suspicious_transactions=len(patterns) or 1,
                primary_reason=reasons[0] if reasons else "Elevated risk score",
            )
        )

    data = FlaggedCasesReport(total_cases=len(cases), cases=cases)

    html = generate_flagged_cases_report(data)
    return _respond(
        html,
        lambda: generate_flagged_cases_report_pdf(data),
        format,
        f"{data.report_id}-flagged-cases.pdf",
    )