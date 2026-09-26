"""Independent AML indicator: detect_offhours_anomaly. Returns uniform (account_id, pattern, evidence) tuples."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from zoneinfo import ZoneInfo
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from .common import _evidence, _frame, _id, _results


def detect_offhours_anomaly(df: pd.DataFrame, local_timezone="UTC", start_hour=2, end_hour=5,
                            min_history=5):
    """Spot 02:00-05:00 local sender activity after at least five earlier normal-hour transfers."""
    records = _frame(df, ("transaction_id", "timestamp", "sender_account"))
    zone = ZoneInfo(local_timezone)
    groups = defaultdict(list)
    for row in records:
        if _id(row["sender_account"]):
            groups[_id(row["sender_account"])].append(row)
    found = {}
    for account, group in groups.items():
        group.sort(key=lambda r: r["timestamp"])
        for i in range(min_history, len(group)):
            past, new = group[:i], group[i]
            hour = new["timestamp"].tz_convert(zone).hour
            if start_hour <= hour < end_hour and all(not start_hour <= r["timestamp"].tz_convert(zone).hour < end_hour for r in past):
                found[account] = _evidence(past + [new], {"new_hour": hour, "prior_count": i,
                                                        "prior_hours": sorted({r["timestamp"].tz_convert(zone).hour for r in past})},
                                           {"local_timezone": local_timezone, "start_hour": start_hour,
                                            "end_hour": end_hour, "min_history": min_history},
                                           ["The supplied timezone is an analysis assumption, not a verified account timezone."])
                break
    return _results(found, "offhours_anomaly")