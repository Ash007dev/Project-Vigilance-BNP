from fastapi import APIRouter, HTTPException
from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Transaction
from app.detection.engine import AMLDetectionEngine
from app.risk.engine import RiskEngine

router = APIRouter()


@router.get("/investigations/{account}")
def get_investigation(account: str):
    # -----------------------------
    # 1. Run detection + risk engine
    # -----------------------------
    detection_engine = AMLDetectionEngine()
    detection_results = detection_engine.run_all()

    risk_engine = RiskEngine(detection_results)
    risk_scores = risk_engine.calculate()

    risk_data = next(
        (item for item in risk_scores if item["account"] == account),
        None,
    )

    if not risk_data:
        raise HTTPException(
            status_code=404,
            detail=f"No investigation data found for {account}",
        )

    # -----------------------------
    # 2. Get transactions
    # -----------------------------
    with SessionLocal() as session:
        query = select(Transaction).where(
            (Transaction.sender_account == account)
            | (Transaction.receiver_account == account)
            | (Transaction.crypto_wallet == account)
        )

        transactions = session.execute(query).scalars().all()

    # -----------------------------
    # 3. Remove duplicate transactions
    # -----------------------------
    #
    # transaction_id is not the database primary key.
    # Some datasets can contain duplicate rows with the
    # same transaction_id, so only keep the first occurrence.
    #
    seen_transaction_ids = set()
    unique_transactions = []

    for tx in transactions:
        if tx.transaction_id in seen_transaction_ids:
            continue

        seen_transaction_ids.add(tx.transaction_id)

        unique_transactions.append(
            {
                "transaction_id": tx.transaction_id,
                "timestamp": tx.timestamp,
                "sender_account": tx.sender_account,
                "sender_name": tx.sender_name,
                "receiver_account": tx.receiver_account,
                "receiver_name": tx.receiver_name,
                "amount": tx.amount,
                "currency": tx.currency,
                "channel": tx.channel,
                "ip_address": tx.ip_address,
                "device_id": tx.device_id,
                "country": tx.country,
                "city": tx.city,
                "crypto_flag": tx.crypto_flag,
                "crypto_wallet": tx.crypto_wallet,
            }
        )

    # -----------------------------
    # 4. Build timeline
    # -----------------------------
    timeline = sorted(
        unique_transactions,
        key=lambda x: x["timestamp"],
    )

    # -----------------------------
    # 5. Find connected accounts
    # -----------------------------
    connected_accounts = set()
    connected_devices = set()
    connected_ips = set()
    connected_wallets = set()

    for tx in unique_transactions:

        if (
            tx["sender_account"]
            and tx["sender_account"] != account
        ):
            connected_accounts.add(tx["sender_account"])

        if (
            tx["receiver_account"]
            and tx["receiver_account"] != account
        ):
            connected_accounts.add(tx["receiver_account"])

        if tx["device_id"]:
            connected_devices.add(tx["device_id"])

        if tx["ip_address"]:
            connected_ips.add(tx["ip_address"])

        if tx["crypto_wallet"]:
            connected_wallets.add(tx["crypto_wallet"])

    # -----------------------------
    # 6. Investigation response
    # -----------------------------
    return {
        "status": "success",

        "entity": {
            "account": account,
            "risk_score": risk_data["risk_score"],
            "risk_level": risk_data["risk_level"],
        },

        "patterns": risk_data["patterns"],

        "reasons": risk_data["reasons"],

        "transactions": unique_transactions,

        "timeline": timeline,

        "relationships": {
            "accounts": sorted(connected_accounts),
            "devices": sorted(connected_devices),
            "ips": sorted(connected_ips),
            "crypto_wallets": sorted(connected_wallets),
        },

        "summary": {
            "transaction_count": len(unique_transactions),
            "connected_account_count": len(connected_accounts),
            "device_count": len(connected_devices),
            "ip_count": len(connected_ips),
            "crypto_wallet_count": len(connected_wallets),
        },
    }