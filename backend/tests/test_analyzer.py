from app.graph.builder import graph_manager
from app.graph.analyzer import graph_analyzer
from tests.sample_transactions import get_sample_dataframe


def run():
    graph_manager.clear_graph()
    graph_manager.build_graph_from_dataframe(get_sample_dataframe())

    print("\nBFS")
    print(graph_analyzer.get_account_network("A001"))

    print("\nShortest Path")
    print(graph_analyzer.shortest_path("A001", "A003"))

    print("\nCycles")
    print(graph_analyzer.detect_cycles())

    print("\nComponents")
    print(graph_analyzer.connected_components()["statistics"])

    print("\nDegree")
    print(graph_analyzer.degree_centrality()["A001"])

    print("\nBetweenness")
    print(graph_analyzer.betweenness_centrality()["A002"])

    print("\nPageRank")
    print(graph_analyzer.pagerank()["A001"])

    print("\nTimeline")
    print(graph_analyzer.get_account_timeline("A001"))


if __name__ == "__main__":
    run()