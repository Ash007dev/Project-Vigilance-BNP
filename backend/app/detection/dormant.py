"""Detect a large transaction after a long period without activity.

How it works: sort each account's transfers, measure gaps, and compare the first
transfer after a long gap with that account's earlier values.

Result: one ``(account, "dormant_reactivation", evidence)`` tuple for each
matching account.

Example: an account is quiet for 100 days and then sends much more than usual,
so it is returned for review.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from .common import _evidence, _frame, _id, _q75, _results


def detect_dormant_reactivation(df: pd.DataFrame, dormancy_days=90):
    """Find large activity after an observed dormant period."""
    records = _frame(
        df,
        (
            "transaction_id",
            "timestamp",
            "sender_account",
            "receiver_account",
            "amount",
            "currency",
        ),
    )
    grouped = defaultdict(list)
    for row in records:
        accounts = {_id(row["sender_account"]), _id(row["receiver_account"])}
        for account in accounts - {None}:
            grouped[(account, _id(row["currency"]))].append(row)

    found = {}
    for (account, currency), rows in grouped.items():
        rows.sort(key=lambda row: row["timestamp"])
        for index in range(1, len(rows)):
            previous = rows[index - 1]
            current = rows[index]
            gap = current["timestamp"] - previous["timestamp"]
            if gap < pd.Timedelta(days=dormancy_days):
                continue
            quartile = _q75([row["amount"] for row in rows[:index]])
            if current["amount"] < quartile:
                continue
            found[account] = _evidence(
                [previous, current],
                {
                    "gap_days": round(gap.total_seconds() / 86400, 2),
                    "amount": str(current["amount"]),
                    "prior_q75": str(quartile),
                    "currency": currency,
                },
                {"dormancy_days": dormancy_days},
                [
                    "Dormancy means no activity in this dataset; other activity may "
                    "exist outside the available records."
                ],
            )
            break

    return _results(found, "dormant_reactivation")
