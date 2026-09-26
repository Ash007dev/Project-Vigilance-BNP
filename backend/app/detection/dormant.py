"""Independent AML indicator: detect_dormant_reactivation. Returns uniform (account_id, pattern, evidence) tuples."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from zoneinfo import ZoneInfo
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from .common import _evidence, _frame, _id, _q75, _results


def detect_dormant_reactivation(df: pd.DataFrame, dormancy_days=90):
    """Find a large event after a 90-day observed account activity gap."""
    records = _frame(df, ("transaction_id", "timestamp", "sender_account", "receiver_account", "amount", "currency"))
    grouped = defaultdict(list)
    for row in records:
        for account in {_id(row["sender_account"]), _id(row["receiver_account"])} - {None}:
            grouped[(account, _id(row["currency"]))].append(row)
    found = {}
    for (account, currency), group in grouped.items():
        group.sort(key=lambda r: r["timestamp"])
        for i in range(1, len(group)):
            previous, current = group[i - 1], group[i]
            gap = current["timestamp"] - previous["timestamp"]
            if gap < pd.Timedelta(days=dormancy_days):
                continue
            history = [r["amount"] for r in group[:i]]
            if not history:
                history = [r["amount"] for r in records if r["timestamp"] < current["timestamp"] and _id(r["currency"]) == currency]
            if not history:
                continue
            quartile = _q75(history)
            if current["amount"] >= quartile:
                found[account] = _evidence([previous, current], {"gap_days": round(gap.total_seconds() / 86400, 2),
                                                              "amount": str(current["amount"]), "prior_q75": str(quartile),
                                                              "currency": currency},
                                           {"dormancy_days": dormancy_days},
                                           ["Dormancy means no observed events in this dataset, not proven account inactivity."])
                break
    return _results(found, "dormant_reactivation")
