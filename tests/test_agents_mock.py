import os
from pathlib import Path

from site_copilot.agents import RFIAgent
from site_copilot.llm import LLMClient
from site_copilot.observability import Tracer
from site_copilot.rag.ingest import load_chunks
from site_copilot.rag.retriever import Retriever
from site_copilot.tools import build_rfi_tools


def test_rfi_agent_mock_runs_end_to_end(tmp_path) -> None:
    os.environ["SITE_COPILOT_USE_MOCK_LLM"] = "1"

    chunks = load_chunks(Path("data/corpus"))
    retriever = Retriever(mode="bm25")
    retriever.index(chunks)
    tracer = Tracer(tmp_path / "traces")
    llm = LLMClient(api_key=None, model="claude-sonnet-4-6", use_mock=True)
    agent = RFIAgent(llm=llm, tools=build_rfi_tools(retriever), tracer=tracer)

    result = agent.run_rfi(
        {
            "rfi_id": "RFI-TEST-001",
            "submitted": "2026-05-22",
            "discipline": "Concrete",
            "trade": "Concrete Sub",
            "references": ["Spec 03 30 00"],
            "question": "Confirm minimum cover at interior columns at the L11 transition.",
        }
    )
    assert result.parsed is not None
    assert "draft_response" in result.parsed
    assert result.steps >= 2  # at least one retrieve step + final synthesis
    assert any(inv["name"] == "retrieve" for inv in result.tool_invocations)
