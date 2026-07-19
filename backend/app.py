"""
AcadEase AI - FastAPI backend entrypoint.

Run locally:
    cd backend
    pip install -r requirements.txt
    cp .env.example .env   # then fill in GROK_API_KEY
    uvicorn app:app --reload --port 8000
"""
import logging

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from config import settings
from data_loader import store
from graph import acadease_graph

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("acadease.app")

app = FastAPI(
    title=settings.app_name,
    description=f"AI-powered multi-agent academic assistant for {settings.university_name}",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatTurnIn(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = "default"
    history: list[ChatTurnIn] = Field(default_factory=list)
    department: str | None = None
    semester: int | None = None


class ChatResponse(BaseModel):
    reply: str
    agent_trail: list[str]
    intent: str | None = None
    resolved_subject: str | None = None
    search_method: str | None = None
    resources: list[dict] = Field(default_factory=list)
    study_plan: dict | None = None
    session_id: str = "default"


@app.get("/")
def root():
    return {"app": settings.app_name, "university": settings.university_name, "status": "ok"}


@app.get("/health")
def health():
    return {
        "status": "ok",
        "subjects": len(store.subjects),
        "notes": len(store.notes),
        "pyqs": len(store.pyqs),
        "resource_topics": len(store.resources),
        "grok_configured": bool(settings.grok_api_key),
    }


@app.get("/api/subjects")
def get_subjects():
    return {"subjects": sorted(store.canonical_pool)}


@app.get("/api/courses")
def get_courses():
    return {"courses": store.courses}


@app.post("/api/reload-catalog")
def reload_catalog():
    store.reload()
    return {"status": "reloaded", "notes": len(store.notes), "pyqs": len(store.pyqs)}


@app.post("/api/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    if not req.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    initial_state = {
        "user_query": req.message,
        "history": [{"role": h.role, "content": h.content} for h in req.history],
        "filter_department": req.department,
        "filter_semester": req.semester,
        "agent_trail": [],
        "resources": [],
    }

    try:
        result = await acadease_graph.ainvoke(initial_state)
    except Exception as e:  # noqa: BLE001
        logger.exception("graph execution failed")
        raise HTTPException(status_code=500, detail=str(e)) from e

    return ChatResponse(
        reply=result.get("reply", ""),
        agent_trail=result.get("agent_trail", []),
        intent=result.get("intent"),
        resolved_subject=result.get("resolved_subject"),
        search_method=result.get("search_method"),
        resources=result.get("resources", []),
        study_plan=result.get("study_plan"),
        session_id=req.session_id,
    )
