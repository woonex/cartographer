"""
Main server to upload and ingest docs for RAG
"""

import tempfile
from fastapi import Depends, FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from ingest import ingest_vehicle, qdrant
from settings import Settings, get_settings

app = FastAPI()


@app.get("/health")
def health():
    """If the server is alive"""
    return {"status": "ok"}


@app.get("/ready")
def ready(settings: Settings = Depends(get_settings)):
    """If the server is ready to process ingestion

    returns:
    200 if okay
    503 if service unavailable
    """
    try:
        qdrant.get_collections()
        return {"status": "ready"}
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not ready", "reason": "vector store unreachable"})


@app.post("/ingest")
def ingest(
    vehicle_name: str = Form(...),
    document_name: str = Form(...),
    file: UploadFile = File(...),
):
    """Ingests a document for a vehicle"""
    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(file.file.read())
            tmp.flush()
            ingest_vehicle(vehicle_name, document_name, tmp.name)
    except Exception as e:
        return JSONResponse(status_code=422, content={"status": "error", "detail": str(e)})

    return {"status": "ok", "vehicle": vehicle_name, "document": document_name}
