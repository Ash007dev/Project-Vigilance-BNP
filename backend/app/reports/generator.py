from pathlib import Path
from jinja2 import Environment, FileSystemLoader

from .schemas import (
    OverviewReport,
    FlaggedCasesReport,
    IndividualReport
)


BASE_DIR = Path(__file__).resolve().parent

env = Environment(
    loader=FileSystemLoader(BASE_DIR / "templates")
)


def generate_overview_report(data: OverviewReport) -> str:
    template = env.get_template("overview_report.html")

    return template.render(
        total_transactions=data.total_transactions,
        flagged_transactions=data.flagged_transactions,
        unflagged_transactions=data.unflagged_transactions,
        transactions=data.transactions
    )


def generate_flagged_cases_report(data: FlaggedCasesReport) -> str:
    template = env.get_template("flagged_cases_report.html")

    return template.render(
        total_cases=data.total_cases,
        cases=data.cases
    )


def generate_individual_report(data: IndividualReport) -> str:
    template = env.get_template("individual_report.html")

    return template.render(
        case_id=data.case_id,
        account_id=data.account_id,
        risk_score=data.risk_score,
        risk_level=data.risk_level,
        investigation_summary=data.investigation_summary,
        transactions=data.transactions,
        risk_indicators=data.risk_indicators,
        supporting_evidence=data.supporting_evidence,
        analyst_observations=data.analyst_observations,
        recommendations=data.recommendations
    )