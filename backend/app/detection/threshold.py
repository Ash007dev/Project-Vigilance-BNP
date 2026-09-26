"""Independent AML indicator: detect_threshold_avoidance. Returns uniform (account_id, pattern, evidence) tuples."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from zoneinfo import ZoneInfo
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from .common import _binomial_tail, _evidence, _frame, _id, _money, _results


def detect_threshold_avoidance(df: pd.DataFrame, threshold=1_000_000, below_fraction=.05,
                               min_transactions=6, min_near=3, alpha=.01):
    """Test whether just-below-threshold transfers are unusually frequent versus other accounts."""
    records = _frame(df, ("transaction_id", "timestamp", "sender_account", "amount", "currency"))
    limit = _money(threshold)
    groups = defaultdict(list)
    for row in records:
        account = _id(row["sender_account"])
        if account and row["amount"] < limit and _id(row["currency"]):
            groups[(account, _id(row["currency"]))].append(row)
    found = {}
    for (account, currency), group in groups.items():
        n = len(group)
        near = [r for r in group if r["amount"] >= limit * (1 - Decimal(str(below_fraction)))]
        if n < min_transactions or len(near) < min_near:
            continue
        cohort = [r for (other, cur), samples in groups.items() if cur == currency and other != account for r in samples]
        p = (1 + sum(r["amount"] >= limit * (1 - Decimal(str(below_fraction))) for r in cohort)) / (len(cohort) + 2) if cohort else below_fraction
        p_value = _binomial_tail(n, len(near), p)
        if p_value <= alpha:
            found[account] = _evidence(near, {"near_count": len(near), "eligible_count": n,
                                               "baseline_near_rate": round(p, 6), "one_sided_binomial_p": p_value,
                                               "currency": currency},
                                       {"threshold": str(limit), "below_fraction": below_fraction,
                                        "min_transactions": min_transactions, "alpha": alpha},
                                       ["A cohort-based binomial screen assumes independent events and a comparable peer mix; p-value is not proof of intent."])
    return _results(found, "threshold_avoidance")
