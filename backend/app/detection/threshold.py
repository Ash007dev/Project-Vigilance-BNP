"""Detect repeated transfers just below a reporting threshold.

How it works: compare each account's near-threshold rate with peer accounts in
the same currency using a one-sided binomial test.

Result: one ``(account, "threshold_avoidance", evidence)`` tuple for each
statistically unusual account.

Example: eight of twenty transfers sit just below the limit while peers rarely
do this, so the account is returned for review.
"""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

import pandas as pd

from .common import _binomial_tail, _evidence, _frame, _id, _money, _results


def detect_threshold_avoidance(
    df: pd.DataFrame,
    threshold=1_000_000,
    below_fraction=0.05,
    min_transactions=6,
    min_near=3,
    alpha=0.01,
):
    """Find unusually frequent transfers just below a threshold."""
    records = _frame(
        df,
        ("transaction_id", "timestamp", "sender_account", "amount", "currency"),
    )
    limit = _money(threshold)
    lower_bound = limit * (1 - Decimal(str(below_fraction)))
    groups = defaultdict(list)
    for row in records:
        account = _id(row["sender_account"])
        currency = _id(row["currency"])
        if account and currency and row["amount"] < limit:
            groups[(account, currency)].append(row)

    found = {}
    for (account, currency), rows in groups.items():
        near = [row for row in rows if row["amount"] >= lower_bound]
        if len(rows) < min_transactions or len(near) < min_near:
            continue
        peers = [
            row
            for (other, peer_currency), samples in groups.items()
            if peer_currency == currency and other != account
            for row in samples
        ]
        if peers:
            peer_near = sum(row["amount"] >= lower_bound for row in peers)
            baseline = (1 + peer_near) / (len(peers) + 2)
        else:
            baseline = below_fraction

        p_value = _binomial_tail(len(rows), len(near), baseline)
        if p_value > alpha:
            continue
        found[account] = _evidence(
            near,
            {
                "near_count": len(near),
                "eligible_count": len(rows),
                "baseline_near_rate": round(baseline, 6),
                "one_sided_binomial_p": p_value,
                "currency": currency,
            },
            {
                "threshold": str(limit),
                "below_fraction": below_fraction,
                "min_transactions": min_transactions,
                "alpha": alpha,
            },
            [
                "A low p-value shows unusual behaviour but does not prove that the "
                "account intended to avoid a threshold."
            ],
        )

    return _results(found, "threshold_avoidance")
