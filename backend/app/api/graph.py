from fastapi import APIRouter

from app.graph.builder import RelationshipGraphBuilder

router = APIRouter()


@router.get("/graph/{account}")
def get_relationship_graph(account: str):

    builder = RelationshipGraphBuilder()

    graph = builder.build_for_account(account)

    data = builder.serialize(graph)

    return {
        "status": "success",
        "entity": account,
        "node_count": len(data["nodes"]),
        "edge_count": len(data["edges"]),
        "graph": data,
    }