from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel, Field

from site_copilot.api.deps import AppState, build_app_state


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


@app.get("/")
def root(request: Request) -> dict[str, Any]:
    """Friendly landing endpoint so a browser hitting the bare URL gets something useful."""
    s = _state(request)
    return {
        "service": "Site Copilot",
        "version": "0.1.0",
        "description": "Agentic RFI + Daily Report copilot for construction jobsites.",
        "endpoints": {
            "POST /agents/rfi/triage": "Triage an incoming RFI.",
            "POST /agents/daily-report/draft": "Draft a structured DCR from raw field notes.",
            "GET /healthz": "Liveness + model/retriever status.",
            "GET /traces/recent": "Recent tracer events (latency, tokens, cost).",
            "GET /docs": "OpenAPI / Swagger UI.",
        },
        "mode": "MOCK (canned responses)" if s.rfi_agent.llm.use_mock else f"LIVE ({s.settings.model})",
    }


@app.post("/agents/rfi/triage", response_model=AgentResponse)
def triage_rfi(payload: RFIPayload, request: Request) -> AgentResponse:
    s = _state(request)
    try:
        result = s.rfi_agent.run_rfi(payload.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
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


@app.post("/agents/daily-report/draft", response_model=AgentResponse)
def draft_dcr(payload: FieldNotesPayload, request: Request) -> AgentResponse:
    s = _state(request)
    try:
        result = s.dcr_agent.run_field_notes(payload.model_dump())
    except RuntimeError as e:
        raise HTTPException(status_code=500, detail=str(e))
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


@app.get("/traces/recent")
def traces_recent(request: Request, limit: int = 100) -> dict[str, Any]:
    s = _state(request)
    p = s.tracer._path
    if not p.exists():
        return {"events": [], "count": 0}
    lines = p.read_text(encoding="utf-8").splitlines()[-limit:]
    events = [json.loads(line) for line in lines if line.strip()]
    return {"events": events, "count": len(events)}
