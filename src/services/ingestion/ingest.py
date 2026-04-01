"""
Ingestion pipeline and supplementary functions
"""

import fitz
import logging
import uuid

from langchain_text_splitters import RecursiveCharacterTextSplitter
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, FilterSelector, FieldCondition, Filter, MatchValue, PointStruct, VectorParams
from sentence_transformers import SentenceTransformer

from settings import get_settings

logger = logging.getLogger(__name__)

settings = get_settings()
model = SentenceTransformer(settings.embedding_model)
qdrant = QdrantClient(url=settings.vector_store_url)

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

def ingest_vehicle(vehicle_name: str, document_name: str, pdf_path: str):
    """Ingests a vehicle pdf and adds encoded vector for later RAG use"""
    logger.info(f"Ingesting {document_name} for {vehicle_name}")
    text = ingest_pdf(pdf_path)
    chunks = chunk_text(text)
    embeddings = model.encode(chunks).tolist()

    collection_name = "manuals"
    vector_size = model.get_sentence_embedding_dimension()

    # first time setup
    if not qdrant.collection_exists(collection_name):
        qdrant.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE),
        )

    # clear existing chunks for this vehicle and document before inserting if re-uploading to prevent minor differences in files giving more embeddings than necessary
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

    # embed in structure for qdrant
    points = [
        PointStruct(
            id=str(uuid.uuid4()),
            vector=embedding,
            payload={"vehicle": vehicle_name, "document": document_name, "text": chunk},
        )
        for chunk, embedding in zip(chunks, embeddings)
    ]

    qdrant.upsert(collection_name=collection_name, points=points)
    logger.info(f"Stored {len(points)} chunks for {vehicle_name}/{document_name}")
