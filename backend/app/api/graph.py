"""Return account relationships in the format used by the investigation screen.

How it works: load the account's transactions, build a local graph, and flatten
the result for Cytoscape. Result: the API uses the shared graph builders without
changing the frontend contract. Example: ``GET /api/graph/A001``.
"""

from typing import Any, Iterable

import networkx as nx
from fastapi import APIRouter
from sqlalchemy import select

from app.db.database import SessionLocal
from app.db.models import Transaction
from app.graph.builders.updater import GraphUpdater

router = APIRouter()


def build_relationship_graph(transactions: Iterable[Any]) -> nx.MultiDiGraph:
    """Build an isolated graph so one API request cannot change another."""
    graph = nx.MultiDiGraph()
    GraphUpdater(graph).add_transactions(transactions)
    return graph


def serialize_for_cytoscape(graph: nx.MultiDiGraph) -> dict[str, list[dict[str, Any]]]:
    """Flatten graph data into the structure already read by the frontend."""
    visible_types = {"Account", "Device", "IP", "Wallet"}
    nodes = [
        {
            "id": str(node_id),
            "type": str(data.get("node_type", "UNKNOWN")).upper(),
            "label": data.get("label", str(node_id)),
        }
        for node_id, data in graph.nodes(data=True)
        if data.get("node_type") in visible_types
    ]
    visible_ids = {node["id"] for node in nodes}

    edges = []
    for source, target, _key, data in graph.edges(keys=True, data=True):
        if str(source) not in visible_ids or str(target) not in visible_ids:
            continue
        relation = data.get("relation", "UNKNOWN")
        edges.append(
            {
                "source": str(source),
                "target": str(target),
                "relationship": "TRANSACTION" if relation == "SENDS_TO" else relation,
                **{name: value for name, value in data.items() if name != "relation"},
            }
        )

    return {"nodes": nodes, "edges": edges}


@router.get("/graph/{account}")
def get_relationship_graph(account: str):
    """Load and return direct transactions and entity links for one account."""
    with SessionLocal() as session:
        query = select(Transaction).where(
            (Transaction.sender_account == account)
            | (Transaction.receiver_account == account)
            | (Transaction.crypto_wallet == account)
        )
        transactions = session.execute(query).scalars().all()

    data = serialize_for_cytoscape(build_relationship_graph(transactions))

    return {
        "status": "success",
        "entity": account,
        "node_count": len(data["nodes"]),
        "edge_count": len(data["edges"]),
        "graph": data,
    }
