"""Detect fast movement through a connected account network.

How it works: keep the strongest sender-to-receiver links, then look for a
multi-hop network involving several accounts inside a short time window.

Result: one ``(account, "layering", evidence)`` tuple for every account in the
matching network.

Example: A sends to B and C, then B and C forward to D and E within two hours.
The connected accounts are returned for review.
"""
from __future__ import annotations

from collections import defaultdict

import networkx as nx
import numpy as np
import pandas as pd

from .common import _evidence, _frame, _id, _results


MIN_ACCOUNTS = 5
TIME_WINDOW_HOURS = 2


def _has_multiple_hops(graph, source, accounts):
    lengths = nx.single_source_shortest_path_length(graph, source)
    return any(account in accounts and distance >= 2 for account, distance in lengths.items())


def detect_layering(
    df: pd.DataFrame,
    min_accounts=MIN_ACCOUNTS,
    window_hours=TIME_WINDOW_HOURS,
    max_expansions=100_000,
):
    """Find repeated multi-hop movement through several connected accounts."""
    if min_accounts < 2:
        raise ValueError("min_accounts must be at least 2")
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

    counts = [len(rows) for rows in grouped.values()]
    if len(counts) > 100:
        minimum_repeats = max(2, int(np.percentile(counts, 99.9)))
    else:
        minimum_repeats = 1

    topology = defaultdict(nx.DiGraph)
    for (currency, source, target), rows in grouped.items():
        if len(rows) >= minimum_repeats:
            rows.sort(key=lambda row: row["timestamp"])
            topology[currency].add_edge(source, target)

    found = {}
    horizon = pd.Timedelta(hours=window_hours)
    checks = 0
    for currency, graph in topology.items():
        for component in nx.weakly_connected_components(graph):
            if len(component) < min_accounts:
                continue
            component_rows = []
            for source, target in graph.subgraph(component).edges:
                component_rows.extend(grouped[(currency, source, target)])
            component_rows.sort(key=lambda row: row["timestamp"])

            left = 0
            active_edges = defaultdict(int)
            for right, row in enumerate(component_rows):
                edge = (_id(row["sender_account"]), _id(row["receiver_account"]))
                changed = active_edges[edge] == 0
                active_edges[edge] += 1
                while row["timestamp"] - component_rows[left]["timestamp"] > horizon:
                    old = component_rows[left]
                    old_edge = (_id(old["sender_account"]), _id(old["receiver_account"]))
                    active_edges[old_edge] -= 1
                    if active_edges[old_edge] == 0:
                        del active_edges[old_edge]
                        changed = True
                    left += 1
                if not changed:
                    continue

                checks += 1
                if checks > max_expansions:
                    return _results(found, "layering")
                active_graph = nx.DiGraph()
                active_graph.add_edges_from(active_edges)
                match = None
                for source in active_graph:
                    accounts = {source} | nx.descendants(active_graph, source)
                    if len(accounts) >= min_accounts and _has_multiple_hops(
                        active_graph, source, accounts
                    ):
                        match = accounts
                        break
                if not match:
                    continue

                representatives = {}
                for evidence_row in component_rows[left : right + 1]:
                    pair = (
                        _id(evidence_row["sender_account"]),
                        _id(evidence_row["receiver_account"]),
                    )
                    if pair[0] in match and pair[1] in match:
                        representatives.setdefault(pair, evidence_row)
                witness = list(representatives.values())
                evidence = _evidence(
                    witness,
                    {
                        "account_count": len(match),
                        "accounts": sorted(match),
                        "transaction_count": len(witness),
                        "total_amount": str(sum(item["amount"] for item in witness)),
                        "currency": currency,
                        "edge_repeat_cutoff": minimum_repeats,
                    },
                    {
                        "min_accounts": min_accounts,
                        "window_hours": window_hours,
                        "max_topology_checks": max_expansions,
                    },
                    [
                        "A connected multi-hop network can be legitimate and still "
                        "needs account-ownership and source-of-funds review."
                    ],
                )
                for account in match:
                    found.setdefault(account, evidence)
                break

    return _results(found, "layering")
