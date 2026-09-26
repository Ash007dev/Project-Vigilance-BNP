from app.graph.analyzer import graph_analyzer
from app.graph.builder import graph_manager
from tests.sample_transactions import get_sample_dataframe


def build_sample_graph():
    graph_manager.clear_graph()
    graph_manager.build_graph_from_dataframe(get_sample_dataframe())


def test_analyzer_finds_paths_components_and_scores():
    build_sample_graph()

    assert graph_analyzer.shortest_path("A001", "A003")["path"] == [
        "A001",
        "A002",
        "A003",
    ]
    assert graph_analyzer.connected_components()["statistics"]["weak_component_count"] == 1
    assert graph_analyzer.degree_centrality()["A001"]["score"] > 0
    assert graph_analyzer.pagerank()["A001"]["score"] > 0


def test_analyzer_returns_a_sorted_account_timeline():
    build_sample_graph()

    timeline = graph_analyzer.get_account_timeline("A001")

    assert [item["transaction_id"] for item in timeline] == ["TX001", "TX003", "TX004"]
    assert [item["direction"] for item in timeline] == [
        "OUTGOING",
        "INCOMING",
        "OUTGOING",
    ]


def test_analyzer_returns_empty_results_for_unknown_accounts():
    build_sample_graph()

    assert graph_analyzer.get_neighbors("missing") == []
    assert graph_analyzer.shortest_path("missing", "A001") == {}
    assert graph_analyzer.get_account_timeline("missing") == []
