import pandas as pd

from app.graph.builder import graph_manager
from tests.sample_transactions import get_sample_dataframe


def test_builder_uses_uploaded_data_columns_and_keeps_parallel_transactions():
    graph_manager.clear_graph()
    graph = graph_manager.build_graph_from_dataframe(get_sample_dataframe())

    assert graph.has_edge("A001", "A002", key="TX001")
    assert graph.has_edge("A001", "A002", key="TX004")
    assert graph["A001"]["A002"]["TX001"]["location_country"] == "India"
    assert graph["A001"]["A002"]["TX001"]["is_crypto"] is True

    assert graph.nodes["C001"]["node_type"] == "Customer"
    assert graph.nodes["W001"]["node_type"] == "Wallet"
    assert any(data["relation"] == "OWNS" for data in graph["C001"]["A001"].values())
    assert any(data["relation"] == "USES_WALLET" for data in graph["A002"]["W001"].values())


def test_builder_keeps_multiple_devices_for_one_account():
    graph_manager.clear_graph()
    graph = graph_manager.build_graph_from_dataframe(get_sample_dataframe())

    device_targets = {
        target
        for _, target, data in graph.out_edges("A001", data=True)
        if data.get("relation") == "USES_DEVICE"
    }
    assert device_targets == {"D001", "D004"}


def test_builder_handles_empty_and_invalid_rows():
    graph_manager.clear_graph()

    assert graph_manager.build_graph_from_dataframe(pd.DataFrame()).number_of_nodes() == 0

    invalid = pd.DataFrame([{"transaction_id": "TX-BAD", "amount": 10}])
    graph = graph_manager.build_graph_from_dataframe(invalid)
    assert graph.number_of_edges() == 0


def test_incremental_update_rejects_a_duplicate_transaction():
    graph_manager.clear_graph()
    row = get_sample_dataframe().iloc[0].to_dict()

    first = graph_manager.update_graph([row])
    second = graph_manager.update_graph([row])

    assert first == {"added": 1, "removed": 0}
    assert second == {"added": 0, "removed": 0}
