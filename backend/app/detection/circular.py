import pandas as pd
import networkx as nx


def detect_circular_flow(transactions: pd.DataFrame):
    """
    Detect potential circular money flow.

    A circular flow is identified when money moves through
    multiple accounts and eventually returns to an account
    already present in the transaction path.
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

    df = df.dropna(
        subset=["timestamp"]
    )

    # 4. Sort transactions chronologically

    df = df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    # 5. Build directed graph

    graph = nx.DiGraph()

    for _, transaction in df.iterrows():

        sender = transaction["sender_account"]
        receiver = transaction["receiver_account"]

        graph.add_edge(
            sender,
            receiver,
            transaction_id=transaction["transaction_id"],
            amount=transaction["amount"],
            timestamp=transaction["timestamp"]
        )

    # 6. Find cycles

    cycles = list(
        nx.simple_cycles(graph)
    )

    suspicious_cycles = []

    # 7. Convert cycles into useful detection results

    for cycle in cycles:

        if len(cycle) < 3:
            continue

        cycle_transactions = []

        total_amount = 0

        for index in range(len(cycle)):

            sender = cycle[index]

            receiver = cycle[
                (index + 1) % len(cycle)
            ]

            matching_transactions = df[
                (df["sender_account"] == sender)
                &
                (df["receiver_account"] == receiver)
            ]

            if matching_transactions.empty:
                continue

            transaction = matching_transactions.iloc[0]

            cycle_transactions.append(
                transaction["transaction_id"]
            )

            total_amount += float(
                transaction["amount"]
            )

        suspicious_cycles.append({
            "pattern": "circular_flow",
            "account_count": len(cycle),
            "accounts": cycle,
            "transaction_ids": cycle_transactions,
            "total_amount": total_amount
        })

    return suspicious_cycles