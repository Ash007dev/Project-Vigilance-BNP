from fastapi import APIRouter, HTTPException

from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Transaction

from app.detection.engine import AMLDetectionEngine
from app.risk.engine import RiskEngine

from app.ai.explainer import AIExplainer


router = APIRouter()


@router.get("/ai/explanation/{account}")
def get_ai_explanation(account: str):

    # ---------------------------------------------------------
    # RUN DETECTION
    # ---------------------------------------------------------

    detection_engine = AMLDetectionEngine()

    detection_results = detection_engine.run_all()

    # ---------------------------------------------------------
    # RUN RISK ENGINE
    # ---------------------------------------------------------

    risk_engine = RiskEngine(
        detection_results
    )

    risk_scores = risk_engine.calculate()

    entity_risk = None

    for item in risk_scores:

        if item["account"] == account:
            entity_risk = item
            break

    if entity_risk is None:

        raise HTTPException(
            status_code=404,
            detail=f"No risk information found for {account}",
        )

    # ---------------------------------------------------------
    # GET TRANSACTIONS
    # ---------------------------------------------------------

    db = SessionLocal()

    try:

        statement = (
            select(Transaction)
            .where(
                (Transaction.sender_account == account)
                |
                (Transaction.receiver_account == account)
                |
                (Transaction.crypto_wallet == account)
            )
            .order_by(Transaction.timestamp.asc())
        )

        rows = db.execute(statement).scalars().all()

        # -----------------------------------------------------
        # DEDUPLICATE TRANSACTIONS
        # -----------------------------------------------------

        unique_transactions = {}

        for tx in rows:

            if tx.transaction_id not in unique_transactions:

                unique_transactions[
                    tx.transaction_id
                ] = tx

        transactions = list(
            unique_transactions.values()
        )

    finally:

        db.close()

    # ---------------------------------------------------------
    # TRANSACTION EVIDENCE
    # ---------------------------------------------------------

    transaction_evidence = []

    for tx in transactions:

        transaction_evidence.append(
            {
                "transaction_id": tx.transaction_id,
                "timestamp": tx.timestamp,
                "sender": tx.sender_account,
                "receiver": tx.receiver_account,
                "amount": tx.amount,
                "currency": tx.currency,
                "channel": tx.channel,
                "device": tx.device_id,
                "ip": tx.ip_address,
                "country": tx.country,
                "city": tx.city,
                "crypto_flag": tx.crypto_flag,
                "crypto_wallet": tx.crypto_wallet,
            }
        )

    # ---------------------------------------------------------
    # TIMELINE SUMMARY
    # ---------------------------------------------------------

    timeline = []

    for tx in transactions:

        timeline.append(
            {
                "timestamp": tx.timestamp,
                "transaction_id": tx.transaction_id,
                "amount": tx.amount,
                "currency": tx.currency,
                "sender": tx.sender_account,
                "receiver": tx.receiver_account,
            }
        )

    # ---------------------------------------------------------
    # NETWORK EVIDENCE
    # ---------------------------------------------------------

    connected_accounts = set()
    devices = set()
    ips = set()
    wallets = set()

    for tx in transactions:

        if tx.sender_account and tx.sender_account != account:
            connected_accounts.add(
                tx.sender_account
            )

        if tx.receiver_account and tx.receiver_account != account:
            connected_accounts.add(
                tx.receiver_account
            )

        if tx.device_id:
            devices.add(tx.device_id)

        if tx.ip_address:
            ips.add(tx.ip_address)

        if tx.crypto_wallet:
            wallets.add(tx.crypto_wallet)

    network = {
        "connected_accounts": sorted(
            connected_accounts
        ),
        "devices": sorted(devices),
        "ips": sorted(ips),
        "crypto_wallets": sorted(wallets),
    }

    # ---------------------------------------------------------
    # COMPLETE EVIDENCE
    # ---------------------------------------------------------

    evidence = {

        "entity": {
            "account": account,
            "risk_score": entity_risk["risk_score"],
            "risk_level": entity_risk["risk_level"],
        },

        "patterns": entity_risk["patterns"],

        "risk_reasons": entity_risk["reasons"],

        "transaction_summary": {
            "count": len(transactions),
        },

        "network_summary": {
            "connected_accounts": len(
                connected_accounts
            ),
            "devices": len(devices),
            "ips": len(ips),
            "crypto_wallets": len(wallets),
        },

        "network": network,

        "timeline": timeline,

        "transactions": transaction_evidence,
    }

    # ---------------------------------------------------------
    # AI EXPLANATION
    # ---------------------------------------------------------

    explainer = AIExplainer()

    # ---------------------------------------------------------
    # COMPACT EVIDENCE FOR AI
    # ---------------------------------------------------------

    ai_transactions = []

    for tx in transactions[:8]:

        ai_transactions.append(
            {
                "transaction_id": tx.transaction_id,
                "timestamp": str(tx.timestamp),
                "sender": tx.sender_account,
                "receiver": tx.receiver_account,
                "amount": tx.amount,
                "currency": tx.currency,
                "channel": tx.channel,
                "device": tx.device_id,
                "ip": tx.ip_address,
                "crypto_flag": tx.crypto_flag,
                "crypto_wallet": tx.crypto_wallet,
            }
        )

    ai_evidence = {

        "entity": {
            "account": account,
            "risk_score": entity_risk["risk_score"],
            "risk_level": entity_risk["risk_level"],
        },

        "patterns": entity_risk["patterns"],

        "risk_reasons": entity_risk["reasons"],

        "transaction_summary": {
            "count": len(transactions),
            "sample_transactions": ai_transactions,
        },

        "network_summary": {
            "connected_accounts": len(
                connected_accounts
            ),
            "devices": len(devices),
            "ips": len(ips),
            "crypto_wallets": len(wallets),
        },

        "network": {
            "connected_accounts": sorted(
                list(connected_accounts)
            )[:20],

            "devices": sorted(
                list(devices)
            ),

            "ips": sorted(
                list(ips)
            ),

            "crypto_wallets": sorted(
                list(wallets)
            ),
        },
    }

    result = explainer.generate(
        ai_evidence
    )

    return {
        "status": "success",
        "entity": account,
        "risk_score": entity_risk["risk_score"],
        "risk_level": entity_risk["risk_level"],
        "patterns": entity_risk["patterns"],
        "evidence": evidence,
        "ai": result,
    }