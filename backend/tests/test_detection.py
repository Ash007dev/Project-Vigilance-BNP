from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone

import networkx as nx
import pandas as pd
import pytest

from backend.app.detection.bridge import detect_bridge_nodes
from backend.app.detection.channels import detect_cross_channel_hopping
from backend.app.detection.circular import detect_circular_flow
from backend.app.detection.clustering import detect_behavioral_clustering
from backend.app.detection.common import (
    _binomial_tail,
    _evidence,
    _frame,
    build_transaction_graph,
)
from backend.app.detection.crypto import detect_crypto_offramp
from backend.app.detection.dormant import detect_dormant_reactivation
from backend.app.detection.fan_in_out import detect_fan_in_out
from backend.app.detection.layering import detect_layering
from backend.app.detection.mule import detect_mule_behavior
from backend.app.detection.offhours import detect_offhours_anomaly
from backend.app.detection.round_trip import detect_round_tripping
from backend.app.detection.shared_device import detect_shared_device_ip
from backend.app.detection.structuring import detect_structuring
from backend.app.detection.threshold import detect_threshold_avoidance


BASE_TIME = datetime(2026, 1, 1, 10, tzinfo=timezone.utc)


def transactions(*rows: dict) -> pd.DataFrame:
    records = []
    for index, changes in enumerate(rows):
        record = {
            "transaction_id": f"TX-{index}",
            "timestamp": BASE_TIME + timedelta(minutes=index),
            "sender_account": f"S-{index}",
            "sender_customer_id": f"SC-{index}",
            "receiver_account": f"R-{index}",
            "receiver_customer_id": f"RC-{index}",
            "amount": 100,
            "currency": "INR",
            "channel": "UPI",
            "ip_address": f"10.0.0.{index + 1}",
            "device_id": f"DEV-{index}",
            "is_crypto": False,
            "crypto_wallet": None,
        }
        record.update(changes)
        records.append(record)
    return pd.DataFrame(records)


def assert_uniform_results(results, pattern: str) -> None:
    for account, result_pattern, evidence in results:
        assert isinstance(account, str) and account
        assert result_pattern == pattern
        assert set(evidence) == {
            "transaction_ids",
            "window_start",
            "window_end",
            "metrics",
            "parameters",
            "limitations",
        }
        json.dumps(evidence)


def test_frame_validates_columns_even_when_dataframe_is_empty():
    with pytest.raises(ValueError, match="Missing required columns"):
        _frame(pd.DataFrame(), ("transaction_id", "timestamp"))


def test_frame_skips_only_rows_with_invalid_timestamps():
    frame = transactions({}, {"timestamp": "not-a-timestamp"})

    records = _frame(frame, ("transaction_id", "timestamp", "amount"))

    assert [row["transaction_id"] for row in records] == ["TX-0"]


def test_frame_skips_only_rows_with_non_positive_amounts():
    frame = transactions({}, {"amount": 0}, {"amount": -10})

    records = _frame(frame, ("transaction_id", "timestamp", "amount"))

    assert [row["transaction_id"] for row in records] == ["TX-0"]


def test_binomial_tail_handles_large_transaction_counts():
    probability = _binomial_tail(20_000, 19_000, 0.1)

    assert 0 <= probability <= 1


def test_evidence_caps_transaction_ids_but_keeps_the_full_time_window():
    frame = transactions(
        *[
            {"timestamp": BASE_TIME + timedelta(minutes=index)}
            for index in range(120)
        ]
    )
    records = _frame(frame, ("transaction_id", "timestamp", "amount"))

    evidence = _evidence(records, {"transaction_count": len(records)})

    assert len(evidence["transaction_ids"]) == 100
    assert evidence["window_start"] == records[0]["timestamp"].isoformat()
    assert evidence["window_end"] == records[-1]["timestamp"].isoformat()


def test_structuring_detects_six_sub_threshold_transfers_in_24_hours():
    frame = transactions(
        *[
            {
                "sender_account": "STRUCTURED",
                "timestamp": BASE_TIME + timedelta(hours=index),
                "amount": 99_000,
            }
            for index in range(6)
        ]
    )

    results = detect_structuring(frame)

    assert [result[0] for result in results] == ["STRUCTURED"]
    assert_uniform_results(results, "structuring")


def test_structuring_ignores_low_value_routine_activity():
    frame = transactions(
        *[
            {
                "sender_account": "ROUTINE",
                "timestamp": BASE_TIME + timedelta(hours=index),
                "amount": 10_000,
            }
            for index in range(6)
        ]
    )

    assert detect_structuring(frame) == []


def test_layering_requires_a_connected_transaction_chain():
    disconnected = transactions(
        *[
            {
                "sender_account": f"SENDER-{index}",
                "receiver_account": f"RECEIVER-{index}",
                "timestamp": BASE_TIME + timedelta(minutes=index),
            }
            for index in range(5)
        ]
    )

    assert detect_layering(disconnected, min_accounts=5) == []


def test_layering_detects_a_fast_connected_chain():
    frame = transactions(
        {"sender_account": "A", "receiver_account": "B"},
        {"sender_account": "B", "receiver_account": "C"},
        {"sender_account": "C", "receiver_account": "D"},
        {"sender_account": "D", "receiver_account": "E"},
    )

    results = detect_layering(frame, min_accounts=5)

    assert {result[0] for result in results} == {"A", "B", "C", "D", "E"}
    assert_uniform_results(results, "layering")


def test_layering_requires_more_than_one_transfer_hop():
    frame = transactions(
        *[
            {"sender_account": "A", "receiver_account": f"TARGET-{index}"}
            for index in range(5)
        ]
    )

    assert detect_layering(frame, min_accounts=5) == []


def test_layering_ignores_one_off_links_in_a_large_graph():
    frame = transactions(
        *[
            {
                "sender_account": f"ACCOUNT-{index}",
                "receiver_account": f"ACCOUNT-{index + 1}",
                "amount": 1_000 + index * 100,
            }
            for index in range(120)
        ]
    )

    assert detect_layering(frame, min_accounts=5) == []


def test_circular_flow_detects_a_three_account_cycle():
    frame = transactions(
        {"sender_account": "A", "receiver_account": "B"},
        {"sender_account": "B", "receiver_account": "C"},
        {"sender_account": "C", "receiver_account": "A"},
    )

    results = detect_circular_flow(frame)

    assert {result[0] for result in results} == {"A", "B", "C"}
    assert_uniform_results(results, "circular_flow")


def test_circular_flow_does_not_join_different_currencies():
    frame = transactions(
        {"sender_account": "A", "receiver_account": "B", "currency": "INR"},
        {"sender_account": "B", "receiver_account": "C", "currency": "INR"},
        {"sender_account": "C", "receiver_account": "A", "currency": "USDT"},
    )

    assert detect_circular_flow(frame) == []


def test_circular_flow_stays_bounded_on_a_large_graph():
    rows = [
        {
            "sender_account": f"UNRELATED-{index}",
            "receiver_account": f"UNRELATED-{index + 1}",
            "timestamp": BASE_TIME + timedelta(seconds=index),
        }
        for index in range(120)
    ]
    for repeat in range(10):
        start = BASE_TIME + timedelta(minutes=10 + repeat * 3)
        rows.extend(
            [
                {"sender_account": "A", "receiver_account": "B", "timestamp": start},
                {
                    "sender_account": "B",
                    "receiver_account": "C",
                    "timestamp": start + timedelta(minutes=1),
                },
                {
                    "sender_account": "C",
                    "receiver_account": "A",
                    "timestamp": start + timedelta(minutes=2),
                },
            ]
        )

    results = detect_circular_flow(transactions(*rows), max_expansions=1)

    assert {result[0] for result in results} == {"A", "B", "C"}


def test_mule_behavior_detects_two_large_inflows_quickly_forwarded():
    frame = transactions(
        {"sender_account": "SOURCE-1", "receiver_account": "MULE", "amount": 1_200_000},
        {
            "sender_account": "MULE",
            "receiver_account": "TARGET-1",
            "amount": 700_000,
            "timestamp": BASE_TIME + timedelta(minutes=10),
        },
        {
            "sender_account": "SOURCE-2",
            "receiver_account": "MULE",
            "amount": 1_100_000,
            "timestamp": BASE_TIME + timedelta(hours=1),
        },
        {
            "sender_account": "MULE",
            "receiver_account": "TARGET-2",
            "amount": 600_000,
            "timestamp": BASE_TIME + timedelta(hours=1, minutes=10),
        },
    )
    graph = build_transaction_graph(frame)

    results = detect_mule_behavior(frame, graph)

    assert [result[0] for result in results] == ["MULE"]
    assert_uniform_results(results, "mule_behavior")


def test_mule_behavior_detects_dataset_sized_rapid_forwarding():
    frame = transactions(
        {"sender_account": "SOURCE-1", "receiver_account": "MULE", "amount": 200_000},
        {
            "sender_account": "MULE",
            "receiver_account": "TARGET",
            "amount": 190_000,
            "timestamp": BASE_TIME + timedelta(minutes=5),
        },
        {
            "sender_account": "SOURCE-2",
            "receiver_account": "MULE",
            "amount": 250_000,
            "timestamp": BASE_TIME + timedelta(hours=1),
        },
        {
            "sender_account": "MULE",
            "receiver_account": "TARGET",
            "amount": 240_000,
            "timestamp": BASE_TIME + timedelta(hours=1, minutes=5),
        },
    )

    results = detect_mule_behavior(frame, build_transaction_graph(frame))

    assert [result[0] for result in results] == ["MULE"]


def test_shared_device_detects_more_than_three_customers():
    frame = transactions(
        *[
            {
                "sender_account": f"ACCOUNT-{index}",
                "sender_customer_id": f"CUSTOMER-{index}",
                "device_id": "SHARED-DEVICE",
            }
            for index in range(4)
        ]
    )

    results = detect_shared_device_ip(frame)

    assert {result[0] for result in results} == {
        "ACCOUNT-0",
        "ACCOUNT-1",
        "ACCOUNT-2",
        "ACCOUNT-3",
    }
    assert_uniform_results(results, "shared_device_ip")


def test_crypto_offramp_detects_crypto_after_structuring():
    rows = [
        {
            "sender_account": "CRYPTO-ACCOUNT",
            "timestamp": BASE_TIME + timedelta(hours=index),
            "amount": 900_000,
        }
        for index in range(6)
    ]
    rows.append(
        {
            "sender_account": "CRYPTO-ACCOUNT",
            "timestamp": BASE_TIME + timedelta(hours=7),
            "is_crypto": True,
            "amount": 850_000,
        }
    )

    results = detect_crypto_offramp(transactions(*rows))

    assert [result[0] for result in results] == ["CRYPTO-ACCOUNT"]
    assert_uniform_results(results, "crypto_offramp")


def test_crypto_offramp_requires_a_comparable_recent_amount():
    rows = [
        {
            "sender_account": "CRYPTO-ACCOUNT",
            "timestamp": BASE_TIME + timedelta(hours=index),
            "amount": 900_000,
        }
        for index in range(6)
    ]
    rows.append(
        {
            "sender_account": "CRYPTO-ACCOUNT",
            "timestamp": BASE_TIME + timedelta(hours=7),
            "is_crypto": True,
            "amount": 100,
        }
    )

    assert detect_crypto_offramp(transactions(*rows)) == []


def test_fan_in_out_detects_a_collection_hub():
    frame = transactions(
        {"sender_account": "A", "receiver_account": "HUB"},
        {"sender_account": "B", "receiver_account": "HUB"},
        {"sender_account": "C", "receiver_account": "HUB"},
        {"sender_account": "D", "receiver_account": "E"},
    )

    results = detect_fan_in_out(build_transaction_graph(frame), percentile=75)

    assert "HUB" in {result[0] for result in results}
    assert_uniform_results(results, "fan_in_out")


def test_fan_in_out_requires_multiple_counterparties():
    frame = transactions(
        {"sender_account": "A", "receiver_account": "HUB"},
        {"sender_account": "A", "receiver_account": "HUB"},
        {"sender_account": "A", "receiver_account": "HUB"},
    )

    assert detect_fan_in_out(build_transaction_graph(frame), percentile=50) == []


def test_dormant_reactivation_detects_large_transfer_after_90_days():
    frame = transactions(
        {"sender_account": "DORMANT", "amount": 100},
        {
            "sender_account": "DORMANT",
            "amount": 1_000,
            "timestamp": BASE_TIME + timedelta(days=100),
        },
    )

    results = detect_dormant_reactivation(frame)

    assert "DORMANT" in {result[0] for result in results}
    assert_uniform_results(results, "dormant_reactivation")


def test_threshold_avoidance_uses_the_peer_baseline():
    rows = [
        {"sender_account": "NEAR-LIMIT", "amount": 990_000}
        for _ in range(6)
    ]
    rows.extend(
        {"sender_account": "NORMAL", "amount": 100_000}
        for _ in range(20)
    )

    results = detect_threshold_avoidance(transactions(*rows), alpha=0.05)

    assert [result[0] for result in results] == ["NEAR-LIMIT"]
    assert_uniform_results(results, "threshold_avoidance")


def test_bridge_nodes_detects_the_account_connecting_groups():
    frame = transactions(
        {"sender_account": "A", "receiver_account": "BRIDGE"},
        {"sender_account": "B", "receiver_account": "BRIDGE"},
        {"sender_account": "BRIDGE", "receiver_account": "C"},
        {"sender_account": "BRIDGE", "receiver_account": "D"},
    )

    results = detect_bridge_nodes(build_transaction_graph(frame), percentile=90)

    assert [result[0] for result in results] == ["BRIDGE"]
    assert_uniform_results(results, "bridge_nodes")


def test_offhours_detects_first_night_transaction_after_daytime_history():
    rows = [
        {"sender_account": "NIGHT", "timestamp": BASE_TIME + timedelta(days=index)}
        for index in range(5)
    ]
    rows.append(
        {
            "sender_account": "NIGHT",
            "timestamp": datetime(2026, 1, 7, 3, tzinfo=timezone.utc),
        }
    )

    results = detect_offhours_anomaly(transactions(*rows))

    assert [result[0] for result in results] == ["NIGHT"]
    assert_uniform_results(results, "offhours_anomaly")


def test_cross_channel_hopping_detects_three_channels_in_one_hour():
    frame = transactions(
        {"sender_account": "CHANNEL", "sender_customer_id": "CUSTOMER", "channel": "UPI"},
        {"sender_account": "CHANNEL", "sender_customer_id": "CUSTOMER", "channel": "NEFT"},
        {"sender_account": "CHANNEL", "sender_customer_id": "CUSTOMER", "channel": "RTGS"},
    )

    results = detect_cross_channel_hopping(frame)

    assert [result[0] for result in results] == ["CHANNEL"]
    assert_uniform_results(results, "cross_channel_hopping")


def test_round_tripping_detects_a_quick_return_of_similar_value():
    frame = transactions(
        {"sender_account": "A", "receiver_account": "B", "amount": 1_000},
        {"sender_account": "B", "receiver_account": "A", "amount": 950},
    )

    results = detect_round_tripping(build_transaction_graph(frame))

    assert [result[0] for result in results] == ["A"]
    assert_uniform_results(results, "round_tripping")


def test_round_tripping_stays_bounded_on_a_large_graph():
    rows = [
        {
            "sender_account": f"UNRELATED-{index}",
            "receiver_account": f"UNRELATED-{index + 1}",
        }
        for index in range(120)
    ]
    for repeat in range(10):
        start = BASE_TIME + timedelta(days=repeat * 2, minutes=10)
        rows.extend(
            [
                {
                    "sender_account": "A",
                    "receiver_account": "B",
                    "amount": 1_000,
                    "timestamp": start,
                },
                {
                    "sender_account": "B",
                    "receiver_account": "A",
                    "amount": 950,
                    "timestamp": start + timedelta(minutes=1),
                },
            ]
        )

    results = detect_round_tripping(
        build_transaction_graph(transactions(*rows)), max_expansions=1
    )

    assert [result[0] for result in results] == ["A"]


def test_behavioral_clustering_detects_a_small_identical_group():
    rows = []
    for account in ("CLUSTER-A", "CLUSTER-B"):
        rows.extend(
            [
                {"sender_account": account, "amount": 100, "timestamp": BASE_TIME},
                {
                    "sender_account": account,
                    "amount": 100,
                    "timestamp": BASE_TIME + timedelta(hours=1),
                },
            ]
        )
    for index, account in enumerate(("C", "D", "E", "F", "G", "H"), start=3):
        rows.extend(
            {
                "sender_account": account,
                "amount": index * 1_000 + event,
                "timestamp": BASE_TIME + timedelta(hours=index, minutes=event),
                "channel": f"CHANNEL-{event % index}",
            }
            for event in range(index)
        )

    results = detect_behavioral_clustering(
        transactions(*rows), eps=0.01, min_samples=2, max_cluster_fraction=0.25
    )

    assert {result[0] for result in results} == {"CLUSTER-A", "CLUSTER-B"}
    assert_uniform_results(results, "behavioral_clustering")


def test_registry_runner_handles_a_normal_transaction_without_alerts():
    from backend.app.detection.registry import run_all_detections

    assert run_all_detections(transactions({})) == []


def test_registry_runner_rejects_missing_required_columns():
    from backend.app.detection.registry import run_all_detections

    with pytest.raises(ValueError, match="Missing required columns"):
        run_all_detections(pd.DataFrame([{"transaction_id": "TX-1"}]))


def test_database_engine_adapter_uses_the_registered_detectors():
    from app.detection.engine import AMLDetectionEngine
    from app.risk.engine import RiskEngine
    from backend.app.detection.registry import PATTERN_FUNCTIONS

    frame = transactions(
        *[
            {
                "sender_account": "STRUCTURED",
                "timestamp": BASE_TIME + timedelta(hours=index),
                "amount": 99_000,
            }
            for index in range(6)
        ]
    )

    results = AMLDetectionEngine(frame).run_all()

    assert set(results) == set(PATTERN_FUNCTIONS)
    assert results["structuring"][0]["account"] == "STRUCTURED"
    assert results["structuring"][0]["pattern"] == "STRUCTURING"
    assert results["structuring"][0]["evidence"]["transaction_ids"]
    risk = RiskEngine(results).calculate()[0]
    assert risk["risk_score"] >= 30
    assert "STRUCTURING" in risk["patterns"]


@pytest.mark.parametrize(
    "detector,arguments",
    [
        (detect_structuring, (transactions({}),)),
        (detect_layering, (transactions({}),)),
        (detect_circular_flow, (transactions({}),)),
        (detect_mule_behavior, (transactions({}), nx.MultiDiGraph())),
        (detect_shared_device_ip, (transactions({}),)),
        (detect_crypto_offramp, (transactions({}),)),
        (detect_fan_in_out, (nx.MultiDiGraph(),)),
        (detect_dormant_reactivation, (transactions({}),)),
        (detect_threshold_avoidance, (transactions({}),)),
        (detect_bridge_nodes, (nx.MultiDiGraph(),)),
        (detect_offhours_anomaly, (transactions({}),)),
        (detect_cross_channel_hopping, (transactions({}),)),
        (detect_round_tripping, (nx.MultiDiGraph(),)),
        (detect_behavioral_clustering, (transactions({}),)),
    ],
)
def test_normal_inputs_do_not_raise(detector, arguments):
    results = detector(*arguments)

    assert isinstance(results, list)


@pytest.mark.parametrize(
    "detector",
    [
        detect_structuring,
        detect_layering,
        detect_circular_flow,
        detect_shared_device_ip,
        detect_crypto_offramp,
        detect_dormant_reactivation,
        detect_threshold_avoidance,
        detect_offhours_anomaly,
        detect_cross_channel_hopping,
        detect_behavioral_clustering,
    ],
)
def test_dataframe_detector_rejects_missing_columns(detector):
    with pytest.raises(ValueError, match="Missing required columns"):
        detector(pd.DataFrame([{"transaction_id": "TX-1"}]))


def test_mule_detector_rejects_missing_columns():
    valid = transactions({})

    with pytest.raises(ValueError, match="Missing required columns"):
        detect_mule_behavior(
            pd.DataFrame([{"transaction_id": "TX-1"}]),
            build_transaction_graph(valid),
        )


@pytest.mark.parametrize(
    "detector", [detect_fan_in_out, detect_bridge_nodes, detect_round_tripping]
)
def test_graph_detector_rejects_edges_without_transaction_evidence(detector):
    graph = nx.DiGraph()
    graph.add_edge("A", "B")

    with pytest.raises(ValueError, match="Graph edge missing required"):
        detector(graph)
