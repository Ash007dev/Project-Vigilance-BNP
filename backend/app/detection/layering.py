import pandas as pd


MIN_ACCOUNTS = 5
TIME_WINDOW_HOURS = 2


def detect_layering(transactions: pd.DataFrame):
    """
    Detect potential layering behavior.

    A potential layering pattern is identified when money
    moves through multiple accounts within a short time window.
    """

    required_columns = [
        "transaction_id",
        "timestamp",
        "sender_account",
        "receiver_account",
        "amount"
    ]

    # 1. Validate required columns

    missing_columns = [
        column
        for column in required_columns
        if column not in transactions.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # 2. Work on a copy

    df = transactions.copy()

    # 3. Convert timestamp

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    # Remove invalid timestamps
    df = df.dropna(subset=["timestamp"])

    # 4. Sort transactions chronologically

    df = df.sort_values("timestamp").reset_index(drop=True)

    suspicious_chains = []

    # 5. Examine every transaction as a possible
    #    starting point

    for start_index in range(len(df)):

        start_transaction = df.iloc[start_index]

        start_time = start_transaction["timestamp"]

        end_time = (
            start_time +
            pd.Timedelta(hours=TIME_WINDOW_HOURS)
        )

        # Transactions occurring inside the time window

        window = df[
            (df["timestamp"] >= start_time)
            &
            (df["timestamp"] <= end_time)
        ].copy()

        if len(window) < MIN_ACCOUNTS:
            continue

    
        # Build the account relationship chain

        accounts = set()

        transaction_ids = []

        for _, transaction in window.iterrows():

            sender = transaction["sender_account"]
            receiver = transaction["receiver_account"]

            accounts.add(sender)
            accounts.add(receiver)

            transaction_ids.append(
                transaction["transaction_id"]
            )

        # Check whether enough accounts are involved

        if len(accounts) >= MIN_ACCOUNTS:

            suspicious_chains.append({
                "pattern": "layering",
                "account_count": len(accounts),
                "transaction_count": len(window),
                "window_start": start_time,
                "window_end": end_time,
                "transaction_ids": transaction_ids,
                "accounts": list(accounts),
                "total_amount": float(
                    window["amount"].sum()
                )
            })

            # Avoid returning the same overlapping windowrepeatedly.
            break

    return suspicious_chains