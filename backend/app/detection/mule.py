"""Independent AML indicator: detect_mule_behavior. Returns uniform (account_id, pattern, evidence) tuples."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from zoneinfo import ZoneInfo
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from .common import _evidence, _frame, _graph_edges, _id, _money, _results


def detect_mule_behavior(df: pd.DataFrame, graph: nx.DiGraph, large_amount=1_000_000,
                         max_minutes=30, min_senders=2, min_forward_fraction=0.5):
    """Find repeated large incoming receipts rapidly followed by substantial outgoing transfers."""
    if df is None or df.empty or graph is None or graph.number_of_edges() == 0:
        return []
    # The supplied graph is the investigation scope; source records supply exact witness IDs.
    records = _frame(df, ("transaction_id", "timestamp", "sender_account", "receiver_account", "amount", "currency"))
    scoped_ids = {e["transaction_id"] for e in _graph_edges(graph)}
    received, sent = defaultdict(list), defaultdict(list)
    for row in records:
        if row["transaction_id"] not in scoped_ids:
            continue
        if _id(row["sender_account"]) == _id(row["receiver_account"]):
            continue
        received[(_id(row["receiver_account"]), _id(row["currency"]))].append(row)
        sent[(_id(row["sender_account"]), _id(row["currency"]))].append(row)
    matches = defaultdict(list)
    for key, arrivals in received.items():
        outgoing = sorted(sent[key], key=lambda r: r["timestamp"])
        used = set()
        for inc in sorted(arrivals, key=lambda r: r["timestamp"]):
            if inc["amount"] < _money(large_amount) or not _id(inc["sender_account"]):
                continue
            for out in outgoing:
                dt = (out["timestamp"] - inc["timestamp"]).total_seconds() / 60
                if dt <= 0:
                    continue
                if dt > max_minutes:
                    break
                if out["transaction_id"] not in used and out["amount"] >= inc["amount"] * Decimal(str(min_forward_fraction)):
                    used.add(out["transaction_id"])
                    matches[key].append((inc, out, dt))
                    break
    found = {}
    for (account, currency), episodes in matches.items():
        senders = {_id(inc["sender_account"]) for inc, _, _ in episodes}
        if account and len(senders) >= min_senders:
            witness = [r for inc, out, _ in episodes for r in (inc, out)]
            found[account] = _evidence(witness, {"episode_count": len(episodes), "distinct_senders": len(senders),
                                                 "forward_minutes": [round(dt, 2) for _, _, dt in episodes], "currency": currency},
                                       {"large_amount": str(large_amount), "max_minutes": max_minutes,
                                        "min_senders": min_senders, "min_forward_fraction": min_forward_fraction},
                                       ["Rapid forwarding is a flow plausibility observation; balances and beneficial ownership are unknown."])
    return _results(found, "mule_behavior")
