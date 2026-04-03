from fastapi import Depends, FastAPI, Request
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
import httpx

from settings_frontend import Settings, get_settings

settings = get_settings()
app = FastAPI()
templates = Jinja2Templates(directory="templates")

class QueryRequest(BaseModel):
    question: str
    vehicle: str

class QueryResponse(BaseModel):
    answer: str

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
    return {"status": "ready"}

@app.get("/")
def main(request: Request):
    return templates.TemplateResponse(request, "main.html")

@app.get("/available-vehicles")
def get_available_vehicles() -> list[str]:
    """Gets available vehicles for the user"""
    response = httpx.get(
        f"{settings.vehicle_library_url}/vehicles",
    )
    response.raise_for_status()
    return response.json()

@app.post("/query-model")
def query_model(req: QueryRequest) -> QueryResponse:
    """Query the frontend serves depending on the vehicles available to the user and the question the user asked"""
    response = httpx.post(
        f"{settings.query_url}/vehicle/specifications",
        json={
            "vehicle": req.vehicle,
            "question": req.question
        },
    )
    response.raise_for_status()
    return response.json()
