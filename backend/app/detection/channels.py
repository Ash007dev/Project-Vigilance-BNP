"""Detect a customer switching between several payment channels.

How it works: count the customer's distinct sending channels inside a rolling
time window.

Result: one ``(account, "cross_channel_hopping", evidence)`` tuple for each
matching account.

Example: the same customer uses UPI, NEFT, and RTGS within one hour, so the
customer's account is returned for review.
"""
from __future__ import annotations
from collections import defaultdict
import pandas as pd
from .common import _evidence, _frame, _id, _results


def detect_cross_channel_hopping(df: pd.DataFrame, min_channels=3, window_hours=1):
    """Find customers using several sending channels in a short period."""
    records = _frame(df, ("transaction_id", "timestamp", "sender_account", "sender_customer_id", "channel"))
    groups = defaultdict(list)
    for row in records:
        if _id(row["sender_customer_id"]) and _id(row["channel"]):
            groups[_id(row["sender_customer_id"])].append(row)
    found = {}
    for customer, group in groups.items():
        group.sort(key=lambda r: r["timestamp"])
        left = 0
        for right, row in enumerate(group):
            while row["timestamp"] - group[left]["timestamp"] > pd.Timedelta(hours=window_hours):
                left += 1
            witness = group[left:right + 1]
            channels = {_id(r["channel"]) for r in witness}
            if len(channels) >= min_channels:
                for account in {_id(r["sender_account"]) for r in witness} - {None}:
                    if account not in found:
                        found[account] = _evidence(witness, {"customer_id": customer,
                                                            "channels": sorted(channels), "channel_count": len(channels)},
                                                   {"min_channels": min_channels, "window_hours": window_hours},
                                                   ["Channel switching can be legitimate; recorded customer mapping may require verification."])
                break
    return _results(found, "cross_channel_hopping")
