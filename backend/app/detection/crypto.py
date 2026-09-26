"""Detect rapid movement from non-crypto activity into crypto.

How it works: keep recent non-crypto transactions for each account. When that
account sends a crypto transaction, compare its amount with the recent activity.

Result: one ``(account, "crypto_offramp", evidence)`` tuple for each matching
account.

Example: an account receives 900,000 INR and sends a similar value to a crypto
wallet 30 minutes later. The account is returned for review.
"""
from __future__ import annotations

from collections import defaultdict, deque
from decimal import Decimal

import pandas as pd

from .common import _evidence, _frame, _id, _results, _truth


def detect_crypto_offramp(
    df: pd.DataFrame,
    lookback_hours=24,
    amount_tolerance=0.25,
):
    """Find comparable crypto transfers after recent non-crypto activity."""
    if lookback_hours <= 0:
        raise ValueError("lookback_hours must be positive")
    if not 0 <= amount_tolerance <= 1:
        raise ValueError("amount_tolerance must be between 0 and 1")

    records = _frame(
        df,
        (
            "transaction_id",
            "timestamp",
            "sender_account",
            "receiver_account",
            "amount",
            "currency",
            "is_crypto",
        ),
    )
    histories = defaultdict(deque)
    found = {}
    horizon = pd.Timedelta(hours=lookback_hours)
    tolerance = Decimal(str(amount_tolerance))

    for row in sorted(records, key=lambda item: item["timestamp"]):
        sender = _id(row["sender_account"])
        receiver = _id(row["receiver_account"])

        if not _truth(row["is_crypto"]):
            for account in {sender, receiver} - {None}:
                histories[account].append(row)
            continue

        if not sender or sender in found:
            continue

        history = histories[sender]
        while history and row["timestamp"] - history[0]["timestamp"] > horizon:
            history.popleft()

        matches = []
        for previous in reversed(history):
            gap = row["timestamp"] - previous["timestamp"]
            if gap <= pd.Timedelta(0):
                continue
            difference = abs(row["amount"] - previous["amount"]) / previous["amount"]
            if difference <= tolerance:
                matches.append((previous, difference, gap))
                break
        if not matches:
            continue

        previous, difference, gap = matches[0]
        found[sender] = _evidence(
            [previous, row],
            {
                "transition": "recent non-crypto activity to crypto transaction",
                "previous_currency": _id(previous["currency"]),
                "crypto_currency": _id(row["currency"]),
                "amount_difference_fraction": float(difference),
                "minutes_between": round(gap.total_seconds() / 60, 2),
                "crypto_destination": receiver,
            },
            {
                "lookback_hours": lookback_hours,
                "amount_tolerance": amount_tolerance,
            },
            [
                "The crypto flag and comparable values suggest a transition, but "
                "they do not verify wallet ownership or exchange rates."
            ],
        )

    return _results(found, "crypto_offramp")
