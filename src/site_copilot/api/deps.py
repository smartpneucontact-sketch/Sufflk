from __future__ import annotations

from dataclasses import dataclass

from site_copilot.agents import DailyReportAgent, RFIAgent
from site_copilot.config import Settings, get_settings
from site_copilot.llm import LLMClient
from site_copilot.observability import Tracer
from site_copilot.rag.ingest import build_retriever
from site_copilot.rag.retriever import Retriever
from site_copilot.tools import build_dcr_tools, build_rfi_tools


@dataclass
class AppState:
    settings: Settings
    retriever: Retriever
    tracer: Tracer
    rfi_agent: RFIAgent
    dcr_agent: DailyReportAgent


def build_app_state() -> AppState:
    settings = get_settings()
    retriever = build_retriever()

    llm = LLMClient(
        api_key=settings.anthropic_api_key, model=settings.model, use_mock=settings.use_mock_llm
    )
    tracer = Tracer(settings.traces_dir)
    rfi_agent = RFIAgent(
        llm=llm, tools=build_rfi_tools(retriever), tracer=tracer, max_steps=settings.max_agent_steps
    )
    dcr_agent = DailyReportAgent(
        llm=llm, tools=build_dcr_tools(retriever), tracer=tracer, max_steps=settings.max_agent_steps
    )
    return AppState(
        settings=settings,
        retriever=retriever,
        tracer=tracer,
        rfi_agent=rfi_agent,
        dcr_agent=dcr_agent,
    )
