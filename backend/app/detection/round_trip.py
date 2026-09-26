"""Detect money that quickly returns to its starting account.

How it works: find strong two- or three-leg cycles, then confirm that the
transactions are chronological and the returned amount is close to the first.

Result: one ``(account, "round_tripping", evidence)`` tuple for the account
that started each matching return.

Example: A sends 1,000 to B and B sends 950 back to A within one day. A is
returned for review.
"""
from __future__ import annotations

from bisect import bisect_right
from collections import defaultdict
from decimal import Decimal

import networkx as nx
import numpy as np
import pandas as pd

from .common import _evidence, _graph_edges, _results


def _matching_return(cycle, currency, grouped, times, horizon, tolerance):
    for offset in range(len(cycle)):
        accounts = cycle[offset:] + cycle[:offset]
        pairs = list(zip(accounts, accounts[1:] + accounts[:1]))
        for first in grouped[(currency, *pairs[0])]:
            path = [first]

            def extend(pair_index):
                if pair_index == len(pairs):
                    return path.copy()
                key = (currency, *pairs[pair_index])
                start = bisect_right(times[key], path[-1]["timestamp"])
                for row in grouped[key][start:]:
                    if row["timestamp"] - first["timestamp"] > horizon:
                        break
                    if pair_index == len(pairs) - 1:
                        difference = abs(row["amount"] - first["amount"]) / first["amount"]
                        if difference > tolerance:
                            continue
                    path.append(row)
                    result = extend(pair_index + 1)
                    path.pop()
                    if result:
                        return result
                return None

            match = extend(1)
            if match:
                return accounts, match
    return None, None


def detect_round_tripping(
    graph,
    window_hours=24,
    amount_tolerance=0.10,
    max_expansions=10_000,
):
    """Find chronological two- or three-leg returns of comparable value."""
    if window_hours <= 0:
        raise ValueError("window_hours must be positive")
    if not 0 <= amount_tolerance <= 1:
        raise ValueError("amount_tolerance must be between 0 and 1")

    edges = _graph_edges(graph)
    grouped = defaultdict(list)
    for edge in edges:
        if edge["src"] != edge["dst"] and edge["currency"]:
            grouped[(edge["currency"], edge["src"], edge["dst"])].append(edge)
    grouped_times = {
        key: [edge["timestamp"] for edge in rows] for key, rows in grouped.items()
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
    tolerance = Decimal(str(amount_tolerance))
    cycles_checked = 0
    for currency, candidate_graph in graphs.items():
        try:
            cycles = nx.simple_cycles(candidate_graph, length_bound=3)
        except TypeError:
            cycles = (
                cycle
                for cycle in nx.simple_cycles(candidate_graph)
                if len(cycle) <= 3
            )
        for cycle in cycles:
            if len(cycle) not in (2, 3):
                continue
            cycles_checked += 1
            if cycles_checked > max_expansions:
                return _results(found, "round_tripping")
            accounts, path = _matching_return(
                cycle,
                currency,
                grouped,
                grouped_times,
                horizon,
                tolerance,
            )
            if not path:
                continue
            account = accounts[0]
            found.setdefault(
                account,
                _evidence(
                    path,
                    {
                        "account_path": accounts + [account],
                        "first_amount": str(path[0]["amount"]),
                        "returned_amount": str(path[-1]["amount"]),
                        "currency": currency,
                        "edge_repeat_cutoff": minimum_repeats,
                    },
                    {
                        "window_hours": window_hours,
                        "amount_tolerance": amount_tolerance,
                        "max_cycles_checked": max_expansions,
                    },
                    [
                        "Comparable values and timing do not prove the same money "
                        "returned to its source."
                    ],
                ),
            )

    return _results(found, "round_tripping")
