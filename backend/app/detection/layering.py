import pandas as pd
import msoffcrypto
import getpass
import tempfile
import os


# ============================================================
# LAYERING DETECTION CONFIGURATION
# ============================================================

MIN_ACCOUNTS = 5
TIME_WINDOW_HOURS = 2


# ============================================================
# LAYERING DETECTION FUNCTION
# ============================================================

def detect_layering(transactions: pd.DataFrame):
    """
    Detect potential layering behavior.

    A potential layering pattern is identified when multiple
    accounts are involved in transactions occurring within
    a short time window.

    Parameters
    ----------
    transactions : pd.DataFrame
        Transaction dataset.

    Returns
    -------
    list
        List of detected layering alerts.
    """

    # --------------------------------------------------------
    # 1. Required columns
    # --------------------------------------------------------

    required_columns = [
        "transaction_id",
        "timestamp",
        "sender_account",
        "receiver_account",
        "amount"
    ]

    # --------------------------------------------------------
    # 2. Validate required columns
    # --------------------------------------------------------

    missing_columns = [
        column
        for column in required_columns
        if column not in transactions.columns
    ]

    if missing_columns:
        raise ValueError(
            f"Missing required columns: {missing_columns}"
        )

    # --------------------------------------------------------
    # 3. Create a copy
    # --------------------------------------------------------

    df = transactions.copy()

    # --------------------------------------------------------
    # 4. Convert timestamp into datetime
    # --------------------------------------------------------

    df["timestamp"] = pd.to_datetime(
        df["timestamp"],
        errors="coerce"
    )

    # Remove rows where timestamp could not be converted
    df = df.dropna(
        subset=["timestamp"]
    )

    # --------------------------------------------------------
    # 5. Convert amount to numeric
    # --------------------------------------------------------

    df["amount"] = pd.to_numeric(
        df["amount"],
        errors="coerce"
    )

    # Remove rows with invalid amount
    df = df.dropna(
        subset=["amount"]
    )

    # --------------------------------------------------------
    # 6. Sort transactions chronologically
    # --------------------------------------------------------

    df = df.sort_values(
        "timestamp"
    ).reset_index(drop=True)

    suspicious_chains = []

    # --------------------------------------------------------
    # 7. Examine every transaction as a possible
    #    starting point
    # --------------------------------------------------------

    for start_index in range(len(df)):

        start_transaction = df.iloc[start_index]

        start_time = start_transaction["timestamp"]

        # Two-hour window
        end_time = (
            start_time
            + pd.Timedelta(hours=TIME_WINDOW_HOURS)
        )

        # ----------------------------------------------------
        # 8. Get transactions inside the time window
        # ----------------------------------------------------

        window = df[
            (df["timestamp"] >= start_time)
            &
            (df["timestamp"] <= end_time)
        ].copy()

        # ----------------------------------------------------
        # 9. Need at least MIN_ACCOUNTS transactions
        # ----------------------------------------------------

        if len(window) < MIN_ACCOUNTS:
            continue

        # ----------------------------------------------------
        # 10. Collect all accounts involved
        # ----------------------------------------------------

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

        # ----------------------------------------------------
        # 11. Check number of unique accounts
        # ----------------------------------------------------

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

            # Avoid duplicate overlapping alerts
            break

    return suspicious_chains


# ============================================================
# DIRECT DATASET EXECUTION
# ============================================================

if __name__ == "__main__":

    # Path to your real Excel dataset
    file_path = (
        "data/"
        "Project_Vigilance_Dataset_Password_Protected.xlsx"
    )

    print("=" * 60)
    print("LAYERING DETECTION")
    print("=" * 60)

    print("\nLoading dataset...")

    try:

        transactions = pd.read_excel(
            file_path,
            engine="openpyxl"
        )

        print("Dataset loaded successfully!")

        print(
            "\nNumber of transactions:",
            len(transactions)
        )

        print(
            "Number of columns:",
            len(transactions.columns)
        )

        print("\nColumns:")
        print(
            transactions.columns.tolist()
        )

        # ----------------------------------------------------
        # Run layering detection
        # ----------------------------------------------------

        print("\nRunning layering detection...")

        results = detect_layering(
            transactions
        )

        # ----------------------------------------------------
        # Display results
        # ----------------------------------------------------

        print("\n" + "=" * 60)
        print("LAYERING DETECTION RESULTS")
        print("=" * 60)

        if results:

            print(
                "\nPotential layering activity detected!"
            )

            for alert in results:

                print("\nPattern:")
                print(
                    alert["pattern"]
                )

                print("\nAccount count:")
                print(
                    alert["account_count"]
                )

                print("\nTransaction count:")
                print(
                    alert["transaction_count"]
                )

                print("\nWindow start:")
                print(
                    alert["window_start"]
                )

                print("\nWindow end:")
                print(
                    alert["window_end"]
                )

                print("\nAccounts:")
                print(
                    alert["accounts"]
                )

                print("\nTransaction IDs:")
                print(
                    alert["transaction_ids"]
                )

                print("\nTotal amount:")
                print(
                    alert["total_amount"]
                )

        else:

            print(
                "\nNo layering pattern detected."
            )

    except Exception as error:

        print("\nERROR:")
        print(error)