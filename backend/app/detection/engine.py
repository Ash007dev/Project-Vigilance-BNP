"""Connect database transactions to the detector registry.

What: Provides the API-facing detection engine.
How: Loads one DataFrame, runs the shared registry, and formats its findings.
Result: API, alert, investigation, and risk routes use the same 14 detectors.
Example: ``AMLDetectionEngine(frame).run_all()`` runs without a database.
"""

from __future__ import annotations

import pandas as pd

from app.db.database import engine
from app.detection.registry import PATTERN_FUNCTIONS, run_all_detections


API_PATTERN_NAMES = {
    "structuring": "STRUCTURING",
    "mule_behavior": "MULE_ACCOUNT",
    "layering": "LAYERING",
    "circular_flow": "CIRCULAR_FLOW",
    "shared_device_ip": "SHARED_DEVICE",
    "crypto_offramp": "CRYPTO_ACTIVITY",
    "fan_in_out": "FAN_IN_OUT",
    "dormant_reactivation": "DORMANT_REACTIVATION",
    "threshold_avoidance": "THRESHOLD_AVOIDANCE",
    "bridge_nodes": "BRIDGE_NODES",
    "offhours_anomaly": "OFFHOURS_ANOMALY",
    "cross_channel_hopping": "CROSS_CHANNEL_HOPPING",
    "round_tripping": "ROUND_TRIPPING",
    "behavioral_clustering": "BEHAVIORAL_CLUSTERING",
}


class AMLDetectionEngine:
    """Load transactions once and format registry findings for API consumers."""

    def __init__(self, frame: pd.DataFrame | None = None) -> None:
        self.df = frame.copy() if frame is not None else self._load_transactions()

    @staticmethod
    def _load_transactions() -> pd.DataFrame:
        query = """
            SELECT
                transaction_id,
                timestamp,
                sender_account,
                sender_name,
                sender_customer_id,
                receiver_account,
                receiver_name,
                receiver_customer_id,
                amount,
                currency,
                channel,
                ip_address,
                device_id,
                country AS location_country,
                city AS location_city,
                crypto_flag AS is_crypto,
                crypto_wallet
            FROM transactions
            ORDER BY timestamp
        """
        with engine.connect() as connection:
            return pd.read_sql(query, connection)

    def run_all(self) -> dict[str, list[dict]]:
        """Run every registered detector and group findings by pattern."""
        grouped = {pattern: [] for pattern in PATTERN_FUNCTIONS}
        for account, pattern, evidence in run_all_detections(self.df):
            grouped[pattern].append(
                {
                    "account": account,
                    "pattern": API_PATTERN_NAMES[pattern],
                    "reason": f"{pattern.replace('_', ' ').title()} was detected.",
                    "evidence": evidence,
                }
            )
        return grouped
