# Target path: backend/app/risk/schemas.py
"""
Data contracts for the risk module. Three kinds of thing live here:

1. What ingestion must hand you (TransactionInput, CustomerData)
2. What your teammates' modules MAY hand you later (GraphMetrics, DetectionSignals)
   -- every field Optional, absence means "not computed", never "zero"/"false"
3. What this module hands back out (RiskFeatures, RuleResult, RiskAssessment)

If ingestion already has an equivalent model in db/ or api/, tell me -- don't
let this become a second source of truth for the same shape.
"""
from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, Field, field_validator

KycStatus = Literal["complete", "pending", "incomplete", "unknown"]


class TransactionInput(BaseModel):
    """One normalized transaction record, as handed off by the ingestion module."""

    transaction_id: str
    timestamp: datetime
    sender_account: Optional[str] = None
    receiver_account: Optional[str] = None
    sender_name: Optional[str] = None
    receiver_name: Optional[str] = None
    sender_customer_id: Optional[str] = None
    receiver_customer_id: Optional[str] = None
    amount: Optional[float] = None
    currency: Optional[str] = None
    channel: Optional[str] = None
    ip_address: Optional[str] = None
    device_id: Optional[str] = None
    location_country: Optional[str] = None
    location_city: Optional[str] = None
    is_crypto: bool = False
    crypto_wallet: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def amount_must_be_non_negative(cls, v: Optional[float]) -> Optional[float]:
        if v is not None and v < 0:
            raise ValueError("amount cannot be negative")
        return v


class CustomerData(BaseModel):
    """
    Customer-level data, keyed by customer_id -- distinct from account-level
    transaction data. One customer can own multiple accounts.

    kyc_status defaults to "unknown", NOT "complete" -- an account with no
    customer record supplied should read as unverified, not as compliant.
    """

    customer_id: str
    kyc_status: KycStatus = "unknown"
    registration_country: Optional[str] = None


class GraphMetrics(BaseModel):
    """Optional signals from the graph module."""

    graph_degree: Optional[int] = None
    in_degree: Optional[int] = None
    out_degree: Optional[int] = None
    unique_counterparties: Optional[int] = None
    graph_depth: Optional[int] = None
    cycle_detected: Optional[bool] = None
    connected_accounts: Optional[List[str]] = None


class DetectionSignals(BaseModel):
    """
    Optional signals from the (not-yet-built) detection module. When present,
    rules.py should prefer these over its own internal approximations, since
    a dedicated detection engine has access to more than one account's data
    at a time and can confirm patterns this module can only approximate.
    """

    structuring_detected: Optional[bool] = None
    layering_detected: Optional[bool] = None
    circular_flow_detected: Optional[bool] = None
    mule_behavior_detected: Optional[bool] = None
    shared_device_detected: Optional[bool] = None
    shared_ip_detected: Optional[bool] = None
    crypto_offramping_detected: Optional[bool] = None


class RiskFeatures(BaseModel):
    """Structured output of features.py -- the only thing rules.py is allowed to read."""

    account_id: str
    customer_id: Optional[str] = None
    reference_time: datetime

    # --- Volume / amount (all-time, over whatever history was supplied) ---
    transaction_count: int = 0
    incoming_transaction_count: int = 0
    outgoing_transaction_count: int = 0
    total_incoming_amount: float = 0.0
    total_outgoing_amount: float = 0.0
    average_transaction_amount: float = 0.0
    median_transaction_amount: float = 0.0
    max_transaction_amount: float = 0.0
    min_transaction_amount: float = 0.0

    # --- Velocity / frequency (configurable windows) ---
    transactions_last_1h: int = 0
    transactions_last_24h: int = 0
    incoming_last_1h: int = 0
    outgoing_last_1h: int = 0
    average_seconds_between_transactions: Optional[float] = None
    burst_velocity_score: float = 0.0  # distinct from raw frequency -- see features.py docstring

    # --- Within-window amount anomaly ---
    max_amount_deviation_ratio: float = 0.0

    # --- Structuring-specific ---
    sub_threshold_outgoing_count_24h: int = 0
    sub_threshold_amount_coefficient_of_variation: Optional[float] = None
    sub_threshold_total_amount_24h: float = 0.0

    # --- Pass-through / mule ---
    rapid_forwarding_count: int = 0
    inflow_outflow_ratio: Optional[float] = None  # None if no inflow to compare against

    # --- Network / counterparties (within supplied transaction data) ---
    unique_senders: int = 0
    unique_receivers: int = 0
    unique_counterparties: int = 0
    reciprocal_counterparty_count: int = 0  # 2/3-hop proxy, not graph-confirmed

    # --- Device / IP -- now cross-account, not just "how many did this account use" ---
    distinct_device_count: int = 0
    distinct_ip_count: int = 0
    max_accounts_sharing_a_device: int = 0
    max_accounts_sharing_an_ip: int = 0

    # --- Location ---
    distinct_country_count: int = 0
    location_change_count: int = 0  # chronological transitions on this account's own timeline

    # --- Crypto ---
    crypto_transaction_count: int = 0
    crypto_total_amount: float = 0.0

    # --- Historical baseline (older period) vs current (recent) period ---
    has_sufficient_baseline: bool = False
    baseline_average_amount: Optional[float] = None
    baseline_transactions_per_day: Optional[float] = None
    baseline_unique_beneficiaries: Optional[int] = None
    current_period_average_amount: Optional[float] = None
    current_period_transactions_per_day: Optional[float] = None
    current_period_unique_beneficiaries: Optional[int] = None

    # --- KYC (customer-level, attached here for convenience) ---
    kyc_status: KycStatus = "unknown"

    # --- Optional teammate-supplied signals, passed through for rules.py ---
    graph: Optional[GraphMetrics] = None
    detection: Optional[DetectionSignals] = None


class RuleResult(BaseModel):
    """Output of a single rule evaluation. Never a bare boolean -- always explainable."""

    rule_name: str
    family: str  # which scoring family this belongs to -- see scorer.py
    triggered: bool
    raw_value: Optional[float] = None
    threshold: Optional[float] = None
    contribution: float = 0.0
    severity: Optional[str] = None
    explanation: str
    evidence: Dict = Field(default_factory=dict)


class RiskAssessment(BaseModel):
    """Final output of the risk engine -- what the API layer returns."""

    account_id: str
    risk_score: int
    risk_level: str
    rule_score: float
    ml_anomaly_score: Optional[float] = None
    triggered_rules: List[RuleResult]
    reasons: List[str]
    feature_summary: Dict
    generated_at: datetime