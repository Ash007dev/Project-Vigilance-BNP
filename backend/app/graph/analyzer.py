"""
Graph Analyzer Facade for Project Vigilance.

Thin integration layer that exposes investigator-friendly APIs while
delegating all graph algorithms to specialized modules.
"""

from __future__ import annotations

from app.graph.algorithms.centrality import CentralityAnalyzer
from app.graph.algorithms.components import ComponentAnalyzer
from app.graph.algorithms.cycles import CycleAnalyzer
from app.graph.algorithms.timeline import TimelineAnalyzer
from app.graph.algorithms.traversal import TraversalAnalyzer
from app.graph.builder import graph_manager
from app.graph.serializers.reactflow import ReactFlowSerializer


class GraphAnalyzer:
    """Facade exposing graph analysis capabilities over the live graph."""

    def __init__(self) -> None:
        self.graph = graph_manager.get_graph()
        self.traversal = TraversalAnalyzer(self.graph)
        self.cycles = CycleAnalyzer(self.graph)
        self.components = ComponentAnalyzer(self.graph)
        self.centrality = CentralityAnalyzer(self.graph)
        self.timeline = TimelineAnalyzer(self.graph)
        self.serializer = ReactFlowSerializer(self.graph)

    def _refresh(self) -> None:
        """Refresh analyzers if the live graph instance changes."""
        graph = graph_manager.get_graph()
        if graph is not self.graph:
            self.__init__()

    def get_neighbors(self, account_id: str):
        self._refresh()
        if account_id not in self.graph:
            return []
        return list(self.graph.successors(account_id))

    def get_account_network(self, account_id: str, hops: int = 2):
        self._refresh()
        return self.traversal.multi_hop_traversal(account_id, hops)

    def shortest_path(self, source: str, target: str):
        self._refresh()
        return self.traversal.shortest_path(source, target)

    def detect_cycles(self):
        self._refresh()
        return self.cycles.detect_cycles()

    def connected_components(self):
        self._refresh()
        return {
            "weak": self.components.weakly_connected_components(),
            "strong": self.components.strongly_connected_components(),
            "largest": self.components.largest_connected_component(),
            "statistics": self.components.component_statistics(),
        }

    def degree_centrality(self):
        self._refresh()
        return self.centrality.degree_centrality()

    def betweenness_centrality(
        self,
        approximate: bool = True,
        sample_size: int = 100,
    ):
        self._refresh()
        return self.centrality.betweenness_centrality(
            approximate=approximate,
            sample_size=sample_size,
        )

    def pagerank(self):
        self._refresh()
        return self.centrality.pagerank()

    def get_account_timeline(self, account_id: str):
        self._refresh()
        return self.timeline.get_account_timeline(account_id)

    def to_reactflow(self):
        self._refresh()
        return self.serializer.serialize()


graph_analyzer = GraphAnalyzer()