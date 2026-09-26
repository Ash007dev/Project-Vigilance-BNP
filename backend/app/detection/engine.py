from collections import defaultdict
from datetime import timedelta

import networkx as nx
import pandas as pd

from app.db.database import engine


class AMLDetectionEngine:

    def __init__(self):
        self.df = self._load_transactions()

    def _load_transactions(self):
        query = """
            SELECT
                id,
                transaction_id,
                timestamp,
                sender_account,
                sender_name,
                sender_customer_id,
                receiver_account,
                receiver_name,
                receiver_customer_id,
                amount,
                currency,
                channel,
                ip_address,
                device_id,
                country,
                city,
                crypto_flag,
                crypto_wallet
            FROM transactions
            ORDER BY timestamp
        """

        with engine.connect() as connection:
            df = pd.read_sql(query, connection)

        if not df.empty:
            df["timestamp"] = pd.to_datetime(df["timestamp"])

        return df

    # =========================================================
    # 1. STRUCTURING / SMURFING
    # =========================================================

    def detect_structuring(self):

        findings = []

        if self.df.empty:
            return findings

        grouped = self.df.groupby("receiver_account")

        for receiver, group in grouped:

            if len(group) < 3:
                continue

            group = group.sort_values("timestamp")

            # Find the strongest 30-minute window
            best_window = None
            best_score = -1

            for i in range(len(group)):

                start_time = group.iloc[i]["timestamp"]

                window = group[
                    (group["timestamp"] >= start_time)
                    &
                    (
                        group["timestamp"]
                        <= start_time + timedelta(minutes=30)
                    )
                ]

                if len(window) < 3:
                    continue

                unique_senders = window[
                    "sender_account"
                ].nunique()

                if unique_senders < 3:
                    continue

                amounts = window["amount"]

                median_amount = amounts.median()

                if median_amount <= 0:
                    continue

                coefficient = (
                    amounts.std() / median_amount
                    if len(amounts) > 1
                    else 0
                )

                below_threshold = (
                    amounts < 100000
                ).sum()

                if (
                    below_threshold >= 3
                    and coefficient < 0.35
                ):

                    # Prefer the window with:
                    # 1. More transactions
                    # 2. More unique senders
                    score = (
                        len(window) * 100
                        + unique_senders
                    )

                    if score > best_score:

                        best_score = score

                        best_window = window.copy()

            # -----------------------------------------
            # Create ONE finding for this receiver
            # -----------------------------------------

            if best_window is not None:

                transaction_ids = (
                    best_window["transaction_id"]
                    .drop_duplicates()
                    .tolist()
                )

                findings.append({
                    "pattern": "STRUCTURING",
                    "severity": "HIGH",
                    "account": receiver,
                    "transaction_count": len(best_window),
                    "unique_senders": int(
                        best_window[
                            "sender_account"
                        ].nunique()
                    ),
                    "total_amount": float(
                        best_window["amount"].sum()
                    ),
                    "time_window_minutes": 30,
                    "reason": (
                        f"{best_window['sender_account'].nunique()} "
                        f"different senders transferred "
                        f"similar-sized amounts to {receiver} "
                        f"within a 30-minute period."
                    ),
                    "transaction_ids": transaction_ids,
                })

        return findings
    
    # =========================================================
    # 2. MULE ACCOUNT
    # =========================================================

    def detect_mule_accounts(self):

        findings = []

        if self.df.empty:
            return findings

        incoming = (
            self.df
            .groupby("receiver_account")
            .agg(
                incoming_count=(
                    "transaction_id",
                    "count",
                ),
                incoming_amount=(
                    "amount",
                    "sum",
                ),
            )
        )

        outgoing = (
            self.df
            .groupby("sender_account")
            .agg(
                outgoing_count=(
                    "transaction_id",
                    "count",
                ),
                outgoing_amount=(
                    "amount",
                    "sum",
                ),
            )
        )

        accounts = set(
            incoming.index
        ) | set(
            outgoing.index
        )

        for account in accounts:

            inc = incoming.loc[account] \
                if account in incoming.index \
                else None

            out = outgoing.loc[account] \
                if account in outgoing.index \
                else None

            incoming_count = (
                int(inc["incoming_count"])
                if inc is not None
                else 0
            )

            outgoing_count = (
                int(out["outgoing_count"])
                if out is not None
                else 0
            )

            incoming_amount = (
                float(inc["incoming_amount"])
                if inc is not None
                else 0
            )

            outgoing_amount = (
                float(out["outgoing_amount"])
                if out is not None
                else 0
            )

            # Mule characteristics:
            # many incoming transactions followed
            # by outgoing activity.

            if (
                incoming_count >= 3
                and outgoing_count >= 1
            ):

                findings.append({
                    "pattern": "MULE_ACCOUNT",
                    "severity": "HIGH",
                    "account": account,
                    "incoming_count": incoming_count,
                    "outgoing_count": outgoing_count,
                    "incoming_amount": incoming_amount,
                    "outgoing_amount": outgoing_amount,
                    "reason": (
                        f"Account received {incoming_count} "
                        f"transactions totaling "
                        f"{incoming_amount:.2f} and subsequently "
                        f"sent {outgoing_count} transactions "
                        f"totaling {outgoing_amount:.2f}."
                    ),
                })

        return findings

    # =========================================================
    # 3. LAYERING
    # =========================================================

    def detect_layering(self):

        findings = []

        if self.df.empty:
            return findings

        graph = nx.DiGraph()

        for _, row in self.df.iterrows():

            sender = row["sender_account"]
            receiver = row["receiver_account"]

            if pd.isna(sender) or pd.isna(receiver):
                continue

            graph.add_edge(
                sender,
                receiver,
                transaction_id=row["transaction_id"],
                amount=float(row["amount"]),
            )

        # Identify accounts that participate in
        # multi-hop transaction chains.

        for account in graph.nodes:

            successors = list(
                graph.successors(account)
            )

            if not successors:
                continue

            for first in successors:

                second_level = list(
                    graph.successors(first)
                )

                if not second_level:
                    continue

                for second in second_level:

                    if second == account:
                        continue

                    findings.append({
                        "pattern": "LAYERING",
                        "severity": "HIGH",
                        "account": account,
                        "path": [
                            account,
                            first,
                            second,
                        ],
                        "reason": (
                            f"Funds move through a multi-hop "
                            f"transaction chain: "
                            f"{account} → {first} → {second}."
                        ),
                    })

        # Remove duplicates
        unique = {}

        for finding in findings:

            key = tuple(
                finding["path"]
            )

            unique[key] = finding

        return list(unique.values())

    # =========================================================
    # 4. CIRCULAR MONEY FLOW
    # =========================================================

    def detect_circular_flow(self):

        findings = []

        if self.df.empty:
            return findings

        graph = nx.DiGraph()

        for _, row in self.df.iterrows():

            sender = row["sender_account"]
            receiver = row["receiver_account"]

            if pd.isna(sender) or pd.isna(receiver):
                continue

            graph.add_edge(
                sender,
                receiver,
            )

        try:
            cycles = nx.simple_cycles(
                graph
            )
        except Exception:
            return findings

        count = 0

        for cycle in cycles:

            if len(cycle) < 3:
                continue

            if len(cycle) > 6:
                continue

            findings.append({
                "pattern": "CIRCULAR_FLOW",
                "severity": "CRITICAL",
                "account": cycle[0],
                "path": cycle,
                "reason": (
                    "A circular transaction relationship "
                    "was detected: "
                    + " → ".join(cycle)
                    + f" → {cycle[0]}"
                ),
            })

            count += 1

            # Prevent excessive results
            if count >= 50:
                break

        return findings

    # =========================================================
    # 5. SHARED DEVICE / IP
    # =========================================================

    def detect_shared_identifiers(self):

        findings = []

        # -------------------------------
        # Shared devices
        # -------------------------------

        if "device_id" in self.df.columns:

            groups = (
                self.df[
                    self.df["device_id"].notna()
                ]
                .groupby("device_id")
            )

            for device, group in groups:

                accounts = (
                    group["sender_account"]
                    .dropna()
                    .unique()
                    .tolist()
                )

                if len(accounts) > 1:

                    findings.append({
                        "pattern": "SHARED_DEVICE",
                        "severity": "MEDIUM",
                        "identifier": device,
                        "accounts": accounts,
                        "reason": (
                            f"Device {device} was used by "
                            f"{len(accounts)} different accounts."
                        ),
                    })

        # -------------------------------
        # Shared IP addresses
        # -------------------------------

        if "ip_address" in self.df.columns:

            groups = (
                self.df[
                    self.df["ip_address"].notna()
                ]
                .groupby("ip_address")
            )

            for ip, group in groups:

                accounts = (
                    group["sender_account"]
                    .dropna()
                    .unique()
                    .tolist()
                )

                if len(accounts) > 1:

                    findings.append({
                        "pattern": "SHARED_IP",
                        "severity": "MEDIUM",
                        "identifier": ip,
                        "accounts": accounts,
                        "reason": (
                            f"IP address {ip} was associated "
                            f"with {len(accounts)} different "
                            f"sender accounts."
                        ),
                    })

        return findings

    # =========================================================
    # 6. CRYPTO ACTIVITY
    # =========================================================

    def detect_crypto_activity(self):

        findings = []

        if self.df.empty:
            return findings

        crypto = self.df[
            (
                self.df["crypto_flag"].fillna(0) == 1
            )
            |
            self.df["crypto_wallet"].notna()
            |
            self.df["channel"]
            .fillna("")
            .str.contains(
                "crypto",
                case=False,
                na=False,
            )
        ]

        if crypto.empty:
            return findings

        wallet_groups = (
            crypto
            .groupby("receiver_account")
        )

        for wallet, group in wallet_groups:

            findings.append({
                "pattern": "CRYPTO_ACTIVITY",
                "severity": "MEDIUM",
                "account": wallet,
                "transaction_count": len(group),
                "total_amount": float(
                    group["amount"].sum()
                ),
                "reason": (
                    f"{len(group)} crypto-related "
                    f"transactions totaling "
                    f"{group['amount'].sum():.2f} "
                    f"were associated with {wallet}."
                ),
            })

        return findings

    # =========================================================
    # RUN ALL DETECTIONS
    # =========================================================

    def run_all(self):

        return {
            "structuring": self.detect_structuring(),
            "mule_accounts": self.detect_mule_accounts(),
            "layering": self.detect_layering(),
            "circular_flow": self.detect_circular_flow(),
            "shared_identifiers":
                self.detect_shared_identifiers(),
            "crypto_activity":
                self.detect_crypto_activity(),
        }