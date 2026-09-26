from typing import Optional
from uuid import uuid4

from pydantic import BaseModel, Field


def new_report_id() -> str:
    return f"REPORT-{uuid4().hex[:12].upper()}"


class Transaction(BaseModel):
    transaction_id: str
    timestamp: str

    sender_account: str
    receiver_account: str

    amount: float
    currency: str = "INR"

    channel: Optional[str] = None
    country: Optional[str] = None
    city: Optional[str] = None

    status: str = "unflagged"
    flag_reason: Optional[str] = None


class FlaggedCase(BaseModel):
    case_id: str
    account_id: str

    risk_score: float = Field(ge=0, le=100)
    risk_level: str

    suspicious_transactions: int
    primary_reason: str


class OverviewReport(BaseModel):
    report_id: str = Field(default_factory=new_report_id)
    total_transactions: int
    flagged_transactions: int
    unflagged_transactions: int

    transactions: list[Transaction]


class FlaggedCasesReport(BaseModel):
    report_id: str = Field(default_factory=new_report_id)
    total_cases: int

    cases: list[FlaggedCase]


class IndividualReport(BaseModel):
    report_id: str = Field(default_factory=new_report_id)
    case_id: str
    account_id: str

    risk_score: float = Field(ge=0, le=100)
    risk_level: str

    investigation_summary: str

    transactions: list[Transaction]

    risk_indicators: list[str]
    supporting_evidence: list[str]

    analyst_observations: list[str]
    recommendations: list[str]
