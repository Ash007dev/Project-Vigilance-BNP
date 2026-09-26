"""
Centrality Analyzer for Project Vigilance (BNP Paribas Hackathon)

Computes investigator-focused importance metrics for accounts and other
entities in a NetworkX MultiDiGraph.

Implemented Algorithms
----------------------
- Degree Centrality
- Betweenness Centrality
- Closeness Centrality
- PageRank

Designed for large graphs by:
- Converting MultiDiGraph to a lightweight DiGraph view for computation.
- Supporting approximate betweenness using sampling.
- Returning reusable dictionaries for downstream Risk Engine consumption.
"""

from __future__ import annotations

import logging
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


class CentralityAnalyzer:
    """
    Computes centrality metrics for fraud-risk analysis.
    """

    def __init__(self, graph: nx.MultiDiGraph) -> None:
        self.graph = graph

    # ------------------------------------------------------------------
    # Internal Helpers
    # ------------------------------------------------------------------

    def _simple_graph(self) -> nx.DiGraph:
        """
        Convert the MultiDiGraph into a lightweight DiGraph.

        Parallel transaction edges are collapsed while preserving direction,
        which significantly improves performance for centrality algorithms.
        """
        simple = nx.DiGraph()

        simple.add_nodes_from(self.graph.nodes(data=True))
        simple.add_edges_from(self.graph.edges())

        return simple

    def _attach_node_info(
        self,
        scores: dict[str, float],
    ) -> dict[str, dict[str, Any]]:
        """
        Attach node metadata to computed scores.
        """
        result: dict[str, dict[str, Any]] = {}

        for node, score in scores.items():
            attrs = self.graph.nodes[node]

            result[node] = {
                "score": float(score),
                "node_type": attrs.get("node_type"),
                "label": attrs.get("label"),
            }

        return result

    # ------------------------------------------------------------------
    # Degree Centrality
    # ------------------------------------------------------------------

    def degree_centrality(self) -> dict[str, dict[str, Any]]:
        """
        Compute degree centrality.

        Complexity: O(V + E)
        """
        graph = self._simple_graph()

        logger.info("Computing Degree Centrality.")

        scores = nx.degree_centrality(graph)

        return self._attach_node_info(scores)

    # ------------------------------------------------------------------
    # Betweenness Centrality
    # ------------------------------------------------------------------

    def betweenness_centrality(
        self,
        approximate: bool = True,
        sample_size: int = 100,
        seed: int = 42,
    ) -> dict[str, dict[str, Any]]:
        """
        Compute betweenness centrality.

        For large graphs, approximation is strongly recommended.

        Args:
            approximate: Use sampling approximation.
            sample_size: Number of sampled nodes.
            seed: Random seed for reproducibility.
        """
        graph = self._simple_graph()

        logger.info("Computing Betweenness Centrality.")

        if graph.number_of_nodes() == 0:
            return {}

        if approximate:
            k = min(sample_size, graph.number_of_nodes())

            scores = nx.betweenness_centrality(
                graph,
                k=k,
                normalized=True,
                seed=seed,
            )
        else:
            scores = nx.betweenness_centrality(
                graph,
                normalized=True,
            )

        return self._attach_node_info(scores)

    # ------------------------------------------------------------------
    # Closeness Centrality
    # ------------------------------------------------------------------

    def closeness_centrality(self) -> dict[str, dict[str, Any]]:
        """
        Compute closeness centrality.

        Uses inward-distance interpretation for directed graphs.
        """
        graph = self._simple_graph()

        logger.info("Computing Closeness Centrality.")

        scores = nx.closeness_centrality(graph)

        return self._attach_node_info(scores)

    # ------------------------------------------------------------------
    # PageRank
    # ------------------------------------------------------------------

    def pagerank(
        self,
        alpha: float = 0.85,
        max_iter: int = 100,
        tol: float = 1e-6,
    ) -> dict[str, dict[str, Any]]:
        """
        Compute PageRank scores.

        Suitable for identifying influential accounts receiving or routing
        money through the network.
        """
        graph = self._simple_graph()

        logger.info("Computing PageRank.")

        if graph.number_of_nodes() == 0:
            return {}

        scores = nx.pagerank(
            graph,
            alpha=alpha,
            max_iter=max_iter,
            tol=tol,
        )

        return self._attach_node_info(scores)

    # ------------------------------------------------------------------
    # Combined Metrics
    # ------------------------------------------------------------------

    def compute_all(
        self,
        approximate_betweenness: bool = True,
        sample_size: int = 100,
    ) -> dict[str, Any]:
        """
        Compute every centrality metric in one call.

        Returns:
            Dictionary containing all centrality results.
        """
        logger.info("Computing all centrality metrics.")

        return {
            "degree": self.degree_centrality(),
            "betweenness": self.betweenness_centrality(
                approximate=approximate_betweenness,
                sample_size=sample_size,
            ),
            "closeness": self.closeness_centrality(),
            "pagerank": self.pagerank(),
        }