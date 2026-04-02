import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

# Add the ingestion service to the path so imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src" / "services" / "ingestion"))

# Set required env vars before importing the app
os.environ.setdefault("INGESTION_VECTOR_STORE_URL", "http://localhost:6333")

# Mock heavy dependencies before importing the app
with patch("sentence_transformers.SentenceTransformer") as mock_st, \
     patch("qdrant_client.QdrantClient") as mock_qc:
    mock_model = MagicMock()
    mock_model.get_sentence_embedding_dimension.return_value = 384
    mock_model.encode.return_value.tolist.return_value = [[0.0] * 384]
    mock_st.return_value = mock_model
    from main import app

client = TestClient(app)


def test_ingest_valid_pdf():
    with patch("main.ingest_vehicle") as mock_ingest:
        pdf_bytes = b"%PDF-1.4 minimal"
        response = client.post(
            "/ingest",
            data={"vehicle_name": "test-car", "document_name": "owners-manual"},
            files={"file": ("manual.pdf", pdf_bytes, "application/pdf")},
        )
        assert response.status_code == 200
        assert response.json()["status"] == "ok"
        mock_ingest.assert_called_once()


def test_ingest_bad_file():
    response = client.post(
        "/ingest",
        data={"vehicle_name": "test-car", "document_name": "owners-manual"},
        files={"file": ("garbage.txt", b"not a pdf", "text/plain")},
    )
    assert response.status_code == 422


def test_ready_qdrant_down():
    with patch("main.qdrant") as mock_qdrant:
        mock_qdrant.get_collections.side_effect = Exception("connection refused")
        response = client.get("/ready")
        assert response.status_code == 503
        assert response.json()["status"] == "not ready"
