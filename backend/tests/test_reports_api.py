from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


OVERVIEW = {
    "total_transactions": 1,
    "flagged_transactions": 1,
    "unflagged_transactions": 0,
    "transactions": [
        {
            "transaction_id": "TX-001",
            "timestamp": "2026-09-27T10:00:00",
            "sender_account": "A-100",
            "receiver_account": "A-200",
            "amount": 12500,
            "currency": "INR",
            "status": "flagged",
            "flag_reason": "Rapid movement",
        }
    ],
}


def test_overview_report_returns_rendered_html():
    response = client.post("/api/reports/overview?format=html", json=OVERVIEW)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "TX-001" in response.text
    assert "A-100" in response.text


def test_overview_report_returns_downloadable_pdf():
    response = client.post("/api/reports/overview", json=OVERVIEW)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF")


def test_overview_report_rejects_an_invalid_payload():
    response = client.post(
        "/api/reports/overview?format=html",
        json={**OVERVIEW, "flagged_transactions": "not-a-number"},
    )

    assert response.status_code == 422
