"""Independent AML indicator: detect_round_tripping. Returns uniform (account_id, pattern, evidence) tuples."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from zoneinfo import ZoneInfo
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from .common import _evidence, _results, _temporal_cycles


def detect_round_tripping(graph: nx.DiGraph, window_hours=24, amount_tolerance=.10,
                          max_expansions=10_000):
    """Find chronological 2- or 3-leg returns with final amount within 10% of initial."""
    found = {}
    for path in _temporal_cycles(graph, 3, pd.Timedelta(hours=window_hours), max_expansions):
        if len(path) not in (2, 3):
            continue
        first, last = path[0]["amount"], path[-1]["amount"]
        if abs(last - first) / first > Decimal(str(amount_tolerance)):
            continue
        account = path[0]["src"]
        if account not in found:
            found[account] = _evidence(path, {"account_path": [account] + [e["dst"] for e in path],
                                               "first_amount": str(first), "returned_amount": str(last),
                                               "currency": path[0]["currency"]},
                                       {"window_hours": window_hours, "amount_tolerance": amount_tolerance},
                                       ["Comparable amounts and chronology do not prove the same money returned."])
    return _results(found, "round_tripping")
