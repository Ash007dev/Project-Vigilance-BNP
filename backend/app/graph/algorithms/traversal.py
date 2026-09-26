"""
Traversal Analyzer for Project Vigilance (BNP Paribas Hackathon)

Provides investigator-focused graph traversal utilities for exploring
transaction networks built on a NetworkX MultiDiGraph.

Implemented Algorithms
----------------------
- Breadth-First Search (BFS)
- Depth-First Search (DFS)
- Shortest Path
- Multi-hop Traversal
- Path reconstruction with transaction metadata

Every returned transaction includes:
- sender
- receiver
- amount
- timestamp
- channel
"""

from __future__ import annotations

import logging
from collections import deque
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


class TraversalAnalyzer:
    """
    Investigator-friendly traversal utilities for a MultiDiGraph.
    """

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _best_transaction(
        self,
        sender: str,
        receiver: str,
    ) -> dict[str, Any]:
        """
        Return the highest-value transaction between two connected nodes.

        This produces a deterministic representative edge when multiple
        parallel transactions exist.
        """
        edge_dict = self.graph.get_edge_data(sender, receiver)

        if not edge_dict:
            return {}

        best = max(
            edge_dict.values(),
            key=lambda edge: edge.get("amount", 0),
        )

        return {
            "sender": sender,
            "receiver": receiver,
            "transaction_id": best.get("transaction_id"),
            "amount": best.get("amount"),
            "currency": best.get("currency"),
            "timestamp": best.get("timestamp"),
            "channel": best.get("channel"),
            "location_country": best.get("location_country"),
            "location_city": best.get("location_city"),
            "is_crypto": best.get("is_crypto"),
        }

    # ------------------------------------------------------------------
    # BFS
    # ------------------------------------------------------------------

    def bfs(
        self,
        start_node: str,
        max_depth: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Breadth-First Search.

        Returns discovered nodes in visitation order.
        """
        if start_node not in self.graph:
            return []

        visited = {start_node}
        queue = deque([(start_node, 0)])
        result = []

        while queue:
            node, depth = queue.popleft()

            result.append(
                {
                    "node": node,
                    "depth": depth,
                    "node_type": self.graph.nodes[node].get("node_type"),
                    "label": self.graph.nodes[node].get("label"),
                }
            )

            if max_depth is not None and depth >= max_depth:
                continue

            for neighbor in self.graph.successors(node):
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, depth + 1))

        logger.debug("BFS visited %d nodes.", len(result))
        return result

    # ------------------------------------------------------------------
    # DFS
    # ------------------------------------------------------------------

    def dfs(
        self,
        start_node: str,
        max_depth: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Depth-First Search.
        """
        if start_node not in self.graph:
            return []

        visited = set()
        result = []

        def visit(node: str, depth: int) -> None:
            visited.add(node)

            result.append(
                {
                    "node": node,
                    "depth": depth,
                    "node_type": self.graph.nodes[node].get("node_type"),
                    "label": self.graph.nodes[node].get("label"),
                }
            )

            if max_depth is not None and depth >= max_depth:
                return

            for neighbor in self.graph.successors(node):
                if neighbor not in visited:
                    visit(neighbor, depth + 1)

        visit(start_node, 0)

        logger.debug("DFS visited %d nodes.", len(result))
        return result

    # ------------------------------------------------------------------
    # Shortest Path
    # ------------------------------------------------------------------

    def shortest_path(
        self,
        source: str,
        target: str,
    ) -> dict[str, Any]:
        """
        Find shortest path between two nodes.

        Returns both node path and transaction details.
        """
        if source not in self.graph or target not in self.graph:
            return {}

        try:
            nodes = nx.shortest_path(self.graph, source, target)

            return {
                "path": nodes,
                "length": len(nodes) - 1,
                "transactions": self.path_with_transaction_metadata(nodes),
            }

        except nx.NetworkXNoPath:
            logger.info("No path found from %s to %s.", source, target)
            return {}

    # ------------------------------------------------------------------
    # Multi-Hop Traversal
    # ------------------------------------------------------------------

    def multi_hop_traversal(
        self,
        start_node: str,
        hops: int = 2,
    ) -> dict[str, Any]:
        """
        Explore neighbors up to N hops.

        Returns:
            {
                "nodes": [...],
                "transactions": [...]
            }
        """
        bfs_result = self.bfs(start_node, max_depth=hops)

        discovered = {entry["node"] for entry in bfs_result}
        transactions = []

        for sender in discovered:
            for receiver in self.graph.successors(sender):
                if receiver in discovered:
                    edge_dict = self.graph.get_edge_data(sender, receiver)

                    if edge_dict:
                        for edge in edge_dict.values():
                            transactions.append(
                                {
                                    "sender": sender,
                                    "receiver": receiver,
                                    "transaction_id": edge.get("transaction_id"),
                                    "amount": edge.get("amount"),
                                    "timestamp": edge.get("timestamp"),
                                    "channel": edge.get("channel"),
                                }
                            )

        return {
            "nodes": bfs_result,
            "transactions": transactions,
        }

    # ------------------------------------------------------------------
    # Path Metadata
    # ------------------------------------------------------------------

    def path_with_transaction_metadata(
        self,
        path: list[str],
    ) -> list[dict[str, Any]]:
        """
        Convert a node path into investigator-friendly transaction details.
        """
        if len(path) < 2:
            return []

        transactions = []

        for sender, receiver in zip(path[:-1], path[1:]):
            transactions.append(self._best_transaction(sender, receiver))

        return transactions