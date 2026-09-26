"""
Cycle Analyzer for Project Vigilance (BNP Paribas Hackathon)

Provides investigator-focused cycle detection utilities for identifying
circular money movement inside a NetworkX MultiDiGraph.

Features
--------
- Detect all unique circular money-flow cycles
- Detect cycles involving a specific account
- Return transaction metadata for every cycle
- Uses NetworkX cycle algorithms
- Avoids duplicate cycle reporting through canonical normalization
"""

from __future__ import annotations

import logging
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


class CycleAnalyzer:
    """
    Detect circular money-flow patterns inside a MultiDiGraph.
    """

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_cycle(cycle: list[str]) -> tuple[str, ...]:
        """
        Canonical representation of a cycle.

        Rotates the cycle so the lexicographically smallest node appears
        first, preventing duplicate reporting of the same circular path.
        """
        if not cycle:
            return tuple()

        if cycle[0] == cycle[-1]:
            cycle = cycle[:-1]

        smallest_index = min(range(len(cycle)), key=lambda i: cycle[i])
        rotated = cycle[smallest_index:] + cycle[:smallest_index]

        return tuple(rotated)

    def _best_transaction(
        self,
        sender: str,
        receiver: str,
    ) -> dict[str, Any]:
        """
        Return the highest-value transaction between two nodes.

        MultiDiGraph may contain many parallel transactions. This returns
        one deterministic representative edge.
        """
        edge_dict = self.graph.get_edge_data(sender, receiver)

        if not edge_dict:
            return {}

        edge = max(
            edge_dict.values(),
            key=lambda e: e.get("amount", 0),
        )

        return {
            "sender": sender,
            "receiver": receiver,
            "transaction_id": edge.get("transaction_id"),
            "amount": edge.get("amount"),
            "currency": edge.get("currency"),
            "timestamp": edge.get("timestamp"),
            "channel": edge.get("channel"),
            "location_country": edge.get("location_country"),
            "location_city": edge.get("location_city"),
            "is_crypto": edge.get("is_crypto"),
        }

    def _cycle_transactions(
        self,
        cycle: list[str],
    ) -> list[dict[str, Any]]:
        """
        Convert a node cycle into transaction metadata.
        """
        closed = cycle + [cycle[0]]

        transactions = []

        for sender, receiver in zip(closed[:-1], closed[1:]):
            transactions.append(self._best_transaction(sender, receiver))

        return transactions

    # ------------------------------------------------------------------
    # Public APIs
    # ------------------------------------------------------------------

    def detect_cycles(self) -> list[dict[str, Any]]:
        """
        Detect all unique circular money-flow cycles.

        Returns:
            List of cycle descriptions with transaction metadata.
        """
        unique: dict[tuple[str, ...], list[str]] = {}

        for cycle in nx.simple_cycles(self.graph):
            key = self._normalize_cycle(cycle)

            if key not in unique:
                unique[key] = list(key)

        logger.info("Detected %d unique cycles.", len(unique))

        results = []

        for nodes in unique.values():
            results.append(
                {
                    "accounts": nodes,
                    "length": len(nodes),
                    "transactions": self._cycle_transactions(nodes),
                }
            )

        return results

    def detect_account_cycles(
        self,
        account_id: str,
    ) -> list[dict[str, Any]]:
        """
        Detect cycles involving a specific account.

        Args:
            account_id: Account to investigate.

        Returns:
            List of cycles containing the account.
        """
        if account_id not in self.graph:
            return []

        account = str(account_id)

        unique: dict[tuple[str, ...], list[str]] = {}

        for cycle in nx.simple_cycles(self.graph):
            if account not in cycle:
                continue

            key = self._normalize_cycle(cycle)

            if key not in unique:
                unique[key] = list(key)

        logger.info(
            "Detected %d cycles involving account %s.",
            len(unique),
            account,
        )

        results = []

        for nodes in unique.values():
            results.append(
                {
                    "accounts": nodes,
                    "length": len(nodes),
                    "transactions": self._cycle_transactions(nodes),
                }
            )

        return results