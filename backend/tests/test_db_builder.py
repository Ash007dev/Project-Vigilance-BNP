from app.db.database import SessionLocal
from app.graph.builder import graph_manager

db = SessionLocal()

graph_manager.clear_graph()

graph = graph_manager.build_graph_from_db(db)

print("Graph built from database")

print("Nodes:", graph.number_of_nodes())
print("Edges:", graph.number_of_edges())

print(graph_manager.graph_statistics())

db.close()