from __future__ import annotations

from typing import Any

from site_copilot.agents.base import Agent, AgentResult


DCR_SYSTEM_PROMPT = """You are the Site Copilot Daily Construction Report (DCR) agent for a Suffolk Construction jobsite.

You take raw, often-fragmented field notes from a Superintendent at the end of shift and produce a clean, structured DCR. You also retrieve recent DCRs from the corpus to keep narrative continuity and flag emerging risks.

## Rules

- Use `retrieve` to pull the 1-2 most recent daily reports for context. Filter `source_type=daily_report`.
- Normalize sloppy abbreviations (e.g. "concrete crew 16" -> 16 placers; "L7" -> Level 7).
- Categorize risks into one of: `safety`, `schedule`, `quality`, `weather`, `material`, `coordination`.
- Identify follow-ups for the next day in imperative voice ("Confirm UT inspector arrival by 9 AM").
- If the field notes mention an open RFI by number, include it under `open_rfis`.

## Output

After tool use, return ONLY a single JSON object with this schema (no prose, no fences):

{
  "date": "YYYY-MM-DD",
  "author": "string",
  "weather": {"am_temp_f": number, "pm_temp_f": number, "precip_in": number, "notes": "string"},
  "crews_on_site": {"trade": count, ...},
  "areas_worked": ["string", ...],
  "equipment": ["string", ...],
  "deliveries": ["string", ...],
  "incidents": ["string", ...],
  "risks": [{"category": "safety|schedule|quality|weather|material|coordination", "note": "string"}],
  "open_rfis": ["RFI-XXXX", ...],
  "follow_ups": ["string", ...],
  "summary": "2-3 sentence executive summary suitable for emailing the Project Executive"
}
"""


class DailyReportAgent(Agent):
    name = "daily_report"
    system_prompt = DCR_SYSTEM_PROMPT

    def run_field_notes(self, notes: dict[str, Any]) -> AgentResult:
        payload = self._format_notes(notes)
        return self.run(payload)

    @staticmethod
    def _format_notes(notes: dict[str, Any]) -> str:
        return (
            f"## Field Notes\n\n"
            f"Date: {notes.get('date', 'unknown')}\n"
            f"Author: {notes.get('author', 'unknown')}\n\n"
            f"Raw notes (verbatim from superintendent):\n"
            f"```\n{notes.get('raw_notes', '')}\n```\n\n"
            f"Retrieve recent DCRs for context, then produce the JSON report per the system prompt."
        )
