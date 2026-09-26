"""
Dedicated Cycle Transaction Test for Project Vigilance.

Tests:
- Existing fraud cycle
- Transaction metadata
- No duplicate cycle reporting
- New cycle after dynamic update
"""

from app.graph.builder import graph_manager
from app.graph.analyzer import graph_analyzer
from tests.sample_transactions import get_sample_dataframe


def run():
    print("=" * 60)
    print("CYCLE TRANSACTION TEST")
    print("=" * 60)

    # Fresh graph
    graph_manager.clear_graph()
    graph_manager.build_graph_from_dataframe(get_sample_dataframe())

    # Existing cycle
    cycles = graph_analyzer.detect_cycles()

    print("\nExisting Cycles Found:", len(cycles))

    for i, cycle in enumerate(cycles, start=1):
        print(f"\nCycle {i}")
        print("Accounts:", " -> ".join(cycle["accounts"]))

        total_amount = 0

        for tx in cycle["transactions"]:
            total_amount += tx["amount"]

            print(
                f"  {tx['transaction_id']}: "
                f"{tx['sender']} -> {tx['receiver']} | "
                f"${tx['amount']} | {tx['channel']}"
            )

        print("Total Amount:", total_amount)

    # ------------------------------------------------------------
    # Add new transactions that create another cycle
    # A004 -> A005 -> A006 -> A004
    # ------------------------------------------------------------

    print("\nAdding another suspicious circular transaction chain...\n")

    graph_manager.update_graph([
        {
            "transaction_id": "TX006",
            "sender_account": "A004",
            "receiver_account": "A005",
            "customer_id": "C004",
            "device_id": "D004",
            "ip_address": "10.0.0.4",
            "wallet_id": "W004",
            "amount": 5000,
            "currency": "USD",
            "timestamp": "2026-09-01T14:00:00",
            "channel": "Mobile",
            "location_country": "India",
            "location_city": "Mumbai",
            "is_crypto": False,
        },
        {
            "transaction_id": "TX007",
            "sender_account": "A005",
            "receiver_account": "A006",
            "customer_id": "C005",
            "device_id": "D005",
            "ip_address": "10.0.0.5",
            "wallet_id": "W005",
            "amount": 5200,
            "currency": "USD",
            "timestamp": "2026-09-01T14:10:00",
            "channel": "Web",
            "location_country": "India",
            "location_city": "Delhi",
            "is_crypto": False,
        },
        {
            "transaction_id": "TX008",
            "sender_account": "A006",
            "receiver_account": "A004",
            "customer_id": "C006",
            "device_id": "D006",
            "ip_address": "10.0.0.6",
            "wallet_id": "W006",
            "amount": 5100,
            "currency": "USD",
            "timestamp": "2026-09-01T14:20:00",
            "channel": "ATM",
            "location_country": "India",
            "location_city": "Pune",
            "is_crypto": False,
        },
    ])

    updated_cycles = graph_analyzer.detect_cycles()

    print("Updated Cycles Found:", len(updated_cycles))

    for i, cycle in enumerate(updated_cycles, start=1):
        print(f"\nCycle {i}")
        print("Accounts:", " -> ".join(cycle["accounts"]))

        for tx in cycle["transactions"]:
            print(
                f"  {tx['transaction_id']} | "
                f"{tx['sender']} -> {tx['receiver']} | "
                f"${tx['amount']}"
            )

    print("\nGraph Statistics")
    print(graph_manager.graph_statistics())


if __name__ == "__main__":
    run()