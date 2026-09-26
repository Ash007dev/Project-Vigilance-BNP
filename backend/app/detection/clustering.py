"""Detect small groups of accounts with very similar behaviour.

How it works: build simple activity features, scale them, and use DBSCAN to
find small dense groups.

Result: one ``(account, "behavioral_clustering", evidence)`` tuple for every
account in a matching group.

Example: two accounts with the same transfer count, values, timing, and channel
mix are returned together for review.
"""
from __future__ import annotations
from collections import defaultdict
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from .common import _evidence, _frame, _id, _results


def detect_behavioral_clustering(df: pd.DataFrame, eps=.45, min_samples=2,
                                 max_cluster_fraction=.25, min_accounts=8):
    """Find small groups with similar activity features."""
    records = _frame(df, ("transaction_id", "timestamp", "sender_account", "amount", "channel"))
    grouped = defaultdict(list)
    for row in records:
        if _id(row["sender_account"]):
            grouped[_id(row["sender_account"])].append(row)
    if len(grouped) < min_accounts:
        return []
    accounts = sorted(grouped)
    features = []
    for account in accounts:
        group = grouped[account]
        amounts = [float(r["amount"]) for r in group]
        features.append([len(group), float(np.mean(amounts)), float(np.std(amounts)),
                         float(np.mean([r["timestamp"].hour + r["timestamp"].minute / 60 for r in group])),
                         len({_id(r["channel"]) for r in group if _id(r["channel"])})])
    data = StandardScaler().fit_transform(np.asarray(features, dtype=float))
    labels = DBSCAN(eps=eps, min_samples=min_samples).fit_predict(data)
    members = defaultdict(list)
    for account, label in zip(accounts, labels):
        if label >= 0:
            members[int(label)].append(account)
    found = {}
    for label, cluster in members.items():
        if not min_samples <= len(cluster) <= max_cluster_fraction * len(accounts):
            continue
        for account in cluster:
            found[account] = _evidence(grouped[account], {"cluster_id": label, "cluster_accounts": cluster,
                                                            "cluster_size": len(cluster),
                                                            "features": dict(zip(("count", "mean_amount", "std_amount",
                                                                                "mean_hour", "channel_diversity"),
                                                                               features[accounts.index(account)]))},
                                       {"eps": eps, "min_samples": min_samples,
                                        "max_cluster_fraction": max_cluster_fraction},
                                       ["Similar activity does not establish account coordination; small groups need independent review."])
    return _results(found, "behavioral_clustering")
