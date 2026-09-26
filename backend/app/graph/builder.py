"""
Graph Manager (Orchestrator) for Project Vigilance (BNP Paribas Hackathon)

This module orchestrates the Graph Layer by integrating specialized
components without implementing node or edge creation logic here.

Integrated Components
---------------------
- cache.py                  -> Singleton live graph
- models.py                 -> Standardized node/edge schemas
- builders/node_builder.py  -> Node creation
- builders/edge_builder.py  -> Edge creation
- builders/updater.py       -> Incremental updates

Features
--------
- Build graph from Pandas DataFrame
- Build graph from SQLAlchemy database
- Incremental live updates
- Singleton graph management
- Graph statistics
- Production-grade logging
"""

from __future__ import annotations

import logging
from typing import Any

import networkx as nx
import pandas as pd
from sqlalchemy.orm import Session

from app.db.models import Transaction
from app.graph.builders.edge_builder import EdgeBuilder
from app.graph.builders.node_builder import NodeBuilder
from app.graph.builders.updater import GraphUpdater
from app.graph.cache import graph_cache

logger = logging.getLogger(__name__)


class GraphManager:
    """
    Orchestrates the complete Graph Layer while keeping a single
    live MultiDiGraph instance in memory.
    """

    def __init__(self) -> None:
        self.graph: nx.MultiDiGraph = graph_cache.get_graph()
        self.node_builder = NodeBuilder(self.graph)
        self.edge_builder = EdgeBuilder(self.graph)
        self.updater = GraphUpdater(self.graph)

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _value(row: pd.Series, column: str, default: Any = None) -> Any:
        """Safely fetch a DataFrame value."""
        value = row.get(column, default)
        return default if pd.isna(value) else value

    # ------------------------------------------------------------------
    # Graph Building
    # ------------------------------------------------------------------

    def build_graph_from_dataframe(self, df: pd.DataFrame) -> nx.MultiDiGraph:
        """
        Build the live graph from a Pandas DataFrame.

        Expected columns (if available):
        - transaction_id / id
        - sender_account
        - receiver_account
        - customer_id
        - device_id
        - ip_address
        - wallet_id
        - amount
        - currency
        - timestamp
        - channel
        - location_country
        - location_city
        - is_crypto
        """

        if df.empty:
            logger.warning("Received empty DataFrame.")
            return self.graph

        logger.info("Building graph from %d DataFrame rows.", len(df))

        for _, row in df.iterrows():
            sender = self._value(row, "sender_account")
            receiver = self._value(row, "receiver_account")

            if sender is not None:
                self.node_builder.add_account(sender)

            if receiver is not None:
                self.node_builder.add_account(receiver)

            customer = self._value(row, "customer_id")
            device = self._value(row, "device_id")
            ip_address = self._value(row, "ip_address")
            wallet = self._value(row, "wallet_id")

            if customer is not None:
                self.node_builder.add_customer(customer)
                if sender is not None:
                    self.node_builder.link_customer_account(customer, sender)

            if device is not None and sender is not None:
                self.node_builder.add_device(device)
                self.node_builder.link_account_device(sender, device)

            if ip_address is not None and sender is not None:
                self.node_builder.add_ip(ip_address)
                self.node_builder.link_account_ip(sender, ip_address)

            if wallet is not None and sender is not None:
                self.node_builder.add_wallet(wallet)
                self.node_builder.link_account_wallet(sender, wallet)

            self.edge_builder.add_transaction(
                from_account=sender,
                to_account=receiver,
                transaction_id=self._value(row, "transaction_id", self._value(row, "id")),
                amount=self._value(row, "amount", 0.0),
                currency=self._value(row, "currency", "UNKNOWN"),
                timestamp=self._value(row, "timestamp", ""),
                channel=self._value(row, "channel", "UNKNOWN"),
                location_country=self._value(row, "location_country"),
                location_city=self._value(row, "location_city"),
                is_crypto=bool(self._value(row, "is_crypto", False)),
            )

        # Refresh updater index after bulk build
        self.updater = GraphUpdater(self.graph)

        logger.info(
            "Graph build complete. Nodes=%d Edges=%d",
            self.graph.number_of_nodes(),
            self.graph.number_of_edges(),
        )

        return self.graph

    def build_graph_from_db(self, session: Session) -> nx.MultiDiGraph:
        """
        Build the live graph from the Transaction database table.
        """

        logger.info("Loading transactions from database.")

        transactions = session.query(Transaction).yield_per(5000)

        added = self.updater.add_transactions(transactions)

        logger.info("Database graph build complete. Added %d transactions.", added)

        return self.graph

    # ------------------------------------------------------------------
    # Incremental Updates
    # ------------------------------------------------------------------

    def update_graph(self, new_transactions: list[Any] | tuple[Any, ...]) -> dict[str, int]:
        """
        Incrementally update the existing live graph.

        The graph is never rebuilt.
        """
        logger.info("Updating live graph with %d new transactions.", len(new_transactions))
        return self.updater.update_graph(transactions=new_transactions)

    # ------------------------------------------------------------------
    # Graph Access
    # ------------------------------------------------------------------

    def get_graph(self) -> nx.MultiDiGraph:
        """Return the live graph instance."""
        return graph_cache.get_graph()

    def clear_graph(self) -> None:
        """
        Clear the live graph while preserving the singleton cache.
        """
        graph_cache.clear_graph()

        self.graph = graph_cache.get_graph()
        self.node_builder = NodeBuilder(self.graph)
        self.edge_builder = EdgeBuilder(self.graph)
        self.updater = GraphUpdater(self.graph)

        logger.info("Live graph cleared.")

    def graph_statistics(self) -> dict[str, Any]:
        """Return live graph statistics."""
        return graph_cache.graph_statistics()


# Shared singleton manager
graph_manager = GraphManager()