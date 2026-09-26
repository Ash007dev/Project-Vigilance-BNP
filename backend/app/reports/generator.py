"""Prepare an auditable report payload; the browser renders its PDF."""

def report_payload(snapshot: dict, account: dict, transactions: list[dict]) -> dict:
    return {"snapshot_id": snapshot["snapshot_id"], "account_id": account["account_id"],
            "score": account["score"], "risk": account["risk"],
            "indicators": account["indicators"], "transactions": transactions,
            "pattern_status": snapshot["pattern_status"],
            "audit": snapshot["audit"], "limitations": snapshot["limitations"]}
