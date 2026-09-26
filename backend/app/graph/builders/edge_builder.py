"""
Edge Builder for Project Vigilance (BNP Paribas Hackathon)

Responsible for creating transaction relationships inside a
NetworkX MultiDiGraph while preserving every individual transaction.

Features:
- Supports multiple transactions between the same accounts
- Uses MultiDiGraph parallel edges
- Never overwrites existing transactions
- Optimized for large datasets (250k+ transactions)
- Standardized SENDS_TO relationships
- Production-grade logging
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import networkx as nx

from app.graph.models import transaction_edge

logger = logging.getLogger(__name__)


class EdgeBuilder:
    """
    Builds transaction edges inside a MultiDiGraph.

    Every transaction is stored as its own parallel edge using
    transaction_id as the edge key.
    """

    RELATION = "SENDS_TO"

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph

    @staticmethod
    def _valid(value: Any) -> bool:
        """
        Validate required values.

        Returns:
            True if value is usable.
        """
        if value is None:
            return False

        if isinstance(value, str) and value.strip() == "":
            return False

        return True

    def add_transaction(
        self,
        from_account: Any,
        to_account: Any,
        transaction_id: Any,
        amount: float,
        currency: str,
        timestamp: datetime | str,
        channel: str,
        location_country: str | None = None,
        location_city: str | None = None,
        is_crypto: bool = False,
        metadata: dict[str, Any] | None = None,
    ) -> bool:
        """
        Create a SENDS_TO transaction edge.

        Each transaction becomes its own parallel edge identified
        by transaction_id, ensuring previous transactions are never
        overwritten.

        Returns:
            True if edge was created.
            False if validation failed or transaction already exists.
        """
        if not (
            self._valid(from_account)
            and self._valid(to_account)
            and self._valid(transaction_id)
        ):
            logger.warning("Skipping transaction due to missing identifiers.")
            return False

        source = str(from_account)
        target = str(to_account)
        tx_id = str(transaction_id)

        if not (self.graph.has_node(source) and self.graph.has_node(target)):
            logger.warning(
                "Skipping transaction %s because source or target account does not exist.",
                tx_id,
            )
            return False

        # Prevent duplicate ingestion of the same transaction while
        # still allowing unlimited parallel edges between accounts.
        if self.graph.has_edge(source, target, key=tx_id):
            logger.debug("Transaction %s already exists.", tx_id)
            return False

        edge_data = transaction_edge(
            transaction_id=tx_id,
            amount=amount,
            currency=currency,
            timestamp=timestamp,
            channel=channel,
            location_country=location_country,
            location_city=location_city,
            is_crypto=is_crypto,
            metadata=metadata,
        )

        edge_data["relation"] = self.RELATION

        self.graph.add_edge(
            source,
            target,
            key=tx_id,
            **edge_data,
        )

        logger.debug(
            "Transaction added: %s (%s -> %s)",
            tx_id,
            source,
            target,
        )

        return True

    def transaction_exists(
        self,
        from_account: Any,
        to_account: Any,
        transaction_id: Any,
    ) -> bool:
        """
        Check whether a specific transaction already exists.
        """
        if not (
            self._valid(from_account)
            and self._valid(to_account)
            and self._valid(transaction_id)
        ):
            return False

        return self.graph.has_edge(
            str(from_account),
            str(to_account),
            key=str(transaction_id),
        )