"""
Node Builder for Project Vigilance (BNP Paribas Hackathon)

Responsible for creating and connecting graph nodes while preventing
duplicates and preserving metadata.

Features:
- Account, Customer, Device, IP, Wallet node creation
- Customer ownership relationships
- Duplicate node prevention
- Safe handling of missing values
- Pandas-based null checking
- Production-grade logging
"""

from __future__ import annotations

import logging
from typing import Any

import networkx as nx
import pandas as pd

from app.graph.models import (
    account_node,
    customer_node,
    device_node,
    ip_node,
    wallet_node,
)

logger = logging.getLogger(__name__)


class NodeBuilder:
    """
    Creates standardized nodes inside a NetworkX MultiDiGraph.
    """

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _valid(value: Any) -> bool:
        """Return True if value is usable."""
        if pd.isna(value):
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        return True

    def _add_node(self, node: dict[str, Any]) -> bool:
        """
        Add a node only if it does not already exist.

        Returns:
            True if node was created.
            False if it already existed.
        """
        node_id = node["id"]

        if self.graph.has_node(node_id):
            return False

        self.graph.add_node(node_id, **node)
        logger.debug("Created node: %s (%s)", node_id, node["node_type"])
        return True

    def _add_relationship(
        self,
        source: str,
        target: str,
        relation: str,
    ) -> None:
        """
        Create a relationship only once.
        """
        if not (self.graph.has_node(source) and self.graph.has_node(target)):
            return

        for _, _, data in self.graph.out_edges(source, data=True):
            if data.get("relation") == relation:
                return

        self.graph.add_edge(source, target, relation=relation)
        logger.debug("%s -> %s (%s)", source, target, relation)

    # ------------------------------------------------------------------
    # Public Node Creation
    # ------------------------------------------------------------------

    def add_account(
        self,
        account_id: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        if not self._valid(account_id):
            return None

        account_id = str(account_id)
        self._add_node(account_node(account_id, metadata))
        return account_id

    def add_customer(
        self,
        customer_id: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        if not self._valid(customer_id):
            return None

        customer_id = str(customer_id)
        self._add_node(customer_node(customer_id, metadata))
        return customer_id

    def add_device(
        self,
        device_id: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        if not self._valid(device_id):
            return None

        device_id = str(device_id)
        self._add_node(device_node(device_id, metadata))
        return device_id

    def add_ip(
        self,
        ip_address: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        if not self._valid(ip_address):
            return None

        ip_address = str(ip_address)
        self._add_node(ip_node(ip_address, metadata))
        return ip_address

    def add_wallet(
        self,
        wallet_id: Any,
        metadata: dict[str, Any] | None = None,
    ) -> str | None:
        if not self._valid(wallet_id):
            return None

        wallet_id = str(wallet_id)
        self._add_node(wallet_node(wallet_id, metadata))
        return wallet_id

    # ------------------------------------------------------------------
    # Relationships
    # ------------------------------------------------------------------

    def link_customer_account(
        self,
        customer_id: Any,
        account_id: Any,
    ) -> None:
        """
        Create ownership relationship:

        Customer ----OWNS----> Account
        """
        if not (self._valid(customer_id) and self._valid(account_id)):
            return

        customer = str(customer_id)
        account = str(account_id)

        self._add_relationship(customer, account, "OWNS")

    def link_account_device(
        self,
        account_id: Any,
        device_id: Any,
    ) -> None:
        if not (self._valid(account_id) and self._valid(device_id)):
            return

        self._add_relationship(str(account_id), str(device_id), "USES_DEVICE")

    def link_account_ip(
        self,
        account_id: Any,
        ip_address: Any,
    ) -> None:
        if not (self._valid(account_id) and self._valid(ip_address)):
            return

        self._add_relationship(str(account_id), str(ip_address), "USES_IP")

    def link_account_wallet(
        self,
        account_id: Any,
        wallet_id: Any,
    ) -> None:
        if not (self._valid(account_id) and self._valid(wallet_id)):
            return

        self._add_relationship(str(account_id), str(wallet_id), "USES_WALLET")