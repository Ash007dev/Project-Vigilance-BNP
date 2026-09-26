"""
Dynamic Graph Updater for Project Vigilance (BNP Paribas Hackathon)

Incrementally updates the existing in-memory NetworkX MultiDiGraph without
rebuilding the graph.

Features:
- Incremental graph updates
- O(new_edges) update complexity
- Duplicate node prevention
- Multi-edge transaction preservation
- Transaction removal by transaction_id
- Efficient transaction lookup index
- Production-grade logging
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from typing import Any

import networkx as nx
import pandas as pd

from app.graph.builders.edge_builder import EdgeBuilder
from app.graph.builders.node_builder import NodeBuilder

logger = logging.getLogger(__name__)


class GraphUpdater:
    """
    Incrementally updates an existing graph.

    Maintains an in-memory transaction index so transaction removal is O(1)
    instead of scanning the graph.
    """

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph
        self.node_builder = NodeBuilder(graph)
        self.edge_builder = EdgeBuilder(graph)

        # transaction_id -> (source, target)
        self._transaction_index: dict[str, tuple[str, str]] = {}

        self._build_transaction_index()

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _valid(value: Any) -> bool:
        if pd.isna(value):
            return False
        if isinstance(value, str) and value.strip() == "":
            return False
        return True

    def _build_transaction_index(self) -> None:
        """
        Build transaction lookup once for an existing graph.
        """
        self._transaction_index.clear()

        for source, target, key, data in self.graph.edges(keys=True, data=True):
            tx_id = data.get("transaction_id", key)
            if tx_id is not None:
                self._transaction_index[str(tx_id)] = (source, target)

        logger.info(
            "Transaction index initialized with %d transactions.",
            len(self._transaction_index),
        )

    # ------------------------------------------------------------------
    # Transaction Operations
    # ------------------------------------------------------------------

    def add_transaction(self, transaction: Any) -> bool:
        """
        Add a single transaction without rebuilding the graph.

        Accepts either:
        - SQLAlchemy model
        - object with attributes
        - dictionary
        """

        def get(name: str, default: Any = None) -> Any:
            if isinstance(transaction, dict):
                return transaction.get(name, default)
            return getattr(transaction, name, default)

        tx_id = get("transaction_id") or get("id")

        if not self._valid(tx_id):
            logger.warning("Skipping transaction with missing transaction_id.")
            return False

        tx_id = str(tx_id)

        if tx_id in self._transaction_index:
            logger.debug("Transaction %s already indexed.", tx_id)
            return False

        sender = get("sender_account")
        receiver = get("receiver_account")

        if not (self._valid(sender) and self._valid(receiver)):
            logger.warning("Transaction %s missing sender/receiver.", tx_id)
            return False

        sender = str(sender)
        receiver = str(receiver)

        customer = get("customer_id")
        device = get("device_id")
        ip_address = get("ip_address")
        wallet = get("wallet_id")

        # ----------------------------
        # Create nodes safely
        # ----------------------------

        self.node_builder.add_account(sender)
        self.node_builder.add_account(receiver)

        if self._valid(customer):
            self.node_builder.add_customer(customer)
            self.node_builder.link_customer_account(customer, sender)

        if self._valid(device):
            self.node_builder.add_device(device)
            self.node_builder.link_account_device(sender, device)

        if self._valid(ip_address):
            self.node_builder.add_ip(ip_address)
            self.node_builder.link_account_ip(sender, ip_address)

        if self._valid(wallet):
            self.node_builder.add_wallet(wallet)
            self.node_builder.link_account_wallet(sender, wallet)

        created = self.edge_builder.add_transaction(
            from_account=sender,
            to_account=receiver,
            transaction_id=tx_id,
            amount=get("amount", 0.0),
            currency=get("currency", "UNKNOWN"),
            timestamp=get("timestamp", ""),
            channel=get("channel", "UNKNOWN"),
            location_country=get("location_country"),
            location_city=get("location_city"),
            is_crypto=bool(get("is_crypto", False)),
        )

        if created:
            self._transaction_index[tx_id] = (sender, receiver)

        return created

    def add_transactions(self, transactions: Iterable[Any]) -> int:
        """
        Incrementally add multiple transactions.

        Complexity: O(number of new transactions)
        """
        added = 0

        for tx in transactions:
            if self.add_transaction(tx):
                added += 1

        logger.info("Added %d new transactions.", added)
        return added

    def remove_transaction(self, transaction_id: Any) -> bool:
        """
        Remove a transaction edge by transaction_id.

        Node cleanup is intentionally avoided to preserve graph history.
        """

        if not self._valid(transaction_id):
            return False

        tx_id = str(transaction_id)

        lookup = self._transaction_index.get(tx_id)

        if lookup is None:
            logger.debug("Transaction %s not found.", tx_id)
            return False

        source, target = lookup

        if self.graph.has_edge(source, target, key=tx_id):
            self.graph.remove_edge(source, target, key=tx_id)
            self._transaction_index.pop(tx_id, None)

            logger.info("Removed transaction %s.", tx_id)
            return True

        self._transaction_index.pop(tx_id, None)
        return False

    # ------------------------------------------------------------------
    # Generic Update
    # ------------------------------------------------------------------

    def update_graph(
        self,
        transactions: Iterable[Any] | None = None,
        remove_transaction_ids: Iterable[Any] | None = None,
    ) -> dict[str, int]:
        """
        Apply incremental additions and removals.

        Returns:
            {
                "added": int,
                "removed": int
            }
        """
        added = 0
        removed = 0

        if transactions is not None:
            added = self.add_transactions(transactions)

        if remove_transaction_ids is not None:
            for tx_id in remove_transaction_ids:
                if self.remove_transaction(tx_id):
                    removed += 1

        logger.info(
            "Graph updated: added=%d removed=%d",
            added,
            removed,
        )

        return {
            "added": added,
            "removed": removed,
        }