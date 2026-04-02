from settings import get_settings

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

settings = get_settings()
qdrant = QdrantClient(url=settings.vector_store_url)

def search_manual(question: str, vehicle: str) -> str:
    """gets relevant text from owner's manual for the selected vehicle"""

    collection_name = settings.collection_name
    top_k = settings.top_k
    results = qdrant.query(
        collection_name=collection_name,
        query_text=question,
        query_filter=Filter(
            must=[
                FieldCondition(
                    key="vehicle",
                    match=MatchValue(value=vehicle)
                )
            ]
        ),
        limit=top_k
    )

    filtered_results = [result.min_similarity for result in results]

    return "\n\n".join(result.metadata["text"] for result in filtered_results)
