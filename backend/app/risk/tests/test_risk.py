# Target path: backend/app/risk/tests/test_risk.py
"""
Run from `backend/`: pytest app/risk/tests/test_risk.py -v

Covers the Step 11 scenario list: normal/low risk, large transaction, high
frequency, structuring, layering, circular flow, mule behaviour, rapid
forwarding, shared device, shared IP, location changes, incomplete KYC,
crypto activity, multiple beneficiaries, historical deviation, missing
fields, duplicate transactions, boundary thresholds, multiple factors
together -- plus scorer-specific checks (double-counting prevention,
supersession, clamping, determinism) since those are just as load-bearing
as the individual rules.

Tests check that the CORRECT rule triggered based on the data, not that a
fixed score came out -- per the brief's own instruction not to hardcode
expected scores.
"""
from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from app.risk.config import DEFAULT_THRESHOLDS
from app.risk.features import (
    build_shared_infrastructure_maps,
    extract_features,
    extract_features_bulk,
)
from app.risk.rules import evaluate_rules
from app.risk.schemas import CustomerData, GraphMetrics, RiskFeatures, RuleResult, TransactionInput
from app.risk.scorer import _classify, calculate_risk, calculate_theoretical_max_rule_score

BASE_TIME = datetime(2026, 1, 1, tzinfo=timezone.utc)


def tx(
    tid, mins=0, sender="A", receiver="B", amount=1000.0,
    device="D1", ip="1.1.1.1", country="India", is_crypto=False, crypto_wallet=None,
):
    return TransactionInput(
        transaction_id=tid,
        timestamp=BASE_TIME + timedelta(minutes=mins),
        sender_account=sender,
        receiver_account=receiver,
        amount=amount,
        currency="INR",
        channel="UPI",
        ip_address=ip,
        device_id=device,
        location_country=country,
        location_city="City",
        is_crypto=is_crypto,
        crypto_wallet=crypto_wallet,
    )


def pipeline(account_id, transactions, **feature_kwargs):
    features = extract_features(account_id, transactions, **feature_kwargs)
    rule_results = evaluate_rules(features)
    assessment = calculate_risk(features, rule_results, ml_anomaly_score=None)
    return features, rule_results, assessment


def rule(rule_results, name):
    return next(r for r in rule_results if r.rule_name == name)


# ============================================================
# 1. Normal account -> low risk
# ============================================================
def test_normal_account_is_low_risk():
    txs = [tx("T1", 0, amount=500), tx("T2", 60, amount=600)]
    _, _, assessment = pipeline("A", txs)
    assert assessment.risk_level == "Low"
    assert assessment.risk_score <= DEFAULT_THRESHOLDS.low_max


# ============================================================
# 2. Large transaction
# ============================================================
def test_large_transaction_triggers():
    txs = [tx("T1", 0, amount=2_000_000)]
    _, rules, _ = pipeline("A", txs)
    assert rule(rules, "large_transaction").triggered


def test_large_transaction_below_threshold_does_not_trigger():
    txs = [tx("T1", 0, amount=500)]
    _, rules, _ = pipeline("A", txs)
    assert not rule(rules, "large_transaction").triggered


# ============================================================
# 3. High transaction frequency
# ============================================================
def test_high_frequency_triggers():
    txs = [tx(f"T{i}", i) for i in range(25)]  # 25 in the last hour, threshold is 20
    _, rules, _ = pipeline("A", txs)
    assert rule(rules, "high_frequency").triggered


def test_high_frequency_below_threshold_does_not_trigger():
    txs = [tx(f"T{i}", i) for i in range(5)]
    _, rules, _ = pipeline("A", txs)
    assert not rule(rules, "high_frequency").triggered


# ============================================================
# 4. Structuring
# ============================================================
def test_structuring_triggers_with_similar_amounts():
    txs = [tx(f"T{i}", i * 10, amount=50_000 + i * 10) for i in range(6)]
    _, rules, _ = pipeline("A", txs)
    r = rule(rules, "structuring")
    assert r.triggered
    assert r.evidence["amounts_repeatedly_similar"] is True


def test_structuring_does_not_trigger_below_min_count():
    txs = [tx(f"T{i}", i * 10, amount=50_000) for i in range(4)]  # min_count is 5
    _, rules, _ = pipeline("A", txs)
    assert not rule(rules, "structuring").triggered


# ============================================================
# 5. Layering
# ============================================================
def test_layering_unknown_without_graph_data():
    _, rules, _ = pipeline("A", [tx("T1")], graph_metrics=None)
    r = rule(rules, "layering")
    assert not r.triggered
    assert "requires graph-module input" in r.explanation


def test_layering_triggers_with_graph_depth():
    gm = GraphMetrics(graph_depth=6)
    _, rules, _ = pipeline("A", [tx("T1")], graph_metrics=gm)
    assert rule(rules, "layering").triggered


def test_layering_prefers_detection_module_over_graph_depth():
    from app.risk.schemas import DetectionSignals
    gm = GraphMetrics(graph_depth=1)  # would NOT trigger on its own
    ds = DetectionSignals(layering_detected=True)  # but detection confirms it
    _, rules, _ = pipeline("A", [tx("T1")], graph_metrics=gm, detection_signals=ds)
    assert rule(rules, "layering").triggered


# ============================================================
# 6. Circular flow
# ============================================================
def test_circular_flow_via_graph_cycle():
    gm = GraphMetrics(cycle_detected=True)
    _, rules, _ = pipeline("A", [tx("T1")], graph_metrics=gm)
    assert rule(rules, "circular_flow").triggered


def test_circular_flow_via_reciprocal_counterparty_fallback():
    txs = [
        tx("T1", 0, sender="A", receiver="X", amount=1000),
        tx("T2", 5, sender="X", receiver="A", amount=900),
    ]
    _, rules, _ = pipeline("A", txs)
    assert rule(rules, "circular_flow").triggered


# ============================================================
# 7. Mule behaviour
# ============================================================
def test_mule_behavior_triggers():
    txs = []
    for i in range(6):
        txs.append(tx(f"IN{i}", i, sender=f"SRC{i}", receiver="MULE", amount=10_000))
        txs.append(tx(f"OUT{i}", i + 1, sender="MULE", receiver="DEST", amount=9_500))
    _, rules, assessment = pipeline("MULE", txs)
    assert rule(rules, "mule_behavior").triggered
    assert assessment.risk_level in ("Medium", "High", "Critical")


def test_mule_behavior_requires_all_three_conditions():
    # many senders, but NOT forwarded quickly -- should not trigger mule
    txs = [tx(f"IN{i}", i * 10_000, sender=f"SRC{i}", receiver="ACC", amount=10_000) for i in range(6)]
    _, rules, _ = pipeline("ACC", txs)
    assert not rule(rules, "mule_behavior").triggered


# ============================================================
# 8. Rapid forwarding
# ============================================================
def test_rapid_forwarding_triggers():
    txs = [
        tx("IN1", 0, sender="X", receiver="A", amount=10_000),
        tx("OUT1", 5, sender="A", receiver="Y", amount=9_000),
    ]
    _, rules, _ = pipeline("A", txs)
    assert rule(rules, "rapid_forwarding").triggered


def test_rapid_forwarding_does_not_trigger_when_outgoing_too_small():
    txs = [
        tx("IN1", 0, sender="X", receiver="A", amount=10_000),
        tx("OUT1", 5, sender="A", receiver="Y", amount=100),  # far below the 80% ratio
    ]
    _, rules, _ = pipeline("A", txs)
    assert not rule(rules, "rapid_forwarding").triggered


# ============================================================
# 9 & 10. Shared device / shared IP (genuinely cross-account)
# ============================================================
def test_shared_device_and_ip_trigger_cross_account():
    shared_txs = [
        tx("T1", 0, sender="A", receiver="X", device="DEV-1", ip="1.1.1.1"),
        tx("T2", 10, sender="B", receiver="Y", device="DEV-1", ip="1.1.1.1"),
    ]
    dmap, imap = build_shared_infrastructure_maps(shared_txs)
    _, rules, _ = pipeline("A", shared_txs, device_to_accounts=dmap, ip_to_accounts=imap)
    assert rule(rules, "shared_device").triggered
    assert rule(rules, "shared_ip").triggered


def test_shared_device_does_not_trigger_for_receiver():
    shared_txs = [
        tx("T1", 0, sender="A", receiver="X", device="DEV-1"),
        tx("T2", 10, sender="B", receiver="Y", device="DEV-1"),
    ]
    dmap, imap = build_shared_infrastructure_maps(shared_txs)
    _, rules, _ = pipeline("X", shared_txs, device_to_accounts=dmap, ip_to_accounts=imap)
    assert not rule(rules, "shared_device").triggered  # X only received, never sent from a device


def test_shared_device_without_map_defaults_to_not_triggered():
    shared_txs = [
        tx("T1", 0, sender="A", receiver="X", device="DEV-1"),
        tx("T2", 10, sender="B", receiver="Y", device="DEV-1"),
    ]
    _, rules, _ = pipeline("A", shared_txs)  # no map passed
    assert not rule(rules, "shared_device").triggered


# ============================================================
# 11. Location changes
# ============================================================
def test_location_change_triggers():
    txs = [
        tx("T1", 0, sender="A", receiver="X", country="India"),
        tx("T2", 60, sender="A", receiver="Y", country="UAE"),
        tx("T3", 120, sender="A", receiver="Z", country="Singapore"),
    ]
    _, rules, _ = pipeline("A", txs)
    assert rule(rules, "location_change").triggered


def test_no_location_change_when_country_is_constant():
    txs = [tx("T1", 0, sender="A", country="India"), tx("T2", 60, sender="A", country="India")]
    _, rules, _ = pipeline("A", txs)
    assert not rule(rules, "location_change").triggered


# ============================================================
# 12. Incomplete KYC
# ============================================================
@pytest.mark.parametrize("status,expect_triggered", [
    ("complete", False), ("pending", True), ("incomplete", True), ("unknown", True),
])
def test_kyc_risk_by_status(status, expect_triggered):
    customer = CustomerData(customer_id="C1", kyc_status=status)
    _, rules, _ = pipeline("A", [tx("T1", 0)], customer_data=customer)
    assert rule(rules, "kyc_risk").triggered == expect_triggered


def test_kyc_defaults_to_unknown_without_customer_data():
    features, rules, _ = pipeline("A", [tx("T1", 0)])  # no customer_data passed
    assert features.kyc_status == "unknown"
    assert rule(rules, "kyc_risk").triggered  # unknown carries a non-zero contribution by default


# ============================================================
# 13. Crypto activity
# ============================================================
def test_crypto_offramp_triggers():
    txs = [tx("T1", is_crypto=True, crypto_wallet="0xABC", amount=5000)]
    _, rules, _ = pipeline("A", txs)
    assert rule(rules, "crypto_offramp").triggered


def test_no_crypto_does_not_trigger():
    txs = [tx("T1", amount=5000)]
    _, rules, _ = pipeline("A", txs)
    assert not rule(rules, "crypto_offramp").triggered


# ============================================================
# 14. Multiple beneficiaries
# ============================================================
def test_multiple_beneficiaries_triggers():
    txs = [tx(f"T{i}", i, sender="A", receiver=f"BEN{i}") for i in range(12)]
    _, rules, _ = pipeline("A", txs)
    assert rule(rules, "multiple_beneficiaries").triggered


def test_multiple_beneficiaries_below_threshold_does_not_trigger():
    txs = [tx(f"T{i}", i, sender="A", receiver=f"BEN{i}") for i in range(3)]
    _, rules, _ = pipeline("A", txs)
    assert not rule(rules, "multiple_beneficiaries").triggered


# ============================================================
# 15. Historical behaviour deviation
# ============================================================
def test_historical_deviation_insufficient_baseline():
    _, rules, _ = pipeline("A", [tx("T1", 0)])
    r = rule(rules, "historical_deviation")
    assert not r.triggered
    assert "cannot be evaluated" in r.explanation


def test_historical_deviation_triggers_on_sufficient_data():
    baseline = [tx(f"OLD{i}", -60 * 24 * 10 + i * 100, sender="A", receiver=f"R{i}", amount=1000) for i in range(10)]
    current = [tx(f"NEW{i}", -60 * 24 * 1 + i * 100, sender="A", receiver=f"R{i}", amount=8000) for i in range(3)]
    ref_time = pd.Timestamp(BASE_TIME)
    _, rules, _ = pipeline("A", baseline + current, reference_time=ref_time)
    r = rule(rules, "historical_deviation")
    assert r.triggered  # current avg (8000) is 8x baseline avg (1000), threshold is 2.5x


def test_historical_deviation_does_not_trigger_on_consistent_behaviour():
    baseline = [tx(f"OLD{i}", -60 * 24 * 10 + i * 100, sender="A", receiver=f"R{i}", amount=1000) for i in range(10)]
    current = [tx(f"NEW{i}", -60 * 24 * 1 + i * 100, sender="A", receiver=f"R{i}", amount=1100) for i in range(3)]
    ref_time = pd.Timestamp(BASE_TIME)
    _, rules, _ = pipeline("A", baseline + current, reference_time=ref_time)
    assert not rule(rules, "historical_deviation").triggered


# ============================================================
# 16. Missing fields
# ============================================================
def test_missing_optional_fields_does_not_crash():
    txn = TransactionInput(
        transaction_id="T1", timestamp=BASE_TIME, sender_account="A", receiver_account=None,
        amount=1000.0, currency=None, channel=None, ip_address=None, device_id=None,
        location_country=None, location_city=None, is_crypto=False, crypto_wallet=None,
    )
    features, _, assessment = pipeline("A", [txn])
    assert features.transaction_count == 1
    assert assessment.risk_score >= 0


def test_missing_customer_data_defaults_safely():
    features, _, _ = pipeline("A", [tx("T1", 0)], customer_data=None)
    assert features.kyc_status == "unknown"
    assert features.customer_id is None


# ============================================================
# 17. Duplicate transactions
# ============================================================
def test_duplicate_transaction_id_counted_once():
    txs = [tx("DUP", 0, amount=1000), tx("DUP", 0, amount=1000)]  # same transaction_id
    features, _, _ = pipeline("A", txs)
    assert features.transaction_count == 1


# ============================================================
# 18. Boundary thresholds
# ============================================================
@pytest.mark.parametrize("score,expected_level", [
    (0, "Low"), (30, "Low"), (31, "Medium"), (60, "Medium"),
    (61, "High"), (80, "High"), (81, "Critical"), (100, "Critical"),
])
def test_risk_level_boundaries(score, expected_level):
    assert _classify(score, DEFAULT_THRESHOLDS) == expected_level


def test_negative_amount_rejected_at_boundary():
    with pytest.raises(ValueError):
        tx("T1", amount=-500)


# ============================================================
# 19. Multiple risk factors together (+ scorer-specific checks)
# ============================================================
def test_multiple_factors_trigger_together():
    txs = [tx(f"S{i}", 10 * i, amount=50_000) for i in range(6)]  # 0-50 min: structuring
    txs.append(tx("BIG", 60, amount=2_000_000))  # 60 min: large transaction
    txs += [tx(f"V{i}", 70 + i, amount=1000) for i in range(25)]  # 70-94 min: velocity, adjacent to reference_time
    _, rules, assessment = pipeline("A", txs)
    triggered_names = {r.rule_name for r in rules if r.triggered}
    assert {"high_frequency", "structuring", "large_transaction"} <= triggered_names
    # NOTE: deliberately not asserting a score band here. With current default
    # weights, these three rules together land at exactly 30 (Low) -- a real
    # calibration finding (see chat), not something to paper over by asserting
    # a threshold that happens to pass. If you retune config.py weights, this
    # test still checks the right thing: that the right rules fired.


def test_double_counting_prevented_for_amount_anomaly_family():
    txs = [tx(f"S{i}", i * 10, amount=500) for i in range(5)] + [tx("BIG", 100, amount=5_000_000)]
    features, rules, assessment = pipeline("A", txs)
    large = next(r for r in assessment.triggered_rules if r.rule_name == "large_transaction")
    deviation = next(r for r in assessment.triggered_rules if r.rule_name == "amount_deviation")
    assert large.triggered and deviation.triggered
    zeroed = [r for r in (large, deviation) if r.contribution == 0]
    assert len(zeroed) == 1, "exactly one of large_transaction/amount_deviation must be de-duplicated"


def test_mule_supersedes_multiple_senders():
    txs = []
    for i in range(12):
        txs.append(tx(f"IN{i}", i, sender=f"SRC{i}", receiver="MULE", amount=10_000))
        txs.append(tx(f"OUT{i}", i + 1, sender="MULE", receiver="DEST", amount=9_500))
    _, _, assessment = pipeline("MULE", txs)
    mule = next(r for r in assessment.triggered_rules if r.rule_name == "mule_behavior")
    senders = next(r for r in assessment.triggered_rules if r.rule_name == "multiple_senders")
    assert mule.contribution > 0
    assert senders.contribution == 0
    assert "superseded" in senders.evidence.get("note", "")


def test_mule_wins_over_rapid_forwarding_despite_lower_flat_weight():
    # rapid_forwarding's contribution scales with count and can numerically
    # exceed mule_behavior's flat weight -- mule must still win (see scorer.py).
    txs = []
    for i in range(12):
        txs.append(tx(f"IN{i}", i, sender=f"SRC{i}", receiver="MULE", amount=10_000))
        txs.append(tx(f"OUT{i}", i + 1, sender="MULE", receiver="DEST", amount=9_500))
    _, _, assessment = pipeline("MULE", txs)
    mule = next(r for r in assessment.triggered_rules if r.rule_name == "mule_behavior")
    rapid = next(r for r in assessment.triggered_rules if r.rule_name == "rapid_forwarding")
    assert mule.contribution > 0
    assert rapid.contribution == 0


def test_score_clamped_to_100():
    features = RiskFeatures(account_id="A", reference_time=BASE_TIME)
    huge = [RuleResult(rule_name="fake", family="standalone", triggered=True, contribution=99_999, explanation="test")]
    assessment = calculate_risk(features, huge, ml_anomaly_score=1.0)
    assert assessment.risk_score == 100


def test_score_never_below_zero():
    features = RiskFeatures(account_id="A", reference_time=BASE_TIME)
    assessment = calculate_risk(features, [], ml_anomaly_score=0.0)
    assert assessment.risk_score == 0


def test_scoring_is_deterministic():
    txs = [tx(f"T{i}", i * 10, amount=50_000) for i in range(6)]
    _, r1, a1 = pipeline("A", txs)
    _, r2, a2 = pipeline("A", txs)
    assert a1.risk_score == a2.risk_score
    assert a1.risk_level == a2.risk_level


def test_theoretical_max_is_positive_and_stable():
    m1 = calculate_theoretical_max_rule_score()
    m2 = calculate_theoretical_max_rule_score()
    assert m1 == m2 > 0


def test_bulk_and_single_account_paths_agree():
    txs = [tx(f"T{i}", i, sender="A", receiver=f"R{i}") for i in range(5)]
    bulk = extract_features_bulk(txs)
    dmap, imap = build_shared_infrastructure_maps(txs)
    single = extract_features(
        "A", txs, reference_time=bulk["A"].reference_time,
        device_to_accounts=dmap, ip_to_accounts=imap,
    )
    for field in type(single).model_fields:
        if field in ("graph", "detection"):
            continue
        assert getattr(single, field) == getattr(bulk["A"], field), f"mismatch on {field}"