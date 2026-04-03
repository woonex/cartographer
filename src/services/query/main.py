import json

from fastapi import Depends, FastAPI
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel

from agent import ask, ask_stream
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
            async for event in ask_stream(req.question, req.vehicle):
                yield f"data: {json.dumps(event)}\n\n"
        except Exception as e:
            yield f"data: {json.dumps({'type': 'error', 'content': str(e)})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
