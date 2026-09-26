from types import SimpleNamespace

from app.graph.builder import graph_manager


class FakeQuery:
    def __init__(self, rows):
        self.rows = rows

    def yield_per(self, _size):
        return self.rows


class FakeSession:
    def __init__(self, rows):
        self.rows = rows

    def query(self, _model):
        return FakeQuery(self.rows)


def test_database_builder_accepts_transaction_models_without_a_live_database():
    row = SimpleNamespace(
        transaction_id="TX-DB",
        sender_account="A100",
        receiver_account="A200",
        sender_customer_id="C100",
        receiver_customer_id="C200",
        device_id="D100",
        ip_address="10.10.10.10",
        crypto_wallet="W200",
        amount=250.0,
        currency="EUR",
        timestamp="2026-09-01T12:00:00",
        channel="Web",
        country="France",
        city="Paris",
        crypto_flag=1,
    )
    graph_manager.clear_graph()

    graph = graph_manager.build_graph_from_db(FakeSession([row]))

    assert graph.has_edge("A100", "A200", key="TX-DB")
    assert graph.has_edge("A200", "W200")
    assert graph["A100"]["A200"]["TX-DB"]["location_city"] == "Paris"
