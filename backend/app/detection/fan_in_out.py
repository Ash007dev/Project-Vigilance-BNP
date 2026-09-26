"""Independent AML indicator: detect_fan_in_out. Returns uniform (account_id, pattern, evidence) tuples."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from zoneinfo import ZoneInfo
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from .common import _evidence, _graph_edges, _results


def detect_fan_in_out(graph: nx.DiGraph, window_hours=24, percentile=99):
    """Find unusually high inbound or outbound transfer degree in rolling 24h windows."""
    edges = _graph_edges(graph)
    if len(edges) < 2:
        return []
    nodes = set(graph.nodes)
    found = {}
    left = 0
    for right, latest in enumerate(edges):
        while latest["timestamp"] - edges[left]["timestamp"] > pd.Timedelta(hours=window_hours):
            left += 1
        window = edges[left:right + 1]
        inbound = defaultdict(int)
        outbound = defaultdict(int)
        for edge in window:
            outbound[edge["src"]] += 1
            inbound[edge["dst"]] += 1
        in_cutoff = np.percentile([inbound[n] for n in nodes], percentile)
        out_cutoff = np.percentile([outbound[n] for n in nodes], percentile)
        for node in nodes:
            if (inbound[node] > 1 and inbound[node] >= in_cutoff) or (outbound[node] > 1 and outbound[node] >= out_cutoff):
                score = max(inbound[node], outbound[node])
                if node not in found or score > found[node]["metrics"]["max_degree"]:
                    witness = [e for e in window if node in (e["src"], e["dst"])]
                    found[node] = _evidence(witness, {"in_degree": inbound[node], "out_degree": outbound[node],
                                                     "max_degree": score, "in_cutoff": float(in_cutoff),
                                                     "out_cutoff": float(out_cutoff)},
                                            {"window_hours": window_hours, "percentile": percentile},
                                            ["Degree counts transfers, not unique counterparties or a causal flow."])
    return _results(found, "fan_in_out")
