from settings import get_settings

from qdrant_client import QdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue
from sentence_transformers import SentenceTransformer

settings = get_settings()
model = SentenceTransformer(settings.embedding_model)
qdrant = QdrantClient(url=settings.vector_store_url)

def search_manual(question: str, vehicle: str) -> str:
    """gets relevant text from owner's manual for the selected vehicle"""

    collection_name = settings.collection_name
    top_k = settings.top_k
    vector = model.encode(question)

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

    return "\n\n".join(point.payload["text"] for point in response.points)
