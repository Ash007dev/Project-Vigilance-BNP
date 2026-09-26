"""Detect accounts receiving from or sending to many counterparties.

How it works: find each account's largest set of unique counterparties inside a
rolling time window, then compare it with the rest of the graph.

Result: one ``(account, "fan_in_out", evidence)`` tuple for each unusually
connected account.

Example: fifteen different accounts send to one hub in a day. The hub is
returned as fan-in activity.
"""
from __future__ import annotations

from collections import defaultdict

import numpy as np
import pandas as pd

from .common import _evidence, _graph_edges, _results


def _best_unique_window(events, horizon):
    counts = defaultdict(int)
    left = 0
    best_count = 0
    best_rows = []
    for right, (timestamp, counterparty, edge) in enumerate(events):
        counts[counterparty] += 1
        while timestamp - events[left][0] > horizon:
            old_counterparty = events[left][1]
            counts[old_counterparty] -= 1
            if counts[old_counterparty] == 0:
                del counts[old_counterparty]
            left += 1
        if len(counts) > best_count:
            best_count = len(counts)
            best_rows = [item[2] for item in events[left : right + 1]]
    return best_count, best_rows


def detect_fan_in_out(graph, window_hours=24, percentile=99):
    """Find high fan-in or fan-out based on unique counterparties."""
    if window_hours <= 0:
        raise ValueError("window_hours must be positive")
    if not 0 <= percentile <= 100:
        raise ValueError("percentile must be between 0 and 100")

    edges = _graph_edges(graph)
    if len(edges) < 2:
        return []

    incoming = defaultdict(list)
    outgoing = defaultdict(list)
    nodes = set()
    for edge in edges:
        nodes.update((edge["src"], edge["dst"]))
        incoming[edge["dst"]].append((edge["timestamp"], edge["src"], edge))
        outgoing[edge["src"]].append((edge["timestamp"], edge["dst"], edge))

    horizon = pd.Timedelta(hours=window_hours)
    inbound = {}
    outbound = {}
    inbound_rows = {}
    outbound_rows = {}
    for node in nodes:
        inbound[node], inbound_rows[node] = _best_unique_window(
            incoming[node], horizon
        )
        outbound[node], outbound_rows[node] = _best_unique_window(
            outgoing[node], horizon
        )

    in_cutoff = float(np.percentile(list(inbound.values()), percentile))
    out_cutoff = float(np.percentile(list(outbound.values()), percentile))
    found = {}
    for node in nodes:
        high_in = inbound[node] > 1 and inbound[node] >= in_cutoff
        high_out = outbound[node] > 1 and outbound[node] >= out_cutoff
        if not high_in and not high_out:
            continue
        witness = inbound_rows[node] if inbound[node] >= outbound[node] else outbound_rows[node]
        found[node] = _evidence(
            witness,
            {
                "unique_inbound_counterparties": inbound[node],
                "unique_outbound_counterparties": outbound[node],
                "inbound_cutoff": in_cutoff,
                "outbound_cutoff": out_cutoff,
            },
            {"window_hours": window_hours, "percentile": percentile},
            [
                "A high number of counterparties may be normal for merchants or "
                "payment hubs and needs business-context review."
            ],
        )

    return _results(found, "fan_in_out")
