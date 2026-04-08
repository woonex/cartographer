import json
import threading
import time
from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field
from qdrant_client import QdrantClient

from settings_query import get_settings

_settings = get_settings()
_qdrant = QdrantClient(url=_settings.vector_store_url)

_ask = None
_ask_stream = None
_agent_ready = threading.Event()
_model_ready = threading.Event()


def _init_all():
    t0 = time.perf_counter()

    from tools.search_manual import is_model_ready, start_model_load
    start_model_load()

    from agent import ask, ask_stream
    global _ask, _ask_stream
    _ask = ask
    _ask_stream = ask_stream
    _agent_ready.set()

    while not is_model_ready():
        time.sleep(0.1)
    _model_ready.set()

    print(f"Query service ready ({time.perf_counter() - t0:.1f}s init)", flush=True)


@asynccontextmanager
async def lifespan(app: FastAPI):
    threading.Thread(target=_init_all, daemon=True).start()
    yield


app = FastAPI(lifespan=lifespan)


@app.get("/health")
def health():
    """If the server is alive"""
    return {"status": "ok"}


@app.get("/ready")
def ready():
    """If the server is ready to process queries

    returns:
    200 if okay
    503 if service unavailable
    """
    try:
        _qdrant.get_collections()
    except Exception:
        return JSONResponse(status_code=503, content={"status": "not ready", "reason": "vector store unreachable"})
    if not _agent_ready.is_set():
        return JSONResponse(status_code=503, content={"status": "not ready", "reason": "agent initializing"})
    if not _model_ready.is_set():
        return JSONResponse(status_code=503, content={"status": "not ready", "reason": "embedding model loading"})
    return {"status": "ready"}


class QueryRequest(BaseModel):
    question: Annotated[str, Field(max_length=500)]
    vehicle: str
    history: list[dict] = []


class QueryResponse(BaseModel):
    answer: str


@app.post("/query", response_model=QueryResponse)
async def query(req: QueryRequest) -> QueryResponse:
    answer = _ask(req.question, req.vehicle, req.history)
    return QueryResponse(answer=answer)


@app.post("/query/stream")
async def query_stream(req: QueryRequest):
    """Stream agent reasoning, tool calls, and final answer as server-sent events.

    Event types:
    - tool_call: {"type": "tool_call", "name": str, "args": dict}
    - tool_result: {"type": "tool_result", "name": str, "content": str}
    - answer_token: {"type": "answer_token", "content": str}
    - done: {"type": "done"}
    - error: {"type": "error", "content": str}
    """
    async def generate():
        try:
            async for event in _ask_stream(req.question, req.vehicle, req.history):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
