from __future__ import annotations

import json
import traceback
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from site_copilot.api.deps import AppState, build_app_state
from site_copilot.notifications import maybe_notify_visitor

_STATIC_DIR = Path(__file__).resolve().parent.parent / "ui" / "static"
_SAMPLES_DIR = Path("data/samples")


class RFIPayload(BaseModel):
    rfi_id: str
    submitted: str | None = None
    discipline: str | None = None
    trade: str | None = None
    references: list[str] = Field(default_factory=list)
    question: str


class FieldNotesPayload(BaseModel):
    date: str
    author: str
    raw_notes: str


class AgentResponse(BaseModel):
    run_id: str
    parsed: dict[str, Any] | None
    final_text: str
    steps: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    tool_invocations: list[dict[str, Any]]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.app_state = build_app_state()
    yield


app = FastAPI(
    title="Site Copilot",
    version="0.1.0",
    description=(
        "Agentic RFI and Daily Report copilot for construction jobsites. "
        "Built as a portfolio demo aligned to Suffolk's Site AI Engineer role."
    ),
    lifespan=lifespan,
)


@app.middleware("http")
async def visitor_notify(request: Request, call_next):
    response = await call_next(request)
    # Only notify on the landing-page HTML hit — not API calls, static assets,
    # or health checks. Schedules a background task; never blocks the response.
    if request.method == "GET" and request.url.path == "/":
        try:
            await maybe_notify_visitor(request, request.url.path)
        except Exception as e:
            print(f"[site-copilot] visitor notify error: {e}", flush=True)
    # Defeat browser caching of UI assets so users always see the latest
    # JS/CSS without needing a hard refresh.
    if request.url.path.startswith("/static/") or request.url.path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    return response


def _state(request: Request) -> AppState:
    return request.app.state.app_state


@app.get("/healthz")
def healthz(request: Request) -> dict[str, Any]:
    s = _state(request)
    return {
        "status": "ok",
        "model": s.settings.model,
        "retriever": s.settings.retriever,
        "corpus_chunks": s.retriever.size(),
        "use_mock_llm": s.rfi_agent.llm.use_mock,
    }


@app.get("/api", include_in_schema=False)
def api_info(request: Request) -> dict[str, Any]:
    """Machine-readable service description (was at / before the HTML UI shipped)."""
    s = _state(request)
    return {
        "service": "Site Copilot",
        "version": "0.1.0",
        "description": "Agentic RFI + Daily Report copilot for construction jobsites.",
        "endpoints": {
            "GET /": "HTML UI.",
            "POST /agents/rfi/triage": "Triage an incoming RFI.",
            "POST /agents/daily-report/draft": "Draft a structured DCR from raw field notes.",
            "GET /healthz": "Liveness + model/retriever status.",
            "GET /traces/recent": "Recent tracer events (latency, tokens, cost).",
            "GET /api/samples/rfi": "Sample RFI inbox.",
            "GET /api/samples/dcr": "Sample superintendent field notes.",
            "GET /docs": "OpenAPI / Swagger UI.",
        },
        "mode": "MOCK (canned responses)" if s.rfi_agent.llm.use_mock else f"LIVE ({s.settings.model})",
    }


@app.get("/api/samples/rfi", include_in_schema=False)
def sample_rfis() -> list[dict[str, Any]]:
    p = _SAMPLES_DIR / "rfi_inbox.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


@app.get("/api/samples/dcr", include_in_schema=False)
def sample_dcrs() -> list[dict[str, Any]]:
    p = _SAMPLES_DIR / "field_notes.json"
    if not p.exists():
        return []
    return json.loads(p.read_text(encoding="utf-8"))


def _run_agent_or_error(fn, payload: dict[str, Any], agent_name: str) -> AgentResponse:
    try:
        result = fn(payload)
    except Exception as e:
        tb = traceback.format_exc()
        print(f"[site-copilot] {agent_name} failed: {type(e).__name__}: {e}\n{tb}", flush=True)
        raise HTTPException(
            status_code=500,
            detail={"error": type(e).__name__, "message": str(e), "agent": agent_name},
        )
    return AgentResponse(
        run_id=result.run_id,
        parsed=result.parsed,
        final_text=result.final_text,
        steps=result.steps,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        cost_usd=round(result.cost_usd, 6),
        tool_invocations=result.tool_invocations,
    )


@app.post("/agents/rfi/triage", response_model=AgentResponse)
def triage_rfi(payload: RFIPayload, request: Request) -> AgentResponse:
    s = _state(request)
    return _run_agent_or_error(s.rfi_agent.run_rfi, payload.model_dump(), "rfi_triage")


@app.post("/agents/daily-report/draft", response_model=AgentResponse)
def draft_dcr(payload: FieldNotesPayload, request: Request) -> AgentResponse:
    s = _state(request)
    return _run_agent_or_error(s.dcr_agent.run_field_notes, payload.model_dump(), "daily_report")


@app.get("/traces/recent")
def traces_recent(request: Request, limit: int = 100) -> dict[str, Any]:
    s = _state(request)
    p = s.tracer._path
    if not p.exists():
        return {"events": [], "count": 0}
    lines = p.read_text(encoding="utf-8").splitlines()[-limit:]
    events = [json.loads(line) for line in lines if line.strip()]
    return {"events": events, "count": len(events)}


# --- HTML UI ---
# Mounted last so explicit routes above always win. /static serves CSS/JS;
# / returns the single-page HTML.

if _STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=_STATIC_DIR), name="static")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        return FileResponse(_STATIC_DIR / "index.html")
