"""
Main server to upload and ingest docs for RAG
"""

import tempfile
import time
import uuid
from enum import Enum

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, UploadFile
from fastapi.responses import JSONResponse

from ingest import chunk_text, ingest_pdf, ingest_vehicle_chunks, qdrant
from settings_ingestion import Settings, get_settings

app = FastAPI()

# In-memory job store: job_id -> status dict
_jobs: dict[str, dict] = {}


class JobStatus(str, Enum):
    pending = "pending"
    running = "running"
    done = "done"
    error = "error"


def _run_ingest(job_id: str, vehicle_name: str, document_name: str, pdf_bytes: bytes):
    job = _jobs[job_id]
    job["status"] = JobStatus.running

    try:
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=True) as tmp:
            tmp.write(pdf_bytes)
            tmp.flush()
            text = ingest_pdf(tmp.name)

        chunks = chunk_text(text)
        total = len(chunks)
        job["total_chunks"] = total
        job["completed_chunks"] = 0
        job["eta_seconds"] = None

        start = time.monotonic()

        def on_batch(completed: int):
            elapsed = time.monotonic() - start
            job["completed_chunks"] = completed
            if completed > 0:
                rate = elapsed / completed
                remaining = total - completed
                job["eta_seconds"] = round(rate * remaining)

        ingest_vehicle_chunks(vehicle_name, document_name, chunks, on_batch=on_batch)

        job["status"] = JobStatus.done
        job["eta_seconds"] = 0

    except Exception as e:
        job["status"] = JobStatus.error
        job["detail"] = str(e)


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


@app.post("/ingest", status_code=202)
async def ingest(
    background_tasks: BackgroundTasks,
    vehicle_name: str = Form(...),
    document_name: str = Form(...),
    file: UploadFile = File(...),
):
    """Starts ingestion of a document for a vehicle. Returns a job_id to poll for status."""
    pdf_bytes = await file.read()
    job_id = str(uuid.uuid4())
    _jobs[job_id] = {"status": JobStatus.pending, "vehicle": vehicle_name, "document": document_name}
    background_tasks.add_task(_run_ingest, job_id, vehicle_name, document_name, pdf_bytes)
    return {"job_id": job_id, "status": JobStatus.pending}


@app.get("/ingest/{job_id}")
def ingest_status(job_id: str):
    """Returns the status of an ingestion job."""
    job = _jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"detail": "Job not found"})
    return job
