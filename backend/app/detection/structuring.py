"""Detect a large amount split across several smaller transfers.

How it works: keep each sender's below-threshold transfers in a rolling time
window. Flag the sender when the count is high and the combined value reaches
the reporting threshold.

Result: one ``(account, "structuring", evidence)`` tuple for each sender.

Example: six transfers of 99,000 in one day are individually below a 100,000
limit but clearly exceed it together, so the sender is returned.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import pandas as pd

from .common import _evidence, _frame, _id, _money, _results


TRANSACTION_THRESHOLD = 100_000
MIN_TRANSACTIONS = 5
TIME_WINDOW_HOURS = 24


def detect_structuring(
    df: pd.DataFrame,
    threshold=TRANSACTION_THRESHOLD,
    min_transactions=MIN_TRANSACTIONS,
    window_hours=TIME_WINDOW_HOURS,
    below_fraction=0.10,
):
    """Find repeated below-threshold transfers with a large combined value."""
    if min_transactions < 1:
        raise ValueError("min_transactions must be at least 1")
    if window_hours <= 0:
        raise ValueError("window_hours must be positive")
    if not 0 < below_fraction <= 1:
        raise ValueError("below_fraction must be between 0 and 1")

    records = _frame(df, ("transaction_id", "timestamp", "sender_account", "amount"))
    limit = _money(threshold)
    lower_bound = limit * (1 - Decimal(str(below_fraction)))
    grouped = defaultdict(list)
    for row in records:
        account = _id(row["sender_account"])
        if account and lower_bound <= row["amount"] < limit:
            grouped[account].append(row)

    found = {}
    horizon = pd.Timedelta(hours=window_hours)
    for account, rows in grouped.items():
        rows.sort(key=lambda row: row["timestamp"])
        left = 0
        total = Decimal(0)
        for right, row in enumerate(rows):
            total += row["amount"]
            while row["timestamp"] - rows[left]["timestamp"] > horizon:
                total -= rows[left]["amount"]
                left += 1
            count = right - left + 1
            if count <= min_transactions or total < limit:
                continue
            window = rows[left : right + 1]
            found[account] = _evidence(
                window,
                {
                    "transaction_count": count,
                    "total_amount": str(total),
                },
                {
                    "threshold": str(limit),
                    "min_transactions": min_transactions,
                    "window_hours": window_hours,
                    "below_fraction": below_fraction,
                },
                [
                    "Several smaller transfers may have a legitimate business reason; "
                    "the pattern does not prove intent."
                ],
            )
            break

    return _results(found, "structuring")
