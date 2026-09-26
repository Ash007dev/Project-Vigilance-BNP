"""
Component Analyzer for Project Vigilance (BNP Paribas Hackathon)

Provides investigator-focused component analysis utilities for exploring
connected groups inside a NetworkX MultiDiGraph.

Implemented Features
--------------------
- Weakly Connected Components
- Strongly Connected Components
- Fraud Ring Discovery
- Component Statistics
- Largest Connected Component

Returns grouped nodes in investigator-friendly structures suitable for
fraud investigations and AML analysis.
"""

from __future__ import annotations

import logging
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


class ComponentAnalyzer:
    """
    Analyze connected groups inside a transaction graph.
    """

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _component_summary(self, nodes: set[str]) -> dict[str, Any]:
        """
        Build investigator-friendly component information.
        """
        subgraph = self.graph.subgraph(nodes)

        node_types: dict[str, int] = {}

        for node in nodes:
            node_type = self.graph.nodes[node].get("node_type", "Unknown")
            node_types[node_type] = node_types.get(node_type, 0) + 1

        return {
            "nodes": sorted(nodes),
            "node_count": len(nodes),
            "edge_count": subgraph.number_of_edges(),
            "node_types": node_types,
        }

    # ------------------------------------------------------------------
    # Weakly Connected Components
    # ------------------------------------------------------------------

    def weakly_connected_components(self) -> list[dict[str, Any]]:
        """
        Return all weakly connected components sorted by size.
        """
        components = sorted(
            nx.weakly_connected_components(self.graph),
            key=len,
            reverse=True,
        )

        logger.info("Found %d weakly connected components.", len(components))

        return [self._component_summary(component) for component in components]

    # ------------------------------------------------------------------
    # Strongly Connected Components
    # ------------------------------------------------------------------

    def strongly_connected_components(self) -> list[dict[str, Any]]:
        """
        Return all strongly connected components sorted by size.
        """
        components = sorted(
            nx.strongly_connected_components(self.graph),
            key=len,
            reverse=True,
        )

        logger.info("Found %d strongly connected components.", len(components))

        return [self._component_summary(component) for component in components]

    # ------------------------------------------------------------------
    # Largest Component
    # ------------------------------------------------------------------

    def largest_connected_component(self) -> dict[str, Any]:
        """
        Return the largest weakly connected component.
        """
        components = list(nx.weakly_connected_components(self.graph))

        if not components:
            return {}

        largest = max(components, key=len)

        logger.info("Largest component contains %d nodes.", len(largest))

        return self._component_summary(largest)

    # ------------------------------------------------------------------
    # Fraud Ring Discovery
    # ------------------------------------------------------------------

    def fraud_ring_discovery(
        self,
        min_accounts: int = 3,
        min_transactions: int = 3,
    ) -> list[dict[str, Any]]:
        """
        Discover suspicious transaction groups.

        A fraud ring is identified as a strongly connected component
        meeting minimum size and transaction thresholds.
        """
        rings = []

        for component in nx.strongly_connected_components(self.graph):
            if len(component) < min_accounts:
                continue

            subgraph = self.graph.subgraph(component)

            if subgraph.number_of_edges() < min_transactions:
                continue

            rings.append(
                {
                    "accounts": sorted(component),
                    "account_count": len(component),
                    "transaction_count": subgraph.number_of_edges(),
                    "density": round(nx.density(subgraph), 4),
                    "node_types": self._component_summary(component)["node_types"],
                }
            )

        rings.sort(
            key=lambda ring: (
                ring["account_count"],
                ring["transaction_count"],
            ),
            reverse=True,
        )

        logger.info("Detected %d potential fraud rings.", len(rings))

        return rings

    # ------------------------------------------------------------------
    # Component Statistics
    # ------------------------------------------------------------------

    def component_statistics(self) -> dict[str, Any]:
        """
        Return overall component statistics.
        """
        weak_components = list(nx.weakly_connected_components(self.graph))
        strong_components = list(nx.strongly_connected_components(self.graph))

        largest_weak = max((len(component) for component in weak_components), default=0)
        largest_strong = max((len(component) for component in strong_components), default=0)

        stats = {
            "weak_component_count": len(weak_components),
            "strong_component_count": len(strong_components),
            "largest_weak_component": largest_weak,
            "largest_strong_component": largest_strong,
            "isolated_nodes": sum(
                1 for component in weak_components if len(component) == 1
            ),
        }

        logger.debug("Component statistics: %s", stats)

        return stats