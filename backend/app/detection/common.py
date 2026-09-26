"""Provide shared input, money, graph, and evidence helpers.

How it works: clean detector inputs once and format every finding the same way.

Result: detector modules receive safe records and return consistent evidence.

Example: ``build_transaction_graph(frame)`` keeps every valid transfer as its
own dated graph edge.
"""
from __future__ import annotations
from decimal import Decimal, InvalidOperation
import networkx as nx
import numpy as np
import pandas as pd
from scipy.stats import binom


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
    missing = sorted(set(required) - set(df.columns))
    if missing:
        raise ValueError("Missing required columns: " + ", ".join(missing))
    if df.empty:
        return []
    records = df.to_dict("records")
    if "timestamp" in required:
        times = pd.to_datetime([r["timestamp"] for r in records], utc=True, errors="coerce")
        valid = ~times.isna()
        records = [row for row, keep in zip(records, valid) if keep]
        for row, stamp in zip(records, times[valid]):
            row["timestamp"] = stamp
    if "amount" in required:
        valid_records = []
        for row in records:
            try:
                row["amount"] = _money(row["amount"])
            except ValueError:
                continue
            valid_records.append(row)
        records = valid_records
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


def _evidence(records, metrics, parameters=None, limitations=None, max_records=100):
    records = list(records)
    times = [r["timestamp"] for r in records if r.get("timestamp") is not None]
    if len(records) > max_records:
        half = max_records // 2
        evidence_records = records[:half] + records[-(max_records - half) :]
    else:
        evidence_records = records
    return {
        "transaction_ids": list(dict.fromkeys(str(r["transaction_id"]) for r in evidence_records if r.get("transaction_id") is not None)),
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


def _binomial_tail(n, hits, p):
    return float(binom.sf(hits - 1, n, p))
