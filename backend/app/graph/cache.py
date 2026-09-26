"""
Thread-safe Singleton Graph Cache for Project Vigilance (BNP Paribas Hackathon)

Maintains exactly one live NetworkX MultiDiGraph instance in memory.

Features:
- Singleton graph instance
- Thread-safe access using threading.Lock
- Graph reset support
- Graph existence check
- Graph statistics (nodes, edges, density)
- Production-ready logging
"""

from __future__ import annotations

import logging
import threading
from typing import Any

import networkx as nx

logger = logging.getLogger(__name__)


class GraphCache:
    """Thread-safe singleton cache for the application's live graph."""

    _instance: GraphCache | None = None
    _instance_lock = threading.Lock()

    def __new__(cls) -> GraphCache:
        if cls._instance is None:
            with cls._instance_lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._graph = nx.MultiDiGraph()
                    cls._instance._graph_lock = threading.Lock()
                    logger.info("GraphCache singleton initialized.")
        return cls._instance

    def get_graph(self) -> nx.MultiDiGraph:
        """
        Return the single live graph instance.

        Returns:
            nx.MultiDiGraph: The cached graph.
        """
        return self._graph

    def clear_graph(self) -> None:
        """
        Reset the cached graph to a new empty MultiDiGraph.
        """
        with self._graph_lock:
            self._graph = nx.MultiDiGraph()
            logger.info("Graph cache cleared.")

    def graph_exists(self) -> bool:
        """
        Check whether the graph contains any nodes or edges.

        Returns:
            bool: True if graph is non-empty.
        """
        graph = self._graph
        return graph.number_of_nodes() > 0 or graph.number_of_edges() > 0

    def graph_statistics(self) -> dict[str, Any]:
        """
        Return graph statistics.

        Returns:
            dict[str, Any]:
                {
                    "total_nodes": int,
                    "total_edges": int,
                    "graph_density": float
                }
        """
        graph = self._graph

        with self._graph_lock:
            nodes = graph.number_of_nodes()
            edges = graph.number_of_edges()

            density = 0.0
            if nodes > 1:
                density = nx.density(graph)

            stats = {
                "total_nodes": nodes,
                "total_edges": edges,
                "graph_density": round(density, 6),
            }

        logger.debug("Graph statistics: %s", stats)
        return stats


# Singleton instance used across the application.
graph_cache = GraphCache()