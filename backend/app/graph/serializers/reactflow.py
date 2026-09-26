"""
React Flow Serializer for Project Vigilance (BNP Paribas Hackathon)

Converts a NetworkX MultiDiGraph into React Flow compatible JSON.

Output Format
-------------
{
    "nodes": [...],
    "edges": [...]
}

Node Fields
-----------
- id
- label
- node_type
- position (placeholder)

Edge Fields
-----------
- id
- source
- target
- label
- amount
- timestamp

Additional transaction metadata is preserved for downstream visualization.
"""

from __future__ import annotations

import logging
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


class ReactFlowSerializer:
    """
    Serialize a NetworkX MultiDiGraph into React Flow compatible JSON.
    """

    DEFAULT_X_SPACING = 220
    DEFAULT_Y_SPACING = 120

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _edge_label(edge: dict[str, Any]) -> str:
        """
        Create a human-readable edge label.
        """
        amount = edge.get("amount")
        currency = edge.get("currency")

        if amount is not None and currency:
            return f"{amount} {currency}"

        if amount is not None:
            return str(amount)

        return edge.get("relation", "SENDS_TO")

    # ------------------------------------------------------------------
    # Node Serialization
    # ------------------------------------------------------------------

    def _serialize_nodes(self) -> list[dict[str, Any]]:
        """
        Convert graph nodes into React Flow nodes.
        """
        nodes = []

        for index, (node_id, attrs) in enumerate(self.graph.nodes(data=True)):
            row = index // 10
            col = index % 10

            nodes.append(
                {
                    "id": str(node_id),
                    "type": "default",
                    "position": {
                        "x": col * self.DEFAULT_X_SPACING,
                        "y": row * self.DEFAULT_Y_SPACING,
                    },
                    "data": {
                        "label": attrs.get("label", str(node_id)),
                        "node_type": attrs.get("node_type", "Unknown"),
                        "metadata": attrs.get("metadata", {}),
                    },
                }
            )

        return nodes

    # ------------------------------------------------------------------
    # Edge Serialization
    # ------------------------------------------------------------------

    def _serialize_edges(self) -> list[dict[str, Any]]:
        """
        Convert MultiDiGraph edges into React Flow edges.

        Every transaction becomes an independent React Flow edge,
        preserving parallel transactions.
        """
        edges = []

        for source, target, key, attrs in self.graph.edges(keys=True, data=True):
            tx_id = attrs.get("transaction_id")

            # Ensure every edge has a unique React Flow ID
            edge_id = (
                str(tx_id)
                if tx_id is not None
                else f"{source}-{target}-{key}-{attrs.get('relation', 'EDGE')}"
            )

            edges.append(
                {
                    "id": edge_id,
                    "source": str(source),
                    "target": str(target),
                    "type": "default",
                    "label": self._edge_label(attrs),
                    "data": {
                        "transaction_id": tx_id,
                        "relation": attrs.get("relation", "SENDS_TO"),
                        "amount": attrs.get("amount"),
                        "currency": attrs.get("currency"),
                        "timestamp": attrs.get("timestamp"),
                        "channel": attrs.get("channel"),
                        "location_country": attrs.get("location_country"),
                        "location_city": attrs.get("location_city"),
                        "is_crypto": attrs.get("is_crypto"),
                    },
                }
            )

        return edges
    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def serialize(self) -> dict[str, list[dict[str, Any]]]:
        """
        Serialize the complete graph into React Flow JSON.
        """
        result = {
            "nodes": self._serialize_nodes(),
            "edges": self._serialize_edges(),
        }

        logger.info(
            "Serialized graph to React Flow: %d nodes, %d edges.",
            len(result["nodes"]),
            len(result["edges"]),
        )

        return result