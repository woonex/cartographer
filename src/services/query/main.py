from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from agent import ask
from settings_query import Settings, get_settings
from tools.search_manual import qdrant

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


class QueryRequest(BaseModel):
    question: str
    vehicle: str
    history: list[dict] = []


class QueryResponse(BaseModel):
    answer: str


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    answer = ask(req.question, req.vehicle, req.history)
    return QueryResponse(answer=answer)
