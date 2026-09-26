from app.graph.builder import graph_manager
from app.graph.analyzer import graph_analyzer
from tests.sample_transactions import get_sample_dataframe

graph_manager.clear_graph()
graph_manager.build_graph_from_dataframe(get_sample_dataframe())

print("Before Update")
print(graph_manager.graph_statistics())

graph_manager.update_graph([
    {
        "transaction_id": "TX005",
        "sender_account": "A003",
        "receiver_account": "A004",
        "customer_id": "C004",
        "device_id": "D004",
        "ip_address": "10.0.0.4",
        "wallet_id": "W004",
        "amount": 2500,
        "currency": "USD",
        "timestamp": "2026-09-01T13:00:00",
        "channel": "Mobile",
        "location_country": "India",
        "location_city": "Mumbai",
        "is_crypto": False,
    }
])

print("After Update")
print(graph_manager.graph_statistics())

print("Timeline A003")
print(graph_analyzer.get_account_timeline("A003"))

rf = graph_analyzer.to_reactflow()
print("ReactFlow:", len(rf["nodes"]), len(rf["edges"]))