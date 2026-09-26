"""List and run every AML detector.

How it works: build the transaction graph once, then give each detector the
DataFrame, graph, or both inputs it needs.

Result: one combined list of ``(account, pattern, evidence)`` tuples.

Example: ``run_all_detections(frame)`` runs all registered patterns in order.
"""
from .common import build_transaction_graph
from .structuring import detect_structuring
from .layering import detect_layering
from .circular import detect_circular_flow
from .mule import detect_mule_behavior
from .shared_device import detect_shared_device_ip
from .crypto import detect_crypto_offramp
from .fan_in_out import detect_fan_in_out
from .dormant import detect_dormant_reactivation
from .threshold import detect_threshold_avoidance
from .bridge import detect_bridge_nodes
from .offhours import detect_offhours_anomaly
from .channels import detect_cross_channel_hopping
from .round_trip import detect_round_tripping
from .clustering import detect_behavioral_clustering

PATTERN_FUNCTIONS = {
    "structuring": detect_structuring,
    "layering": detect_layering,
    "circular_flow": detect_circular_flow,
    "mule_behavior": detect_mule_behavior,
    "shared_device_ip": detect_shared_device_ip,
    "crypto_offramp": detect_crypto_offramp,
    "fan_in_out": detect_fan_in_out,
    "dormant_reactivation": detect_dormant_reactivation,
    "threshold_avoidance": detect_threshold_avoidance,
    "bridge_nodes": detect_bridge_nodes,
    "offhours_anomaly": detect_offhours_anomaly,
    "cross_channel_hopping": detect_cross_channel_hopping,
    "round_tripping": detect_round_tripping,
    "behavioral_clustering": detect_behavioral_clustering,
}


GRAPH_PATTERNS = {
    "fan_in_out",
    "bridge_nodes",
    "round_tripping",
}


def run_all_detections(df):
    """Run all registered detectors and return their combined findings."""
    graph = build_transaction_graph(df)
    results = []
    for pattern, detector in PATTERN_FUNCTIONS.items():
        if pattern == "mule_behavior":
            findings = detector(df, graph)
        elif pattern in GRAPH_PATTERNS:
            findings = detector(graph)
        else:
            findings = detector(df)
        results.extend(findings)
    return results
