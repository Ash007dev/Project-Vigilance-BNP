"""Connect transactions, detections, graph metrics, and risk scoring.

How it works: normalize transaction rows, calculate account features, apply
the risk rules, and optionally add an anomaly score. Result: existing API
routes receive their original response shape from the new risk pipeline.
Example: ``RiskEngine(findings, frame).calculate()`` returns ranked accounts.
"""

from __future__ import annotations

from collections import defaultdict
from typing import Any

import pandas as pd

from app.detection.common import build_transaction_graph
from app.risk.config import DEFAULT_THRESHOLDS
from app.risk.features import extract_features_bulk
from app.risk.model import MIN_POPULATION_SIZE, fit_anomaly_model, score_anomaly
from app.risk.rules import evaluate_rules
from app.risk.schemas import DetectionSignals, GraphMetrics, TransactionInput
from app.risk.scorer import calculate_risk


_DIRECT_SIGNAL_FIELDS = {
    "structuring": "structuring_detected",
    "layering": "layering_detected",
    "circular_flow": "circular_flow_detected",
    "mule_behavior": "mule_behavior_detected",
    "crypto_offramp": "crypto_offramping_detected",
}

_PATTERN_ALIASES = {
    "STRUCTURING": "structuring",
    "LAYERING": "layering",
    "CIRCULAR_FLOW": "circular_flow",
    "MULE_ACCOUNT": "mule_behavior",
    "SHARED_DEVICE": "shared_device_ip",
    "SHARED_IP": "shared_device_ip",
    "CRYPTO_ACTIVITY": "crypto_offramp",
}

_DETECTION_ONLY_POINTS = {
    "STRUCTURING": 30,
    "MULE_ACCOUNT": 30,
    "LAYERING": 25,
    "CIRCULAR_FLOW": 35,
    "SHARED_DEVICE": 10,
    "SHARED_IP": 10,
    "CRYPTO_ACTIVITY": 10,
}


def classify_risk(score: int) -> str:
    """Return the uppercase risk level expected by the current frontend."""
    if score <= DEFAULT_THRESHOLDS.low_max:
        return "LOW"
    if score <= DEFAULT_THRESHOLDS.medium_max:
        return "MEDIUM"
    if score <= DEFAULT_THRESHOLDS.high_max:
        return "HIGH"
    return "CRITICAL"


class RiskEngine:
    """Run the complete risk pipeline and keep the existing API contract."""

    def __init__(
        self,
        detection_results: dict[str, list[dict[str, Any]]],
        frame: pd.DataFrame | None = None,
    ) -> None:
        self.detection_results = detection_results
        self.frame = frame.copy() if frame is not None else None

    @staticmethod
    def _value(value: Any) -> Any:
        """Turn Pandas missing values into normal Python ``None`` values."""
        return None if pd.isna(value) else value

    def _transactions(self) -> list[TransactionInput]:
        """Convert DataFrame rows into the risk module's transaction model."""
        if self.frame is None:
            return []
        aliases = {
            "country": "location_country",
            "city": "location_city",
            "crypto_flag": "is_crypto",
        }
        frame = self.frame.rename(
            columns={source: target for source, target in aliases.items() if source in self.frame}
        )
        fields = set(TransactionInput.model_fields)
        transactions = []

        for record in frame.to_dict(orient="records"):
            payload = {
                name: self._value(value)
                for name, value in record.items()
                if name in fields
            }
            if payload.get("transaction_id") is None or payload.get("timestamp") is None:
                continue
            payload["is_crypto"] = bool(payload.get("is_crypto", False))
            transactions.append(TransactionInput.model_validate(payload))

        return transactions

    @staticmethod
    def _account_ids(transactions: list[TransactionInput]) -> list[str]:
        """Return every sender and receiver account once."""
        return sorted(
            {
                account
                for transaction in transactions
                for account in (transaction.sender_account, transaction.receiver_account)
                if account
            }
        )

    @staticmethod
    def _pattern_name(value: str) -> str:
        """Translate API pattern names back to detector registry names."""
        return _PATTERN_ALIASES.get(value, value.lower())

    def _detection_signals(
        self,
        account_ids: list[str],
    ) -> dict[str, DetectionSignals]:
        """Create per-account signals from the completed detector registry."""
        evaluated = {self._pattern_name(name) for name in self.detection_results}
        defaults: dict[str, bool] = {}
        for pattern, field in _DIRECT_SIGNAL_FIELDS.items():
            if pattern in evaluated:
                defaults[field] = False
        if "shared_device_ip" in evaluated:
            defaults["shared_device_detected"] = False
            defaults["shared_ip_detected"] = False

        values_by_account = {account: dict(defaults) for account in account_ids}
        for group_name, findings in self.detection_results.items():
            for finding in findings:
                account = finding.get("account") or finding.get("identifier")
                if account not in values_by_account:
                    continue

                pattern = self._pattern_name(finding.get("pattern", group_name))
                if pattern in _DIRECT_SIGNAL_FIELDS:
                    values_by_account[account][_DIRECT_SIGNAL_FIELDS[pattern]] = True
                    continue

                if pattern == "shared_device_ip":
                    metrics = finding.get("evidence", {}).get("metrics", {})
                    has_device = bool(metrics.get("device_id"))
                    has_ip = bool(metrics.get("ip_address"))
                    values_by_account[account]["shared_device_detected"] = has_device
                    values_by_account[account]["shared_ip_detected"] = has_ip

        return {
            account: DetectionSignals.model_validate(values)
            for account, values in values_by_account.items()
            if values
        }

    def _graph_metrics(
        self,
        account_ids: list[str],
        detection_signals: dict[str, DetectionSignals],
    ) -> dict[str, GraphMetrics]:
        """Calculate simple account connections from the transaction graph."""
        if self.frame is None:
            return {}
        graph = build_transaction_graph(self.frame)
        metrics = {}
        for account in account_ids:
            predecessors = set(graph.predecessors(account)) if account in graph else set()
            successors = set(graph.successors(account)) if account in graph else set()
            connected = sorted(predecessors | successors)
            signals = detection_signals.get(account)
            metrics[account] = GraphMetrics(
                graph_degree=len(connected),
                in_degree=graph.in_degree(account) if account in graph else 0,
                out_degree=graph.out_degree(account) if account in graph else 0,
                unique_counterparties=len(connected),
                cycle_detected=(
                    signals.circular_flow_detected
                    if signals and signals.circular_flow_detected is not None
                    else None
                ),
                connected_accounts=connected,
            )
        return metrics

    def _calculate_from_detections(self) -> list[dict[str, Any]]:
        """Keep findings-only callers working when transaction rows are unavailable."""
        accounts = defaultdict(lambda: {"score": 0, "patterns": [], "reasons": []})
        for findings in self.detection_results.values():
            for finding in findings:
                account = finding.get("account") or finding.get("identifier")
                if not account:
                    continue
                pattern = finding.get("pattern", "UNKNOWN")
                points = _DETECTION_ONLY_POINTS.get(pattern, 0)
                accounts[account]["score"] += points
                if pattern not in accounts[account]["patterns"]:
                    accounts[account]["patterns"].append(pattern)
                accounts[account]["reasons"].append(
                    {
                        "pattern": pattern,
                        "points": points,
                        "reason": finding.get("reason", "Suspicious activity detected."),
                    }
                )

        for data in accounts.values():
            if len(data["patterns"]) >= 2:
                data["score"] += 10
                data["reasons"].append(
                    {
                        "pattern": "MULTIPLE_PATTERNS",
                        "points": 10,
                        "reason": "Multiple independent risk indicators were detected.",
                    }
                )

        results = []
        for account, data in accounts.items():
            score = min(int(data["score"]), 100)
            results.append(
                {
                    "account": account,
                    "risk_score": score,
                    "risk_level": classify_risk(score),
                    "patterns": data["patterns"],
                    "reasons": data["reasons"],
                }
            )
        results.sort(key=lambda item: (-item["risk_score"], item["account"]))
        return results

    def calculate(self) -> list[dict[str, Any]]:
        """Calculate and rank risk for every account in the transaction frame."""
        if self.frame is None:
            return self._calculate_from_detections()

        transactions = self._transactions()
        if not transactions:
            return []

        account_ids = self._account_ids(transactions)
        detection_signals = self._detection_signals(account_ids)
        graph_metrics = self._graph_metrics(account_ids, detection_signals)
        features_by_account = extract_features_bulk(
            transactions,
            graph_metrics_by_account=graph_metrics,
            detection_signals_by_account=detection_signals,
        )

        feature_population = list(features_by_account.values())
        anomaly_model = (
            fit_anomaly_model(feature_population)
            if len(feature_population) >= MIN_POPULATION_SIZE
            else None
        )

        results = []
        for account, features in features_by_account.items():
            anomaly_score = None
            anomaly_evidence: dict[str, Any] = {}
            if anomaly_model is not None:
                anomaly_score, anomaly_evidence = score_anomaly(anomaly_model, features)

            assessment = calculate_risk(
                features,
                evaluate_rules(features),
                ml_anomaly_score=anomaly_score,
            )
            triggered = assessment.triggered_rules
            results.append(
                {
                    "account": account,
                    "risk_score": assessment.risk_score,
                    "risk_level": assessment.risk_level.upper(),
                    "patterns": [rule.rule_name.upper() for rule in triggered],
                    "reasons": [
                        {
                            "pattern": rule.rule_name.upper(),
                            "points": round(rule.contribution, 2),
                            "reason": rule.explanation,
                            "evidence": rule.evidence,
                        }
                        for rule in triggered
                    ],
                    "rule_score": assessment.rule_score,
                    "ml_anomaly_score": assessment.ml_anomaly_score,
                    "ml_evidence": anomaly_evidence,
                    "feature_summary": assessment.feature_summary,
                    "graph_metrics": graph_metrics[account].model_dump(),
                }
            )

        results.sort(key=lambda item: (-item["risk_score"], item["account"]))
        return results
