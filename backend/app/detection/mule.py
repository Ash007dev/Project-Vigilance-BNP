"""
This is basically to detect accounts that receive money and quickly forward it.

How it works is that it match a large incoming transfer with a later outgoing transfer
from the same account and currency. The account is suspicious after this happens
for money received from several senders.

Result: one (account, "mule_behavior", evidence) tuple for each matching
account.

Example: an account receives 200,000 from two people and forwards most of each
amount within five minutes. The account is returned for review.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from decimal import Decimal

import networkx as nx
import pandas as pd

from .common import _evidence, _frame, _graph_edges, _id, _money, _results


def detect_mule_behavior(
    df: pd.DataFrame,
    graph: nx.DiGraph,
    large_amount=100_000,
    max_minutes=30,
    min_senders=2,
    min_forward_fraction=0.5,
):
    """Find repeated large inflows followed by rapid forwarding."""
    if df is None or df.empty or graph is None or graph.number_of_edges() == 0:
        return []
    if max_minutes <= 0:
        raise ValueError("max_minutes must be positive")
    if min_senders < 1:
        raise ValueError("min_senders must be at least 1")
    if not 0 < min_forward_fraction <= 1:
        raise ValueError("min_forward_fraction must be between 0 and 1")

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
    scoped_ids = {edge["transaction_id"] for edge in _graph_edges(graph)}
    received = defaultdict(list)
    sent = defaultdict(list)
    for row in records:
        if row["transaction_id"] not in scoped_ids:
            continue
        sender = _id(row["sender_account"])
        receiver = _id(row["receiver_account"])
        currency = _id(row["currency"])
        if not sender or not receiver or not currency or sender == receiver:
            continue
        received[(receiver, currency)].append(row)
        sent[(sender, currency)].append(row)

    matches = defaultdict(list)
    amount_limit = _money(large_amount)
    forward_fraction = Decimal(str(min_forward_fraction))
    for key, arrivals in received.items():
        outgoing = sorted(sent[key], key=lambda row: row["timestamp"])
        outgoing_times = [row["timestamp"] for row in outgoing]
        used = set()
        for incoming in sorted(arrivals, key=lambda row: row["timestamp"]):
            if incoming["amount"] < amount_limit:
                continue
            start = bisect_right(outgoing_times, incoming["timestamp"])
            for outgoing_row in outgoing[start:]:
                minutes = (
                    outgoing_row["timestamp"] - incoming["timestamp"]
                ).total_seconds() / 60
                if minutes > max_minutes:
                    break
                if outgoing_row["transaction_id"] in used:
                    continue
                if outgoing_row["amount"] < incoming["amount"] * forward_fraction:
                    continue
                used.add(outgoing_row["transaction_id"])
                matches[key].append((incoming, outgoing_row, minutes))
                break

    found = {}
    for (account, currency), episodes in matches.items():
        senders = {_id(incoming["sender_account"]) for incoming, _, _ in episodes}
        senders.discard(None)
        if len(senders) < min_senders:
            continue
        witness = [row for incoming, outgoing, _ in episodes for row in (incoming, outgoing)]
        found[account] = _evidence(
            witness,
            {
                "episode_count": len(episodes),
                "distinct_senders": len(senders),
                "forward_minutes": [round(minutes, 2) for _, _, minutes in episodes],
                "currency": currency,
            },
            {
                "large_amount": str(amount_limit),
                "max_minutes": max_minutes,
                "min_senders": min_senders,
                "min_forward_fraction": min_forward_fraction,
            },
            [
                "Rapid forwarding is suspicious, but balances and beneficial "
                "ownership are not available in transaction data alone."
            ],
        )

    return _results(found, "mule_behavior")
