"""
Ingestion pipeline and supplementary functions
"""

import logging
import uuid
from collections.abc import Callable

import fitz
from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FieldCondition, Filter, FilterSelector, MatchValue, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from settings_ingestion import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
model = SentenceTransformer(settings.embedding_model)
qdrant = QdrantClient(url=settings.vector_store_url)

BATCH_SIZE = 32


def ingest_pdf(pdf_path: str) -> str:
    """Gets raw text from PDF"""
    doc = fitz.open(pdf_path)
    return "\n".join(page.get_text() for page in doc)


def chunk_text(text: str) -> list[str]:
    """Chunks text into overlapping chunks"""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ".", " "]
    )
    return splitter.split_text(text)


def ingest_vehicle_chunks(
    vehicle_name: str,
    document_name: str,
    chunks: list[str],
    on_batch: Callable[[int], None] | None = None,
):
    """Embeds and upserts pre-chunked text into the vector store.

    on_batch is called after each batch with the cumulative completed chunk count.
    """
    collection_name = settings.collection_name
    vector_size = model.get_sentence_embedding_dimension()

    if not qdrant.collection_exists(collection_name):
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    # Clear existing chunks for this vehicle/document before inserting
    qdrant.delete(
        collection_name=collection_name,
        points_selector=FilterSelector(
            filter=Filter(
                must=[
                    FieldCondition(key="vehicle", match=MatchValue(value=vehicle_name)),
                    FieldCondition(key="document", match=MatchValue(value=document_name)),
                ]
            )
        ),
    )

    completed = 0
    for i in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[i:i + BATCH_SIZE]
        embeddings = model.encode(batch).tolist()
        points = [
            PointStruct(
                id=str(uuid.uuid4()),
                vector=embedding,
                payload={"vehicle": vehicle_name, "document": document_name, "text": chunk},
            )
            for chunk, embedding in zip(batch, embeddings)
        ]
        qdrant.upsert(collection_name=collection_name, points=points)
        completed += len(batch)
        if on_batch:
            on_batch(completed)

    logger.info(f"Stored {len(chunks)} chunks for {vehicle_name}/{document_name}")


def ingest_vehicle(vehicle_name: str, document_name: str, pdf_path: str):
    """Ingests a vehicle pdf end-to-end (no progress tracking)."""
    logger.info(f"Ingesting {document_name} for {vehicle_name}")
    text = ingest_pdf(pdf_path)
    chunks = chunk_text(text)
    ingest_vehicle_chunks(vehicle_name, document_name, chunks)
