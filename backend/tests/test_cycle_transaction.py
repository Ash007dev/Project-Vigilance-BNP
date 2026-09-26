from app.graph.analyzer import graph_analyzer
from app.graph.builder import graph_manager
from tests.sample_transactions import get_sample_dataframe


def test_cycle_detection_returns_accounts_and_transaction_evidence_once():
    graph_manager.clear_graph()
    graph_manager.build_graph_from_dataframe(get_sample_dataframe())

    cycles = graph_analyzer.detect_cycles()
    account_cycle = next(
        item for item in cycles if set(item["accounts"]) == {"A001", "A002", "A003"}
    )

    assert account_cycle["length"] == 3
    assert {item["transaction_id"] for item in account_cycle["transactions"]} == {
        "TX002",
        "TX003",
        "TX004",
    }
    assert sum(
        set(item["accounts"]) == {"A001", "A002", "A003"} for item in cycles
    ) == 1
