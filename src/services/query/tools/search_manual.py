from langchain.tools import tool
from qdrant_client import QdrantClient
from qdrant_client.models import FieldCondition, Filter, MatchValue
from sentence_transformers import SentenceTransformer

from settings_query import get_settings

settings = get_settings()
model = SentenceTransformer(settings.embedding_model)
qdrant = QdrantClient(url=settings.vector_store_url)


@tool
def search_manual(search_info: str = "", vehicle: str = "") -> str:
    """Gets relevant text from owner's manual for a vehicle

    Args:
        search_info: the text to search for
        vehicle: the vehicle to search collections for

    Returns:
        str continaing top matching results from owner's manual
    """

    if search_info is None or search_info == "" or vehicle is None or vehicle == "":
        return "Malformed tool call, please pass both \"search_info\" and \"vehicle\" to this function"

    collection_name = settings.collection_name
    top_k = settings.top_k
    vector = model.encode(search_info)

    response = qdrant.query_points(
        collection_name=collection_name,
        query=vector.tolist(),
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="vehicle",
                    match=MatchValue(value=vehicle)
                )
            ]
        ),
        limit=top_k,
        score_threshold=settings.min_similarity,
    )

    if len(response.points) == 0:
        return f"No owner's manual data is available for {vehicle}. Do not retry this search."

    return "\n\n".join(point.payload["text"] for point in response.points)
