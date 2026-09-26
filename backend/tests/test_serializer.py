import json

from app.graph.builder import graph_manager
from app.graph.analyzer import graph_analyzer
from tests.sample_transactions import get_sample_dataframe

graph_manager.clear_graph()
graph_manager.build_graph_from_dataframe(get_sample_dataframe())

rf = graph_analyzer.to_reactflow()

with open("reactflow_output.json", "w") as f:
    json.dump(rf, f, indent=2)

print("Nodes:", len(rf["nodes"]))
print("Edges:", len(rf["edges"]))
print("reactflow_output.json generated")