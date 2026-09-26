from fastapi import APIRouter
from sqlalchemy import text

from app.db.database import engine


router = APIRouter()


@router.get("/stats")
def dataset_stats():

    with engine.connect() as connection:

        # --------------------------------
        # Basic transaction statistics
        # --------------------------------

        basic = connection.execute(
            text(
                """
                SELECT
                    COUNT(*) AS total_transactions,
                    COUNT(DISTINCT sender_account) AS unique_senders,
                    COUNT(DISTINCT receiver_account) AS unique_receivers,
                    COUNT(DISTINCT sender_account)
                        + COUNT(DISTINCT receiver_account) AS account_references,
                    COALESCE(SUM(amount), 0) AS total_amount,
                    COALESCE(AVG(amount), 0) AS average_amount,
                    COALESCE(MIN(amount), 0) AS minimum_amount,
                    COALESCE(MAX(amount), 0) AS maximum_amount,
                    MIN(timestamp) AS first_transaction,
                    MAX(timestamp) AS last_transaction
                FROM transactions
                """
            )
        ).mappings().one()

        # --------------------------------
        # Currency distribution
        # --------------------------------

        currencies = connection.execute(
            text(
                """
                SELECT
                    COALESCE(currency, 'UNKNOWN') AS currency,
                    COUNT(*) AS transaction_count,
                    COALESCE(SUM(amount), 0) AS total_amount
                FROM transactions
                GROUP BY currency
                ORDER BY transaction_count DESC
                """
            )
        ).mappings().all()

        # --------------------------------
        # Channel distribution
        # --------------------------------

        channels = connection.execute(
            text(
                """
                SELECT
                    COALESCE(channel, 'UNKNOWN') AS channel,
                    COUNT(*) AS transaction_count,
                    COALESCE(SUM(amount), 0) AS total_amount
                FROM transactions
                GROUP BY channel
                ORDER BY transaction_count DESC
                """
            )
        ).mappings().all()

        # --------------------------------
        # Crypto statistics
        # --------------------------------

        crypto = connection.execute(
            text(
                """
                SELECT
                    COUNT(*) FILTER (
                        WHERE crypto_flag = 1
                           OR crypto_wallet IS NOT NULL
                           OR channel ILIKE '%crypto%'
                    ) AS crypto_transactions,

                    COUNT(DISTINCT crypto_wallet) FILTER (
                        WHERE crypto_wallet IS NOT NULL
                    ) AS unique_crypto_wallets

                FROM transactions
                """
            )
        ).mappings().one()

        # --------------------------------
        # Top sender accounts
        # --------------------------------

        top_senders = connection.execute(
            text(
                """
                SELECT
                    sender_account,
                    COUNT(*) AS transaction_count,
                    COALESCE(SUM(amount), 0) AS total_sent
                FROM transactions
                GROUP BY sender_account
                ORDER BY transaction_count DESC
                LIMIT 10
                """
            )
        ).mappings().all()

        # --------------------------------
        # Top receiver accounts
        # --------------------------------

        top_receivers = connection.execute(
            text(
                """
                SELECT
                    receiver_account,
                    COUNT(*) AS transaction_count,
                    COALESCE(SUM(amount), 0) AS total_received
                FROM transactions
                GROUP BY receiver_account
                ORDER BY transaction_count DESC
                LIMIT 10
                """
            )
        ).mappings().all()

        # --------------------------------
        # Shared device statistics
        # --------------------------------

        shared_devices = connection.execute(
            text(
                """
                SELECT
                    COUNT(*) AS shared_devices
                FROM (
                    SELECT device_id
                    FROM transactions
                    WHERE device_id IS NOT NULL
                    GROUP BY device_id
                    HAVING COUNT(DISTINCT sender_account) > 1
                ) d
                """
            )
        ).scalar_one()

        # --------------------------------
        # Shared IP statistics
        # --------------------------------

        shared_ips = connection.execute(
            text(
                """
                SELECT
                    COUNT(*) AS shared_ips
                FROM (
                    SELECT ip_address
                    FROM transactions
                    WHERE ip_address IS NOT NULL
                    GROUP BY ip_address
                    HAVING COUNT(DISTINCT sender_account) > 1
                ) i
                """
            )
        ).scalar_one()

    return {
        "dataset": {
            "total_transactions": basic["total_transactions"],
            "unique_senders": basic["unique_senders"],
            "unique_receivers": basic["unique_receivers"],
            "total_amount": float(basic["total_amount"]),
            "average_amount": float(basic["average_amount"]),
            "minimum_amount": float(basic["minimum_amount"]),
            "maximum_amount": float(basic["maximum_amount"]),
            "first_transaction": basic["first_transaction"],
            "last_transaction": basic["last_transaction"],
        },
        "currencies": [
            {
                "currency": row["currency"],
                "transaction_count": row["transaction_count"],
                "total_amount": float(row["total_amount"]),
            }
            for row in currencies
        ],
        "channels": [
            {
                "channel": row["channel"],
                "transaction_count": row["transaction_count"],
                "total_amount": float(row["total_amount"]),
            }
            for row in channels
        ],
        "crypto": {
            "crypto_transactions": crypto["crypto_transactions"],
            "unique_crypto_wallets": crypto["unique_crypto_wallets"],
        },
        "network": {
            "shared_devices": shared_devices,
            "shared_ips": shared_ips,
        },
        "top_senders": [
            {
                "account": row["sender_account"],
                "transaction_count": row["transaction_count"],
                "total_sent": float(row["total_sent"]),
            }
            for row in top_senders
        ],
        "top_receivers": [
            {
                "account": row["receiver_account"],
                "transaction_count": row["transaction_count"],
                "total_received": float(row["total_received"]),
            }
            for row in top_receivers
        ],
    }