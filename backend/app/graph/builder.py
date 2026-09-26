"""Build and update the shared relationship graph.

How it works: translate uploaded rows or database models into standard nodes
and edges. Result: analysis code sees one consistent graph. Example: a row from
the uploaded Excel file becomes an account-to-account transaction edge.
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
    """Manage the single live MultiDiGraph used by graph analysis."""

    def __init__(self) -> None:
        self.graph: nx.MultiDiGraph = graph_cache.get_graph()
        self.node_builder = NodeBuilder(self.graph)
        self.edge_builder = EdgeBuilder(self.graph)
        self.updater = GraphUpdater(self.graph)

    @staticmethod
    def _value(row: pd.Series, column: str, default: Any = None) -> Any:
        """Safely fetch a DataFrame value."""
        value = row.get(column, default)
        return default if pd.isna(value) else value

    @classmethod
    def _first_value(
        cls,
        row: pd.Series,
        *columns: str,
        default: Any = None,
    ) -> Any:
        """Return the first non-empty value from compatible column names."""
        for column in columns:
            value = cls._value(row, column)
            if value is not None and (not isinstance(value, str) or value.strip()):
                return value
        return default

    @staticmethod
    def _as_bool(value: Any) -> bool:
        """Read common spreadsheet and database boolean values."""
        if isinstance(value, str):
            return value.strip().lower() in {"1", "true", "yes", "y"}
        return bool(value) if value is not None and not pd.isna(value) else False

    def build_graph_from_dataframe(self, df: pd.DataFrame) -> nx.MultiDiGraph:
        """Build the live graph from cleaned upload rows."""

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

            sender_customer = self._first_value(
                row,
                "sender_customer_id",
                "sender_customer",
                "customer_id",
            )
            receiver_customer = self._first_value(
                row,
                "receiver_customer_id",
                "receiver_customer",
            )
            device = self._value(row, "device_id")
            ip_address = self._value(row, "ip_address")
            legacy_wallet = self._value(row, "wallet_id")
            crypto_wallet = self._value(row, "crypto_wallet")

            if sender_customer is not None:
                self.node_builder.add_customer(sender_customer)
                if sender is not None:
                    self.node_builder.link_customer_account(sender_customer, sender)

            if receiver_customer is not None:
                self.node_builder.add_customer(receiver_customer)
                if receiver is not None:
                    self.node_builder.link_customer_account(receiver_customer, receiver)

            if device is not None and sender is not None:
                self.node_builder.add_device(device)
                self.node_builder.link_account_device(sender, device)

            if ip_address is not None and sender is not None:
                self.node_builder.add_ip(ip_address)
                self.node_builder.link_account_ip(sender, ip_address)

            if legacy_wallet is not None and sender is not None:
                self.node_builder.add_wallet(legacy_wallet)
                self.node_builder.link_account_wallet(sender, legacy_wallet)

            if crypto_wallet is not None and receiver is not None:
                self.node_builder.add_wallet(crypto_wallet)
                self.node_builder.link_account_wallet(receiver, crypto_wallet)

            self.edge_builder.add_transaction(
                from_account=sender,
                to_account=receiver,
                transaction_id=self._value(row, "transaction_id", self._value(row, "id")),
                amount=self._value(row, "amount", 0.0),
                currency=self._value(row, "currency", "UNKNOWN"),
                timestamp=self._value(row, "timestamp", ""),
                channel=self._value(row, "channel", "UNKNOWN"),
                location_country=self._first_value(row, "location_country", "country"),
                location_city=self._first_value(row, "location_city", "city"),
                is_crypto=self._as_bool(
                    self._first_value(row, "is_crypto", "crypto_flag", default=False)
                ),
            )

        # Refresh the transaction lookup after adding all rows.
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

    def update_graph(self, new_transactions: list[Any] | tuple[Any, ...]) -> dict[str, int]:
        """
        Incrementally update the existing live graph.

        The graph is never rebuilt.
        """
        logger.info("Updating live graph with %d new transactions.", len(new_transactions))
        return self.updater.update_graph(transactions=new_transactions)

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
