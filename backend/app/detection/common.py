"""Shared validation, evidence format, and bounded graph traversal for indicators."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal, InvalidOperation
from math import comb
import networkx as nx
import numpy as np
import pandas as pd


def _id(value):
    if value is None or pd.isna(value) or str(value).strip() == "":
        return None
    return str(value)


def _money(value):
    try:
        result = Decimal(str(value))
    except (TypeError, InvalidOperation) as exc:
        raise ValueError(f"Invalid transaction amount: {value!r}") from exc
    if not result.is_finite() or result <= 0:
        raise ValueError(f"Transaction amount must be positive and finite: {value!r}")
    return result


def _q75(values):
    """Linear 75th percentile using Decimal arithmetic throughout."""
    ordered = sorted(values)
    position = Decimal(3) * (len(ordered) - 1) / 4
    low = int(position)
    fraction = position - low
    return ordered[low] + (ordered[min(low + 1, len(ordered) - 1)] - ordered[low]) * fraction


def _frame(df: pd.DataFrame, required: tuple[str, ...]):
    if not isinstance(df, pd.DataFrame):
        raise TypeError("Expected a pandas DataFrame")
    if df.empty:
        return []
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    records = df.to_dict("records")
    if "timestamp" in required:
        times = pd.to_datetime([r["timestamp"] for r in records], utc=True, errors="coerce")
        if times.isna().any():
            raise ValueError("Invalid timestamp in nonempty input")
        for row, stamp in zip(records, times):
            row["timestamp"] = stamp
    if "amount" in required:
        for row in records:
            row["amount"] = _money(row["amount"])
    for row in records:
        if "transaction_id" in row:
            row["transaction_id"] = _id(row["transaction_id"])
    return records


def _truth(value):
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str):
        return value.strip().lower() in {"true", "1", "yes"}
    return value == 1


def _evidence(records, metrics, parameters=None, limitations=None):
    times = [r["timestamp"] for r in records if r.get("timestamp") is not None]
    return {
        "transaction_ids": list(dict.fromkeys(str(r["transaction_id"]) for r in records if r.get("transaction_id") is not None)),
        "window_start": min(times).isoformat() if times else None,
        "window_end": max(times).isoformat() if times else None,
        "metrics": metrics,
        "parameters": parameters or {},
        "limitations": limitations or ["Observed behaviour warrants review; it does not establish laundering or ownership."],
    }


def _results(mapping, pattern):
    return [(account, pattern, evidence) for account, evidence in sorted(mapping.items(), key=lambda v: str(v[0]))]


def build_transaction_graph(df: pd.DataFrame) -> nx.MultiDiGraph:
    """Preserve each dated transfer as its own directed edge, including duplicates between accounts."""
    graph = nx.MultiDiGraph()
    records = _frame(df, ("transaction_id", "timestamp", "sender_account", "receiver_account", "amount", "currency"))
    for index, row in enumerate(records):
        source, target = _id(row["sender_account"]), _id(row["receiver_account"])
        if source is None or target is None:
            continue  # Unresolved party cannot be used to assert a shared identity.
        graph.add_edge(source, target, key=f"{row['transaction_id']}:{index}",
                       transaction_id=row["transaction_id"], timestamp=row["timestamp"],
                       amount=row["amount"], currency=_id(row["currency"]))
    return graph


def _graph_edges(graph):
    if graph is None or graph.number_of_edges() == 0:
        return []
    if not graph.is_directed():
        raise ValueError("A directed transaction graph is required")
    iterator = graph.edges(keys=True, data=True) if graph.is_multigraph() else ((u, v, 0, a) for u, v, a in graph.edges(data=True))
    edges = []
    for u, v, key, data in iterator:
        for required in ("transaction_id", "timestamp", "amount", "currency"):
            if required not in data:
                raise ValueError(f"Graph edge missing required {required}")
        stamp = pd.to_datetime(data["timestamp"], utc=True, errors="coerce")
        if pd.isna(stamp):
            raise ValueError("Invalid graph edge timestamp")
        edges.append({"src": _id(u), "dst": _id(v), "key": key,
                      "timestamp": stamp, "transaction_id": _id(data["transaction_id"]),
                      "amount": _money(data["amount"]), "currency": _id(data["currency"])})
    return sorted(edges, key=lambda e: (e["timestamp"], str(e["transaction_id"])))


def _adjacency(edges):
    result = defaultdict(list)
    for edge in edges:
        result[edge["src"]].append(edge)
    return result


def _temporal_cycles(graph, max_depth, horizon, max_expansions):
    """Enumerate only short, time-respecting cycles on bounded case subgraphs."""
    edges = _graph_edges(graph)
    adj = _adjacency(edges)
    expansions = 0
    for first in edges:
        if first["src"] == first["dst"]:
            continue
        stack = [(first["dst"], [first], {first["src"], first["dst"]})]
        while stack:
            node, path, visited = stack.pop()
            if len(path) >= max_depth:
                continue
            for edge in adj[node]:
                if edge["timestamp"] <= path[-1]["timestamp"] or edge["currency"] != first["currency"]:
                    continue
                if edge["timestamp"] - first["timestamp"] > horizon:
                    break
                expansions += 1
                if expansions > max_expansions:
                    raise RuntimeError("Temporal cycle search budget exceeded; analyse a smaller case subgraph")
                if edge["dst"] == first["src"]:
                    yield path + [edge]
                elif edge["dst"] not in visited:
                    stack.append((edge["dst"], path + [edge], visited | {edge["dst"]}))


def _binomial_tail(n, hits, p):
    return sum(comb(n, k) * p ** k * (1 - p) ** (n - k) for k in range(hits, n + 1))
