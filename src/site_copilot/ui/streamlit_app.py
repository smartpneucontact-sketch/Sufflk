"""Streamlit UI for Site Copilot.

Two tabs: RFI triage and Daily Report drafting. The point of this UI is to
demo what a hiring panel would see if it were running on a tablet on the
jobsite — it is intentionally minimal."""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from site_copilot.api.deps import build_app_state


@st.cache_resource
def get_state():
    return build_app_state()


def main() -> None:
    st.set_page_config(page_title="Site Copilot", page_icon=None, layout="wide")
    st.title("Site Copilot")
    st.caption(
        "Agentic RFI + Daily Report assistant. Built for the Suffolk Site AI Engineer role. "
        "Powered by Claude with tool use, RAG over project specs/RFIs/DCRs, and JSONL traces."
    )

    state = get_state()
    with st.sidebar:
        st.subheader("System")
        st.write({
            "model": state.settings.model,
            "retriever": state.settings.retriever,
            "corpus_chunks": state.retriever.size(),
            "mock_llm": state.settings.use_mock_llm,
        })
        st.divider()
        st.caption(
            "Project: synthetic Allerton Tower (32-story mixed-use, Boston). "
            "Corpus: 5 specs, 8 prior RFIs, 3 DCRs."
        )

    tab_rfi, tab_dcr = st.tabs(["RFI Triage", "Daily Report"])
    _render_rfi_tab(tab_rfi, state)
    _render_dcr_tab(tab_dcr, state)


def _render_rfi_tab(tab, state) -> None:
    with tab:
        st.subheader("RFI Triage Agent")
        st.write(
            "Paste or pick an incoming RFI. The agent retrieves relevant spec "
            "sections and prior RFIs, then drafts a citation-backed response "
            "with urgency and impact estimates."
        )

        inbox_path = Path("data/samples/rfi_inbox.json")
        inbox = json.loads(inbox_path.read_text()) if inbox_path.exists() else []
        labels = [f"{r['rfi_id']} — {r['discipline']}" for r in inbox]
        idx = st.selectbox("Sample RFIs", list(range(len(labels))), format_func=lambda i: labels[i] if labels else "")
        if not inbox:
            st.warning("No sample RFIs found at data/samples/rfi_inbox.json")
            return

        rfi = inbox[idx]
        rfi_id = st.text_input("RFI ID", rfi["rfi_id"])
        question = st.text_area("Question", rfi["question"], height=140)
        discipline = st.text_input("Discipline", rfi.get("discipline", ""))
        trade = st.text_input("Trade", rfi.get("trade", ""))
        refs = st.text_input("References (comma-separated)", ", ".join(rfi.get("references", [])))

        if st.button("Triage RFI", type="primary"):
            payload = {
                "rfi_id": rfi_id,
                "submitted": rfi.get("submitted"),
                "discipline": discipline,
                "trade": trade,
                "references": [r.strip() for r in refs.split(",") if r.strip()],
                "question": question,
            }
            with st.spinner("Retrieving context and drafting response..."):
                result = state.rfi_agent.run_rfi(payload)
            _render_agent_result(result, prefer="rfi")


def _render_dcr_tab(tab, state) -> None:
    with tab:
        st.subheader("Daily Construction Report Agent")
        st.write(
            "Paste end-of-shift field notes (anything goes — fragments, abbreviations, "
            "stream-of-consciousness). Agent produces a structured DCR with risks and follow-ups."
        )

        notes_path = Path("data/samples/field_notes.json")
        notes_inbox = json.loads(notes_path.read_text()) if notes_path.exists() else []
        labels = [f"{n['date']} — {n['author']}" for n in notes_inbox]
        idx = st.selectbox(
            "Sample field notes",
            list(range(len(labels))),
            format_func=lambda i: labels[i] if labels else "",
            key="dcr_sample",
        )
        if not notes_inbox:
            st.warning("No sample field notes found at data/samples/field_notes.json")
            return

        sample = notes_inbox[idx]
        date = st.text_input("Date", sample["date"], key="dcr_date")
        author = st.text_input("Author", sample["author"], key="dcr_author")
        raw_notes = st.text_area("Raw field notes", sample["raw_notes"], height=220)

        if st.button("Draft DCR", type="primary", key="dcr_btn"):
            payload = {"date": date, "author": author, "raw_notes": raw_notes}
            with st.spinner("Drafting structured DCR..."):
                result = state.dcr_agent.run_field_notes(payload)
            _render_agent_result(result, prefer="dcr")


def _render_agent_result(result, *, prefer: str) -> None:
    col1, col2 = st.columns([3, 2])
    with col1:
        st.markdown("### Agent output")
        if result.parsed is not None:
            st.json(result.parsed)
        else:
            st.code(result.final_text or "(no text)", language="json")

    with col2:
        st.markdown("### Run telemetry")
        st.write(
            {
                "run_id": result.run_id,
                "steps": result.steps,
                "input_tokens": result.input_tokens,
                "output_tokens": result.output_tokens,
                "cost_usd": round(result.cost_usd, 5),
                "tool_calls": len(result.tool_invocations),
            }
        )

        if result.tool_invocations:
            st.markdown("**Tool invocations**")
            for inv in result.tool_invocations:
                with st.expander(f"step {inv['step']} -> {inv['name']}"):
                    st.write({"input": inv["input"]})
                    res = inv["result"]
                    if isinstance(res, dict) and "results" in res:
                        st.write(f"{res.get('count', 0)} results")
                        for r in res["results"][:6]:
                            st.markdown(
                                f"- `{r['source_type']}:{r['source_id']}` "
                                f"({r.get('section') or 'no section'}) — score {r['score']}"
                            )
                    else:
                        st.write(res)


if __name__ == "__main__":
    main()
