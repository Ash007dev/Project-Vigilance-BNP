# Target path: backend/app/risk/config.py
"""
Every threshold, window, and weight the risk engine uses lives here.
If a number is about to appear in features.py/rules.py/scorer.py, it belongs
here instead, referenced by name.
"""
from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class RiskThresholds:
    # --- Risk level boundaries (upper bound inclusive) ---
    low_max: int = 30
    medium_max: int = 60
    high_max: int = 80
    max_score: int = 100
    min_score: int = 0

    # --- Structuring / smurfing ---
    structuring_amount_threshold: float = 1_000_000.0
    structuring_min_count: int = 5
    structuring_window_hours: int = 24
    structuring_max_coefficient_of_variation: float = 0.25  # "repeated similar amounts"

    # --- Velocity / frequency ---
    high_frequency_tx_per_hour: int = 20
    high_frequency_tx_per_24h: int = 60
    velocity_window_1h_hours: int = 1
    velocity_window_24h_hours: int = 24
    burst_velocity_threshold: float = 0.5  # see features.py: 1 / avg_seconds_between_tx, normalized

    # --- Layering / circular flow (graph-dependent, with internal fallback) ---
    layering_min_hops: int = 5
    circular_flow_min_reciprocal_counterparties: int = 1

    # --- Mule behaviour ---
    mule_min_unique_senders: int = 5
    mule_inflow_outflow_ratio_min: float = 0.8  # forwarded >= 80% of received

    # --- Rapid forwarding ---
    rapid_forwarding_window_minutes: int = 30
    rapid_forwarding_amount_ratio: float = 0.8

    # --- Shared device / IP -- now cross-account thresholds ---
    shared_device_min_accounts: int = 2
    shared_ip_min_accounts: int = 2

    # --- Location ---
    location_change_window_hours: int = 24
    location_change_min_count: int = 2

    # --- High-risk geography: empty by default, filled by compliance config ---
    # Maps country name/code -> severity contribution (0-100 scale, pre-weighting)
    high_risk_geography: Dict[str, float] = field(default_factory=dict)

    # --- KYC contribution by status (0-100 scale, pre-weighting) ---
    kyc_contribution: Dict[str, float] = field(default_factory=lambda: {
        "complete": 0.0,
        "pending": 10.0,
        "incomplete": 25.0,
        "unknown": 15.0,
    })

    # --- Multiple beneficiaries / senders ---
    multiple_beneficiaries_min_count: int = 10
    multiple_senders_min_count: int = 10

    # --- Large transaction / deviation ---
    large_transaction_amount: float = 1_000_000.0
    large_transaction_percentile: float = 0.95  # data-driven alternative path
    deviation_ratio_threshold: float = 3.0

    # --- Historical baseline split ---
    baseline_window_days: int = 7  # data older than this, relative to reference_time
    current_window_days: int = 7   # data within this, relative to reference_time
    min_baseline_transactions: int = 5  # below this, treat baseline as insufficient
    historical_deviation_ratio_threshold: float = 2.5

    # --- Crypto ---
    crypto_offramp_min_count: int = 1

    # --- Per-rule contribution weights (points on a 0-100 scale, BEFORE family caps) ---
    weights: Dict[str, float] = field(default_factory=lambda: {
        "large_transaction": 20.0,
        "high_frequency": 12.0,
        "high_velocity": 15.0,
        "structuring": 18.0,
        "layering": 20.0,
        "circular_flow": 20.0,
        "mule_behavior": 20.0,
        "rapid_forwarding": 15.0,
        "shared_device": 10.0,
        "shared_ip": 10.0,
        "location_change": 8.0,
        "high_risk_geography": 15.0,
        "kyc_risk": 10.0,
        "multiple_beneficiaries": 8.0,
        "multiple_senders": 8.0,
        "crypto_offramp": 15.0,
        "amount_deviation": 12.0,
        "historical_deviation": 15.0,
        "network_risk": 15.0,
    })

    # --- Family caps: max total contribution from any one family, after summing
    # the rules inside it (families that use "max" combination are naturally
    # capped at their single largest member's weight; these caps matter for
    # the "sum, capped" families). See scorer.py for the family assignment. ---
    family_caps: Dict[str, float] = field(default_factory=lambda: {
        "network_topology": 30.0,   # layering + circular_flow + network_risk
        "identity_infra": 20.0,     # shared_device + shared_ip + location_change
    })

    # --- Rule channel vs ML channel blend ---
    rule_channel_weight: float = 0.7
    ml_channel_weight: float = 0.3


DEFAULT_THRESHOLDS = RiskThresholds()