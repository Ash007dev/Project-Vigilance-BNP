"""Detect devices or IP addresses shared by many customers.

How it works: group transactions by device and IP, then count distinct customer
IDs using each value.

Result: one ``(account, "shared_device_ip", evidence)`` tuple for each account
using an over-shared device or IP.

Example: four customers use the same device when the limit is three, so their
accounts are returned for review.
"""
from __future__ import annotations

from collections import defaultdict

import pandas as pd

from .common import _evidence, _frame, _id, _results


def detect_shared_device_ip(df: pd.DataFrame, max_customers=3):
    """Find devices or IP addresses used by too many customers."""
    records = _frame(
        df,
        (
            "transaction_id",
            "timestamp",
            "sender_account",
            "sender_customer_id",
            "device_id",
            "ip_address",
        ),
    )
    grouped = defaultdict(list)
    for row in records:
        for field in ("device_id", "ip_address"):
            identifier = _id(row[field])
            customer = _id(row["sender_customer_id"])
            if identifier and customer:
                grouped[(field, identifier)].append(row)

    flagged = defaultdict(lambda: {"rows": [], "device_id": [], "ip_address": []})
    for (field, identifier), rows in grouped.items():
        customers = {_id(row["sender_customer_id"]) for row in rows}
        if len(customers) <= max_customers:
            continue
        for row in rows:
            account = _id(row["sender_account"])
            if not account:
                continue
            flagged[account]["rows"].append(row)
            flagged[account][field].append(
                {"value": identifier, "distinct_customers": len(customers)}
            )

    findings = {}
    for account, item in flagged.items():
        findings[account] = _evidence(
            item["rows"],
            {
                "device_id": list(
                    {value["value"]: value for value in item["device_id"]}.values()
                ),
                "ip_address": list(
                    {value["value"]: value for value in item["ip_address"]}.values()
                ),
            },
            {"max_customers": max_customers},
            [
                "A shared device or IP can be legitimate, such as public Wi-Fi or "
                "a shared computer."
            ],
        )

    return _results(findings, "shared_device_ip")
