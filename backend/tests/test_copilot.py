import json
from datetime import datetime
from types import SimpleNamespace

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api import copilot
from app.db.models import Base, Transaction
from app.main import app


client = TestClient(app)


def _transaction_session():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)

    with session_factory() as session:
        session.add_all(
            [
                Transaction(
                    transaction_id="TX-001",
                    timestamp=datetime(2026, 1, 1, 10, 0),
                    sender_account="ACC-A",
                    receiver_account="ACC-B",
                    amount=100.0,
                    currency="USD",
                    channel="WIRE",
                    crypto_flag=0,
                ),
                Transaction(
                    transaction_id="TX-002",
                    timestamp=datetime(2026, 1, 2, 10, 0),
                    sender_account="ACC-C",
                    receiver_account="ACC-A",
                    amount=200.0,
                    currency="USD",
                    channel="WIRE",
                    crypto_flag=1,
                ),
                Transaction(
                    transaction_id="TX-003",
                    timestamp=datetime(2026, 1, 3, 10, 0),
                    sender_account="ACC-A",
                    receiver_account="ACC-D",
                    amount=300.0,
                    currency="EUR",
                    channel="CRYPTO",
                    crypto_flag=1,
                ),
            ]
        )
        session.commit()

    return session_factory


def test_copilot_route_requires_api_key(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    response = client.post(
        "/api/copilot/query",
        json={"question": "Which accounts transferred the most money?"},
    )

    assert response.status_code == 503
    assert response.json() == {
        "detail": "OPENAI_API_KEY is not configured.",
    }


def test_copilot_settings_load_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "OPENAI_API_KEY=test-file-key\nOPENAI_MODEL=test-file-model\n",
        encoding="utf-8",
    )
    load_settings = getattr(copilot, "_load_settings", None)

    assert callable(load_settings), "env-file settings loader must be implemented"

    settings = load_settings(env_file)
    assert settings.openai_api_key == "test-file-key"
    assert settings.openai_model == "test-file-model"


def test_copilot_route_returns_grounded_answer(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "test-key")
    monkeypatch.setattr(
        copilot,
        "run_copilot",
        lambda question: {
            "model": "test-model",
            "answer": f"Grounded answer for: {question}",
            "tools_used": ["aggregate_transactions"],
        },
        raising=False,
    )

    response = client.post(
        "/api/copilot/query",
        json={"question": "Which accounts transferred the most money?"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "status": "success",
        "question": "Which accounts transferred the most money?",
        "model": "test-model",
        "answer": (
            "Grounded answer for: Which accounts transferred the most money?"
        ),
        "tools_used": ["aggregate_transactions"],
    }


def test_search_transactions_applies_safe_filters_sort_and_limit(monkeypatch):
    monkeypatch.setattr(
        copilot,
        "SessionLocal",
        _transaction_session(),
        raising=False,
    )
    search_transactions = getattr(copilot, "_search_transactions", None)

    assert callable(search_transactions), "search tool must be implemented"

    result = search_transactions(
        {
            "account": "ACC-A",
            "crypto": "yes",
            "sort_by": "amount",
            "sort_order": "desc",
            "limit": 1,
        }
    )

    assert result == {
        "returned_count": 1,
        "transactions": [
            {
                "transaction_id": "TX-003",
                "timestamp": "2026-01-03T10:00:00",
                "sender_account": "ACC-A",
                "receiver_account": "ACC-D",
                "amount": 300.0,
                "currency": "EUR",
                "channel": "CRYPTO",
                "country": None,
                "city": None,
                "device_id": None,
                "ip_address": None,
                "crypto_flag": 1,
                "crypto_wallet": None,
            }
        ],
    }


def test_aggregate_transactions_ranks_groups_by_metric(monkeypatch):
    monkeypatch.setattr(
        copilot,
        "SessionLocal",
        _transaction_session(),
        raising=False,
    )
    aggregate_transactions = getattr(
        copilot,
        "_aggregate_transactions",
        None,
    )

    assert callable(aggregate_transactions), "aggregate tool must be implemented"

    result = aggregate_transactions(
        {
            "group_by": "sender_account",
            "metric": "total_amount",
            "limit": 2,
        }
    )

    assert result == {
        "metric": "total_amount",
        "group_by": "sender_account",
        "results": [
            {"group": "ACC-A", "value": 400.0},
            {"group": "ACC-C", "value": 200.0},
        ],
    }


def test_run_copilot_executes_database_tool_before_answering(monkeypatch):
    monkeypatch.setattr(copilot, "SessionLocal", _transaction_session())
    monkeypatch.setenv("OPENAI_MODEL", "test-model")

    class FakeResponses:
        def __init__(self):
            self.turn = 0

        def create(self, **kwargs):
            self.turn += 1
            if self.turn == 1:
                return SimpleNamespace(
                    id="response-1",
                    output=[
                        SimpleNamespace(
                            type="function_call",
                            name="aggregate_transactions",
                            call_id="call-1",
                            arguments=json.dumps(
                                {
                                    "group_by": "sender_account",
                                    "metric": "total_amount",
                                    "limit": 2,
                                }
                            ),
                        )
                    ],
                    output_text="",
                )

            tool_result = json.loads(kwargs["input"][0]["output"])
            leader = tool_result["results"][0]
            return SimpleNamespace(
                id="response-2",
                output=[],
                output_text=(
                    f"{leader['group']} has the highest total: "
                    f"{leader['value']}."
                ),
            )

    fake_client = SimpleNamespace(responses=FakeResponses())
    monkeypatch.setattr(
        copilot,
        "_create_client",
        lambda: fake_client,
        raising=False,
    )

    result = copilot.run_copilot(
        "Which sender account transferred the highest total amount?"
    )

    assert result == {
        "model": "test-model",
        "answer": "ACC-A has the highest total: 400.0.",
        "tools_used": ["aggregate_transactions"],
    }
