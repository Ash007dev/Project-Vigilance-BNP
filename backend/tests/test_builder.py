from app.graph.builder import graph_manager
from tests.sample_transactions import get_sample_dataframe

graph_manager.clear_graph()

graph = graph_manager.build_graph_from_dataframe(get_sample_dataframe())

print("GRAPH BUILT")
print("Nodes:", graph.number_of_nodes())
print("Edges:", graph.number_of_edges())
print(graph_manager.graph_statistics())