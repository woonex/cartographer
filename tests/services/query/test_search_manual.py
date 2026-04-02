"""
Integration test: embed 3 sentences into Qdrant, then query via search_manual()
and verify the most relevant result comes back.

Requires a running Qdrant instance (docker compose up qdrant).
"""

import os
import sys
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

QDRANT_URL = "http://localhost:6333"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = f"test_manuals_{uuid.uuid4().hex[:8]}"

SENTENCES = [
    "the color of the car is red",
    "the length of the car is 78 inches",
    "the engine size is 2.5 liters",
]

# Add the query service to the path so imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "services" / "query"))

os.environ.setdefault("QUERY_VECTOR_STORE_URL", QDRANT_URL)


@pytest.fixture(scope="module")
def model():
    return SentenceTransformer(EMBEDDING_MODEL)


@pytest.fixture(scope="module")
def qdrant():
    client = QdrantClient(url=QDRANT_URL)
    yield client
    client.delete_collection(COLLECTION_NAME)


@pytest.fixture(scope="module", autouse=True)
def seed_collection(qdrant, model):
    """Create a temporary collection and insert the 3 test sentences."""
    vector_size = model.get_sentence_embedding_dimension()
    qdrant.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
    )

    embeddings = model.encode(SENTENCES).tolist()
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=emb,
            payload={"vehicle": "test-car", "text": text},
        )
        for text, emb in zip(SENTENCES, embeddings)
    ]
    qdrant.upsert(collection_name=COLLECTION_NAME, points=points)


def test_search_manual_matches_color():
    """search_manual('what color?') should return text containing the color sentence."""
    # Patch settings so search_manual uses our test collection
    with patch("settings.get_settings") as mock_settings:
        mock_settings.return_value.vector_store_url = QDRANT_URL
        mock_settings.return_value.collection_name = COLLECTION_NAME
        mock_settings.return_value.top_k = 1
        mock_settings.return_value.min_similarity = 0.5

        # Import after patching so module-level code picks up our settings
        import importlib
        import tools.search_manual as sm
        importlib.reload(sm)

        result = sm.search_manual("what color is the car?", "test-car")

    assert "the color of the car is red" in result
