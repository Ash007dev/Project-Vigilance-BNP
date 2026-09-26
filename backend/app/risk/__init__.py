"""Expose the supported risk-scoring tools from one import location.

How it works: re-export the public models and functions. Result: callers do
not depend on internal file names. Example: ``from app.risk import calculate_risk``.
"""
from .config import DEFAULT_THRESHOLDS, RiskThresholds
from .features import (
    build_shared_infrastructure_maps,
    calculate_shared_device_count,
    calculate_shared_ip_count,
    extract_features,
    extract_features_bulk,
)
from .model import (
    FEATURE_NAMES,
    MIN_POPULATION_SIZE,
    AnomalyModel,
    features_to_vector,
    fit_anomaly_model,
    score_anomaly,
)
from .rules import evaluate_rules
from .schemas import (
    CustomerData,
    DetectionSignals,
    GraphMetrics,
    RiskAssessment,
    RiskFeatures,
    RuleResult,
    TransactionInput,
)
from .scorer import calculate_risk, calculate_theoretical_max_rule_score

__all__ = [
    # schemas
    "TransactionInput",
    "CustomerData",
    "GraphMetrics",
    "DetectionSignals",
    "RiskFeatures",
    "RuleResult",
    "RiskAssessment",
    # features
    "extract_features",
    "extract_features_bulk",
    "build_shared_infrastructure_maps",
    "calculate_shared_device_count",
    "calculate_shared_ip_count",
    # rules
    "evaluate_rules",
    # model
    "fit_anomaly_model",
    "score_anomaly",
    "AnomalyModel",
    "features_to_vector",
    "FEATURE_NAMES",
    "MIN_POPULATION_SIZE",
    # scorer
    "calculate_risk",
    "calculate_theoretical_max_rule_score",
    # config
    "RiskThresholds",
    "DEFAULT_THRESHOLDS",
]
