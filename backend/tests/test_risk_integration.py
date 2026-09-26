from datetime import datetime, timedelta, timezone

import pandas as pd

from app.api import alerts as alerts_api
from app.api import risk as risk_api
from app.risk.engine import RiskEngine


BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def transaction_frame(*rows):
    defaults = {
        "transaction_id": "TX-1",
        "timestamp": BASE_TIME,
        "sender_account": "A",
        "receiver_account": "B",
        "amount": 100.0,
        "currency": "INR",
        "channel": "UPI",
        "sender_customer_id": "CA",
        "receiver_customer_id": "CB",
        "device_id": "D1",
        "ip_address": "10.0.0.1",
        "location_country": "India",
        "location_city": "Bengaluru",
        "is_crypto": False,
        "crypto_wallet": None,
    }
    return pd.DataFrame([{**defaults, **row} for row in rows])


def result_for(scores, account):
    return next(item for item in scores if item["account"] == account)


def test_risk_engine_runs_new_rules_and_keeps_the_dashboard_contract():
    frame = transaction_frame({"amount": 2_000_000.0})

    scores = RiskEngine({}, frame=frame).calculate()
    account = result_for(scores, "A")

    assert "LARGE_TRANSACTION" in account["patterns"]
    assert account["risk_level"] in {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
    assert account["risk_score"] > 0
    assert account["reasons"]
    assert set(account["reasons"][0]) >= {"pattern", "points", "reason"}
    assert account["feature_summary"]["transaction_count"] == 1


def test_risk_engine_passes_detection_and_graph_signals_to_rules():
    frame = transaction_frame({})
    detections = {
        "layering": [
            {
                "account": "A",
                "pattern": "LAYERING",
                "reason": "Layering was detected.",
                "evidence": {},
            }
        ]
    }

    account = result_for(RiskEngine(detections, frame=frame).calculate(), "A")

    assert "LAYERING" in account["patterns"]
    assert account["graph_metrics"]["graph_degree"] == 1
    assert account["graph_metrics"]["connected_accounts"] == ["B"]


def test_findings_only_scoring_keeps_the_multiple_pattern_bonus():
    detections = {
        "structuring": [{"account": "A", "pattern": "STRUCTURING"}],
        "layering": [{"account": "A", "pattern": "LAYERING"}],
    }

    account = result_for(RiskEngine(detections).calculate(), "A")

    assert account["risk_score"] == 65
    assert account["reasons"][-1]["pattern"] == "MULTIPLE_PATTERNS"


def test_risk_engine_adds_population_anomaly_scores_when_enough_accounts_exist():
    rows = []
    for index in range(20):
        rows.append(
            {
                "transaction_id": f"TX-{index}",
                "timestamp": BASE_TIME + timedelta(minutes=index),
                "sender_account": f"A{index}",
                "receiver_account": "HUB",
                "amount": 100.0 + index,
                "device_id": f"D{index}",
                "ip_address": f"10.0.0.{index + 1}",
            }
        )

    scores = RiskEngine({}, frame=transaction_frame(*rows)).calculate()

    assert len(scores) == 21
    assert all(item["ml_anomaly_score"] is not None for item in scores)


def test_risk_api_reuses_detection_rows_for_full_risk_scoring(monkeypatch):
    frame = transaction_frame({"amount": 2_000_000.0})

    class DetectionEngineWithoutDatabase:
        def __init__(self):
            self.df = frame

        def run_all(self):
            return {}

    monkeypatch.setattr(risk_api, "AMLDetectionEngine", DetectionEngineWithoutDatabase)

    response = risk_api.get_risk_scores()
    account = result_for(response["risk_scores"], "A")

    assert "LARGE_TRANSACTION" in account["patterns"]
    assert account["feature_summary"]["transaction_count"] == 1


def test_alert_api_does_not_open_alerts_for_low_risk_accounts(monkeypatch):
    frame = transaction_frame({"amount": 100.0})

    class DetectionEngineWithoutDatabase:
        def __init__(self):
            self.df = frame

        def run_all(self):
            return {}

    monkeypatch.setattr(alerts_api, "AMLDetectionEngine", DetectionEngineWithoutDatabase)

    response = alerts_api.get_alerts()

    assert response["total_alerts"] == 0
    assert response["alerts"] == []
