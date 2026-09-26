from types import SimpleNamespace

from app.api import graph as graph_api
from app.api.graph import serialize_for_cytoscape
from app.graph.analyzer import graph_analyzer
from app.graph.builder import graph_manager
from tests.sample_transactions import get_sample_dataframe


def test_reactflow_serializer_keeps_nodes_and_parallel_transactions():
    graph_manager.clear_graph()
    graph_manager.build_graph_from_dataframe(get_sample_dataframe())

    result = graph_analyzer.to_reactflow()

    assert any(node["data"]["node_type"] == "Account" for node in result["nodes"])
    transaction_ids = {
        edge["data"]["transaction_id"]
        for edge in result["edges"]
        if edge["data"]["transaction_id"] is not None
    }
    assert transaction_ids == {"TX001", "TX002", "TX003", "TX004"}


def test_cytoscape_serializer_matches_the_existing_frontend_contract():
    graph_manager.clear_graph()
    graph = graph_manager.build_graph_from_dataframe(get_sample_dataframe())

    result = serialize_for_cytoscape(graph)

    account = next(node for node in result["nodes"] if node["id"] == "A001")
    transaction = next(
        edge for edge in result["edges"] if edge.get("transaction_id") == "TX001"
    )
    visible_ids = {node["id"] for node in result["nodes"]}

    assert account == {"id": "A001", "type": "ACCOUNT", "label": "Account A001"}
    assert all(node["type"] != "CUSTOMER" for node in result["nodes"])
    assert all(
        edge["source"] in visible_ids and edge["target"] in visible_ids
        for edge in result["edges"]
    )
    assert transaction["relationship"] == "TRANSACTION"
    assert transaction["source"] == "A001"
    assert transaction["target"] == "A002"
    assert transaction["amount"] == 500.0


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def scalars(self):
        return self

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def execute(self, _query):
        return FakeResult(self.rows)


def test_graph_api_builds_the_frontend_response_without_global_state(monkeypatch):
    row = SimpleNamespace(**get_sample_dataframe().iloc[0].to_dict())
    monkeypatch.setattr(graph_api, "SessionLocal", lambda: FakeSession([row]))

    response = graph_api.get_relationship_graph("A001")

    assert response["status"] == "success"
    assert response["entity"] == "A001"
    assert response["edge_count"] >= 1
    assert any(
        edge["relationship"] == "TRANSACTION" for edge in response["graph"]["edges"]
    )
