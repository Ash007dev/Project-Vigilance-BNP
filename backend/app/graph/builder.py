import networkx as nx
from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Transaction


class RelationshipGraphBuilder:

    def build_for_account(self, account: str):
        graph = nx.MultiDiGraph()

        with SessionLocal() as session:
            query = select(Transaction).where(
                (Transaction.sender_account == account)
                | (Transaction.receiver_account == account)
                | (
                    Transaction.sender_account.in_(
                        select(Transaction.sender_account).where(
                            Transaction.receiver_account == account
                        )
                    )
                )
            )

            transactions = session.execute(query).scalars().all()

        seen_transactions = set()
        seen_relationships = set()

        for tx in transactions:

            # --------------------------------
            # Transaction edge
            # --------------------------------
            if tx.transaction_id not in seen_transactions:

                seen_transactions.add(tx.transaction_id)

                sender = tx.sender_account
                receiver = tx.receiver_account

                if not sender or not receiver:
                    continue

                graph.add_node(
                    sender,
                    type="ACCOUNT",
                )

                graph.add_node(
                    receiver,
                    type="ACCOUNT",
                )

                graph.add_edge(
                    sender,
                    receiver,
                    relationship="TRANSACTION",
                    transaction_id=tx.transaction_id,
                    amount=tx.amount,
                    currency=tx.currency,
                    timestamp=(
                        tx.timestamp.isoformat()
                        if tx.timestamp
                        else None
                    ),
                    channel=tx.channel,
                )

            else:
                sender = tx.sender_account

            # --------------------------------
            # Device relationship
            # --------------------------------
            if sender and tx.device_id:

                relationship_key = (
                    sender,
                    tx.device_id,
                    "USES_DEVICE",
                )

                if relationship_key not in seen_relationships:

                    seen_relationships.add(relationship_key)

                    graph.add_node(
                        tx.device_id,
                        type="DEVICE",
                    )

                    graph.add_edge(
                        sender,
                        tx.device_id,
                        relationship="USES_DEVICE",
                    )

            # --------------------------------
            # IP relationship
            # --------------------------------
            if sender and tx.ip_address:

                relationship_key = (
                    sender,
                    tx.ip_address,
                    "USES_IP",
                )

                if relationship_key not in seen_relationships:

                    seen_relationships.add(relationship_key)

                    graph.add_node(
                        tx.ip_address,
                        type="IP",
                    )

                    graph.add_edge(
                        sender,
                        tx.ip_address,
                        relationship="USES_IP",
                    )

            # --------------------------------
            # Crypto wallet
            # --------------------------------
            if tx.crypto_wallet and tx.receiver_account:

                relationship_key = (
                    tx.receiver_account,
                    tx.crypto_wallet,
                    "RECEIVES_CRYPTO",
                )

                if relationship_key not in seen_relationships:

                    seen_relationships.add(relationship_key)

                    graph.add_node(
                        tx.crypto_wallet,
                        type="CRYPTO_WALLET",
                    )

                    graph.add_edge(
                        tx.receiver_account,
                        tx.crypto_wallet,
                        relationship="RECEIVES_CRYPTO",
                    )

        return graph

    def serialize(self, graph: nx.MultiDiGraph):

        nodes = []

        for node, data in graph.nodes(data=True):
            nodes.append(
                {
                    "id": node,
                    "type": data.get("type", "UNKNOWN"),
                }
            )

        edges = []

        for source, target, data in graph.edges(data=True):

            edges.append(
                {
                    "source": source,
                    "target": target,
                    **data,
                }
            )

        return {
            "nodes": nodes,
            "edges": edges,
        }