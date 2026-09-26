import pandas as pd

TRANSACTION_THRESHOLD = 1_000_000
MIN_TRANSACTIONS = 5
TIME_WINDOW_HOURS = 24


def detect_structuring(transactions: pd.DataFrame):

    required_columns = [
        "transaction_id",
        "timestamp",
        "sender_account",
        "amount"
    ]

    # Check required columns
    missing_columns = [
        column for column in required_columns
        if column not in transactions.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # Work on a copy so we don't modify the original data
    df = transactions.copy()

    # Convert timestamp to datetime
    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    # Remove invalid timestamps
    df = df.dropna(subset=["timestamp"])

    # Keep transactions below the configured threshold
    df = df[
        df["amount"] < TRANSACTION_THRESHOLD
    ].copy()

    # Sort by account and timestamp
    df = df.sort_values(
        ["sender_account", "timestamp"]
    )

    suspicious_accounts = []

    # Analyze each sender account separately
    for account_id, account_transactions in df.groupby(
        "sender_account"
    ):

        account_transactions = account_transactions.reset_index(
            drop=True
        )

        # Sliding time window
        for start_index in range(
            len(account_transactions)
        ):

            start_time = account_transactions.loc[
                start_index,
                "timestamp"
            ]

            end_time = (
                start_time +
                pd.Timedelta(hours=TIME_WINDOW_HOURS)
            )

            window = account_transactions[
                (account_transactions["timestamp"] >= start_time)
                &
                (account_transactions["timestamp"] <= end_time)
            ]

            # Check whether the number of transactions crosses the configured threshold
            if len(window) > MIN_TRANSACTIONS:

                suspicious_accounts.append({
                    "account_id": account_id,
                    "pattern": "structuring",
                    "transaction_count": len(window),
                    "total_amount": float(
                        window["amount"].sum()
                    ),
                    "window_start": start_time,
                    "window_end": end_time,
                    "transaction_ids": (
                        window["transaction_id"]
                        .tolist()
                    )
                })

                # We already found suspicious behavior for this account.
                break

    return suspicious_accounts