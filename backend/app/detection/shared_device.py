"""Independent AML indicator: detect_shared_device_ip. Returns uniform (account_id, pattern, evidence) tuples."""
from __future__ import annotations
from collections import defaultdict
from decimal import Decimal
from zoneinfo import ZoneInfo
import networkx as nx
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from sklearn.preprocessing import StandardScaler
from .common import _evidence, _frame, _id, _results


def detect_shared_device_ip(df: pd.DataFrame, max_customers=3):
    """Find a sender device or originating IP recorded for more than three distinct customers."""
    records = _frame(df, ("transaction_id", "timestamp", "sender_account", "sender_customer_id", "device_id", "ip_address"))
    grouped = defaultdict(list)
    for row in records:
        for field in ("device_id", "ip_address"):
            if _id(row[field]) and _id(row["sender_customer_id"]):
                grouped[(field, _id(row[field]))].append(row)
    found = defaultdict(lambda: {"rows": [], "device_id": [], "ip_address": []})
    for (field, identifier), group in grouped.items():
        customers = {_id(r["sender_customer_id"]) for r in group}
        if len(customers) > max_customers:
            for row in group:
                account = _id(row["sender_account"])
                if account:
                    found[account]["rows"].append(row)
                    found[account][field].append({"value": identifier, "distinct_customers": len(customers)})
    return _results({account: _evidence(item["rows"],
                                         {"device_id": list({v["value"]: v for v in item["device_id"]}.values()),
                                          "ip_address": list({v["value"]: v for v in item["ip_address"]}.values())},
                                         {"max_customers": max_customers},
                                         ["A shared device or IP does not establish common control; public infrastructure is possible."])
                     for account, item in found.items()}, "shared_device_ip")
