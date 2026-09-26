"""
Standardized Graph Models for Project Vigilance (BNP Paribas Hackathon)

Provides reusable helper functions for creating consistent graph nodes and
transaction edges used throughout the Graph Layer.

Features:
- Standardized node schema
- Standardized transaction edge schema
- Strong type hints
- Immutable helper outputs
- Builder-friendly reusable functions
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

# ---------------------------------------------------------------------
# Node Type Constants
# ---------------------------------------------------------------------

ACCOUNT = "Account"
CUSTOMER = "Customer"
DEVICE = "Device"
IP = "IP"
WALLET = "Wallet"

VALID_NODE_TYPES = {ACCOUNT, CUSTOMER, DEVICE, IP, WALLET}


# ---------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------


def _build_node(
    node_id: str,
    node_type: str,
    label: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create a standardized graph node.

    Args:
        node_id: Unique node identifier.
        node_type: One of the supported node types.
        label: Human-readable node label.
        metadata: Optional additional node metadata.

    Returns:
        Standardized node dictionary.
    """
    if node_type not in VALID_NODE_TYPES:
        raise ValueError(f"Unsupported node type: {node_type}")

    return {
        "id": str(node_id),
        "node_type": node_type,
        "label": label,
        "metadata": metadata or {},
    }


# ---------------------------------------------------------------------
# Node Builders
# ---------------------------------------------------------------------


def account_node(
    account_id: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _build_node(account_id, ACCOUNT, f"Account {account_id}", metadata)


def customer_node(
    customer_id: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _build_node(customer_id, CUSTOMER, f"Customer {customer_id}", metadata)


def device_node(
    device_id: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _build_node(device_id, DEVICE, f"Device {device_id}", metadata)


def ip_node(
    ip_address: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _build_node(ip_address, IP, ip_address, metadata)


def wallet_node(
    wallet_id: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return _build_node(wallet_id, WALLET, f"Wallet {wallet_id}", metadata)


# ---------------------------------------------------------------------
# Transaction Edge Builder
# ---------------------------------------------------------------------


def transaction_edge(
    transaction_id: str,
    amount: float,
    currency: str,
    timestamp: datetime | str,
    channel: str,
    location_country: str | None = None,
    location_city: str | None = None,
    is_crypto: bool = False,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """
    Create standardized transaction edge attributes.

    Args:
        transaction_id: Unique transaction ID.
        amount: Transaction amount.
        currency: Currency code.
        timestamp: Transaction timestamp.
        channel: Transaction channel.
        location_country: Country where transaction occurred.
        location_city: City where transaction occurred.
        is_crypto: Whether transaction is crypto-related.
        metadata: Optional additional edge metadata.

    Returns:
        Standardized edge attribute dictionary.
    """
    ts = timestamp.isoformat() if isinstance(timestamp, datetime) else str(timestamp)

    edge = {
        "transaction_id": str(transaction_id),
        "amount": float(amount),
        "currency": str(currency),
        "timestamp": ts,
        "channel": str(channel),
        "location_country": location_country,
        "location_city": location_city,
        "is_crypto": bool(is_crypto),
    }

    if metadata:
        edge.update(metadata)

    return edge