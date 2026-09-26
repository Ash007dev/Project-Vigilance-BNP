"""Detect money that returns to its starting account.

How it works: group repeated transfers by sender, receiver, and currency. Build
a small graph from the strongest links, then confirm each cycle with real
transactions in time order.

Result: one ``(account, "circular_flow", evidence)`` tuple for every account in
the cycle.

Example: A sends INR to B, B sends INR to C, and C sends INR back to A. All
three accounts are returned for review.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd

from .common import _evidence, _frame, _id, _results


MIN_CYCLE_LENGTH = 3
MAX_CYCLE_LENGTH = 6


def _ordered_cycle(cycle, currency, grouped, grouped_times, horizon):
    """Return the first time-ordered set of transactions for one cycle."""
    for offset in range(len(cycle)):
        accounts = cycle[offset:] + cycle[:offset]
        pairs = list(zip(accounts, accounts[1:] + accounts[:1]))
        first_rows = grouped[(currency, *pairs[0])]
        for first in first_rows:
            path = [first]
            previous_time = first["timestamp"]
            for source, target in pairs[1:]:
                key = (currency, source, target)
                times = grouped_times[key]
                index = bisect_right(times, previous_time)
                if index == len(times):
                    break
                next_row = grouped[key][index]
                if next_row["timestamp"] - first["timestamp"] > horizon:
                    break
                path.append(next_row)
                previous_time = next_row["timestamp"]
            if len(path) == len(pairs):
                return accounts, path
    return None, None


def detect_circular_flow(
    df: pd.DataFrame,
    min_cycle_length=MIN_CYCLE_LENGTH,
    max_cycle_length=MAX_CYCLE_LENGTH,
    window_hours=24,
    max_expansions=100_000,
):
    """Find short chronological cycles that use one currency."""
    if min_cycle_length < 2:
        raise ValueError("min_cycle_length must be at least 2")
    if max_cycle_length < min_cycle_length:
        raise ValueError("max_cycle_length must be at least min_cycle_length")
    if window_hours <= 0:
        raise ValueError("window_hours must be positive")

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
        source = _id(row["sender_account"])
        target = _id(row["receiver_account"])
        currency = _id(row["currency"])
        if source and target and currency and source != target:
            grouped[(currency, source, target)].append(row)

    for rows in grouped.values():
        rows.sort(key=lambda row: row["timestamp"])
    grouped_times = {
        key: [row["timestamp"] for row in rows] for key, rows in grouped.items()
    }

    counts = [len(rows) for rows in grouped.values()]
    if len(counts) > 100:
        minimum_repeats = max(2, int(np.percentile(counts, 99.9)))
    else:
        minimum_repeats = 1

    graphs = defaultdict(nx.DiGraph)
    for (currency, source, target), rows in grouped.items():
        if len(rows) >= minimum_repeats:
            graphs[currency].add_edge(source, target)

    found = {}
    horizon = pd.Timedelta(hours=window_hours)
    cycles_checked = 0
    for currency, graph in graphs.items():
        try:
            cycles = nx.simple_cycles(graph, length_bound=max_cycle_length)
        except TypeError:
            cycles = (
                cycle
                for cycle in nx.simple_cycles(graph)
                if len(cycle) <= max_cycle_length
            )
        for cycle in cycles:
            if len(cycle) < min_cycle_length:
                continue
            cycles_checked += 1
            if cycles_checked > max_expansions:
                return _results(found, "circular_flow")
            accounts, path = _ordered_cycle(
                cycle, currency, grouped, grouped_times, horizon
            )
            if not path:
                continue
            evidence = _evidence(
                path,
                {
                    "cycle_length": len(path),
                    "cycle_accounts": accounts,
                    "total_amount": str(sum(row["amount"] for row in path)),
                    "currency": currency,
                    "edge_repeat_cutoff": minimum_repeats,
                },
                {
                    "min_cycle_length": min_cycle_length,
                    "max_cycle_length": max_cycle_length,
                    "window_hours": window_hours,
                    "max_cycles_checked": max_expansions,
                },
                [
                    "A closed path does not prove the same money completed the cycle; "
                    "amounts and account ownership still need review."
                ],
            )
            for account in accounts:
                found.setdefault(account, evidence)

    return _results(found, "circular_flow")
