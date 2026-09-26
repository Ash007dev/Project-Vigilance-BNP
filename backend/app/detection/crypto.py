"""Independent AML indicator: detect_crypto_offramp. Returns uniform (account_id, pattern, evidence) tuples."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from zoneinfo import ZoneInfo
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from .common import _evidence, _frame, _id, _results, _truth
from .structuring import detect_structuring


def detect_crypto_offramp(df: pd.DataFrame, lookback_hours=24, threshold=1_000_000):
    """Find a fiat-to-crypto-marked transition after a detected structuring episode.

    ``is_crypto`` alone does not establish wallet direction. Despite the
    historical detector name, this is an *on-ramp-like* observation, not a
    verified crypto off-ramp or wallet transfer.
    """
    records = _frame(df, ("transaction_id", "timestamp", "sender_account", "receiver_account", "amount", "currency", "is_crypto"))
    prior_hits = defaultdict(list)
    for account, _, evidence in detect_structuring(df, threshold=threshold):
        ids = set(evidence["transaction_ids"])
        prior_hits[account] = [r for r in records if r["transaction_id"] in ids and not _truth(r["is_crypto"])]
    found = {}
    for row in sorted(records, key=lambda r: r["timestamp"]):
        account = _id(row["sender_account"])
        if not account or not _truth(row["is_crypto"]):
            continue
        same_currency = _id(row["currency"])
        previous = [r for r in records if _id(r["sender_account"]) == account
                    and _id(r["currency"]) == same_currency and r["timestamp"] < row["timestamp"]]
        if not previous or _truth(max(previous, key=lambda r: r["timestamp"])["is_crypto"]):
            continue
        supporting = [r for r in prior_hits[account] if _id(r["currency"]) == same_currency
                      and pd.Timedelta(0) < row["timestamp"] - r["timestamp"] <= pd.Timedelta(hours=lookback_hours)]
        if supporting and account not in found:
            found[account] = _evidence(supporting + [row],
                                       {"transition": "prior non-crypto activity -> crypto-marked transaction",
                                        "supporting_prior_count": len(supporting), "currency": _id(row["currency"])},
                                       {"lookback_hours": lookback_hours, "structuring_threshold": str(threshold)},
                                       ["is_crypto does not specify a wallet direction; fiat-to-crypto movement is unverified."])
    return _results(found, "crypto_offramp")