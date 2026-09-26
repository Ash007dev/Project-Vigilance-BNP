"""Detect accounts that connect otherwise separate groups.

How it works: calculate graph betweenness and compare each account with the
configured percentile.

Result: one ``(account, "bridge_nodes", evidence)`` tuple for each strong
bridge account.

Example: if most transfers between two groups pass through X, X is returned
for review.
"""
from __future__ import annotations
from collections import defaultdict
import networkx as nx
import numpy as np
from .common import _evidence, _graph_edges, _results


def detect_bridge_nodes(graph: nx.DiGraph, percentile=99):
    """Find accounts with unusually high betweenness centrality."""
    edges = _graph_edges(graph)
    if len(edges) < 2:
        return []
    simple = nx.DiGraph()
    simple.add_edges_from((e["src"], e["dst"]) for e in edges)
    scores = nx.betweenness_centrality(simple)
    cutoff = float(np.percentile(list(scores.values()), percentile))
    volumes = defaultdict(int)
    for edge in edges:
        volumes[edge["src"]] += 1
        volumes[edge["dst"]] += 1
    median_volume = float(np.median(list(volumes.values())))
    found = {}
    for account, centrality in scores.items():
        if centrality > 0 and centrality >= cutoff:
            witness = [e for e in edges if account in (e["src"], e["dst"])]
            found[account] = _evidence(witness, {"betweenness": centrality, "cutoff": cutoff,
                                                 "transaction_volume": volumes[account], "median_volume": median_volume,
                                                 "unremarkable_volume": volumes[account] <= median_volume},
                                       {"percentile": percentile},
                                       ["Static graph centrality cannot establish time-respecting transaction flow."])
    return _results(found, "bridge_nodes")
