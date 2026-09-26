"""
Timeline Analyzer for Project Vigilance (BNP Paribas Hackathon)

Provides investigator-focused chronological transaction timelines for
accounts in a NetworkX MultiDiGraph.

Implemented Features
--------------------
- Account transaction timeline
- Incoming and outgoing transactions
- Chronological sorting
- Robust timestamp handling
- Investigation-ready event format
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


class TimelineAnalyzer:
    """
    Build chronological investigation timelines for accounts.
    """

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _parse_timestamp(timestamp: Any) -> datetime:
        """
        Convert supported timestamp formats into a datetime object.

        Invalid or missing timestamps are pushed to the beginning of the
        timeline while preserving the original value in the output.
        """
        if isinstance(timestamp, datetime):
            return timestamp

        if timestamp is None:
            return datetime.min

        text = str(timestamp).strip()

        if not text:
            return datetime.min

        try:
            return datetime.fromisoformat(text.replace("Z", "+00:00"))
        except ValueError:
            pass

        formats = (
            "%Y-%m-%d %H:%M:%S",
            "%Y-%m-%d",
            "%d-%m-%Y %H:%M:%S",
            "%d/%m/%Y %H:%M:%S",
            "%d/%m/%Y",
        )

        for fmt in formats:
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue

        return datetime.min

    @staticmethod
    def _event(
        sender: str,
        receiver: str,
        edge: dict[str, Any],
        direction: str,
    ) -> dict[str, Any]:
        """
        Create a standardized timeline event.
        """
        return {
            "transaction_id": edge.get("transaction_id"),
            "sender": sender,
            "receiver": receiver,
            "amount": edge.get("amount"),
            "currency": edge.get("currency"),
            "timestamp": edge.get("timestamp"),
            "channel": edge.get("channel"),
            "location_country": edge.get("location_country"),
            "location_city": edge.get("location_city"),
            "is_crypto": edge.get("is_crypto", False),
            "direction": direction,
        }

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def get_account_timeline(
        self,
        account_id: str,
    ) -> list[dict[str, Any]]:
        """
        Return a chronological timeline for an account.

        Includes both incoming and outgoing transactions.

        Returns:
            List of events sorted by timestamp.
        """
        account = str(account_id)

        if account not in self.graph:
            logger.warning("Account %s not found.", account)
            return []

        events: list[dict[str, Any]] = []

        # Outgoing transactions
        for _, receiver, _, edge in self.graph.out_edges(
            account,
            keys=True,
            data=True,
        ):
            events.append(
                self._event(
                    sender=account,
                    receiver=receiver,
                    edge=edge,
                    direction="OUTGOING",
                )
            )

        # Incoming transactions
        for sender, _, _, edge in self.graph.in_edges(
            account,
            keys=True,
            data=True,
        ):
            events.append(
                self._event(
                    sender=sender,
                    receiver=account,
                    edge=edge,
                    direction="INCOMING",
                )
            )

        events.sort(
            key=lambda event: (
                self._parse_timestamp(event["timestamp"]),
                event.get("transaction_id") or "",
            )
        )

        logger.info(
            "Generated timeline for account %s with %d events.",
            account,
            len(events),
        )

        return events