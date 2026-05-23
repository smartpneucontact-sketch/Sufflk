from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from site_copilot.rag.retriever import Retriever


@dataclass
class ToolSpec:
    name: str
    description: str
    input_schema: dict[str, Any]
    fn: Callable[..., Any]

    def to_anthropic(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "input_schema": self.input_schema,
        }


class ToolRegistry:
    """Registers callable tools and produces Anthropic tool definitions.

    Tools accept kwargs from the model and return JSON-serializable results."""

    def __init__(self, tools: list[ToolSpec] | None = None):
        self._tools: dict[str, ToolSpec] = {}
        for t in tools or []:
            self.register(t)

    def register(self, spec: ToolSpec) -> None:
        self._tools[spec.name] = spec

    def to_anthropic(self) -> list[dict[str, Any]]:
        return [t.to_anthropic() for t in self._tools.values()]

    def call(self, name: str, arguments: dict[str, Any]) -> Any:
        if name not in self._tools:
            return {"error": f"unknown tool: {name}"}
        try:
            return self._tools[name].fn(**arguments)
        except TypeError as e:
            return {"error": f"bad arguments for {name}: {e}"}
        except Exception as e:  # pragma: no cover
            return {"error": f"{name} raised: {type(e).__name__}: {e}"}


def _make_retrieve_tool(retriever: Retriever) -> ToolSpec:
    def retrieve(query: str, k: int = 6, source_type: str | None = None) -> dict[str, Any]:
        filters = {"source_type": source_type} if source_type else None
        results = retriever.search(query, k=k, filters=filters)
        return {
            "results": [
                {
                    "chunk_id": r.chunk.chunk_id,
                    "source_type": r.chunk.source_type,
                    "source_id": r.chunk.source_id,
                    "section": r.chunk.section,
                    "score": round(r.score, 3),
                    "text": r.chunk.text,
                }
                for r in results
            ],
            "count": len(results),
        }

    return ToolSpec(
        name="retrieve",
        description=(
            "Search the project corpus (specs, prior RFIs, daily reports) for context "
            "relevant to a question. Use this BEFORE drafting any answer. Returns chunks "
            "with their source so you can cite them precisely."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Natural-language search query. Include spec numbers, drawing IDs, or material terms.",
                },
                "k": {"type": "integer", "default": 6, "description": "Max results to return (1-12)."},
                "source_type": {
                    "type": "string",
                    "enum": ["spec", "prior_rfi", "daily_report"],
                    "description": "Optional filter to one source type.",
                },
            },
            "required": ["query"],
        },
        fn=retrieve,
    )


def _classify_urgency() -> ToolSpec:
    def classify_urgency(
        question: str,
        is_safety: bool = False,
        is_critical_path: bool = False,
        days_until_affected_activity: int | None = None,
    ) -> dict[str, Any]:
        if is_safety:
            level = "high"
        elif is_critical_path and (days_until_affected_activity or 99) <= 3:
            level = "high"
        elif (days_until_affected_activity or 99) <= 7:
            level = "medium"
        else:
            level = "low"
        return {
            "urgency": level,
            "rationale": (
                f"safety={is_safety}, critical_path={is_critical_path}, "
                f"days_until_affected_activity={days_until_affected_activity}"
            ),
        }

    return ToolSpec(
        name="classify_urgency",
        description=(
            "Classify RFI urgency as low/medium/high based on safety, critical-path "
            "impact, and days until the affected activity."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "The RFI question."},
                "is_safety": {"type": "boolean", "default": False},
                "is_critical_path": {"type": "boolean", "default": False},
                "days_until_affected_activity": {
                    "type": "integer",
                    "description": "Calendar days until the next dependent activity starts. Use 99 if unknown.",
                },
            },
            "required": ["question"],
        },
        fn=classify_urgency,
    )


def _estimate_impact() -> ToolSpec:
    def estimate_impact(
        scenario: str,
        rough_labor_hours: float = 0.0,
        rough_material_usd: float = 0.0,
        schedule_delay_days: float = 0.0,
        labor_rate_usd_per_hour: float = 95.0,
    ) -> dict[str, Any]:
        labor_cost = rough_labor_hours * labor_rate_usd_per_hour
        total_cost = labor_cost + rough_material_usd
        return {
            "scenario": scenario,
            "estimated_cost_usd": round(total_cost, 2),
            "estimated_schedule_delay_days": schedule_delay_days,
            "breakdown": {
                "labor_cost_usd": round(labor_cost, 2),
                "material_cost_usd": round(rough_material_usd, 2),
                "labor_hours": rough_labor_hours,
                "labor_rate_usd_per_hour": labor_rate_usd_per_hour,
            },
            "note": "Rough order-of-magnitude only; not a change-order estimate.",
        }

    return ToolSpec(
        name="estimate_impact",
        description=(
            "Produce a rough order-of-magnitude cost and schedule estimate for an RFI "
            "resolution scenario. Use conservative inputs; do not promise precision."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "scenario": {"type": "string", "description": "Short label for the scenario."},
                "rough_labor_hours": {"type": "number", "default": 0.0},
                "rough_material_usd": {"type": "number", "default": 0.0},
                "schedule_delay_days": {"type": "number", "default": 0.0},
                "labor_rate_usd_per_hour": {"type": "number", "default": 95.0},
            },
            "required": ["scenario"],
        },
        fn=estimate_impact,
    )


def build_rfi_tools(retriever: Retriever) -> ToolRegistry:
    return ToolRegistry(
        tools=[
            _make_retrieve_tool(retriever),
            _classify_urgency(),
            _estimate_impact(),
        ]
    )


def build_dcr_tools(retriever: Retriever) -> ToolRegistry:
    return ToolRegistry(tools=[_make_retrieve_tool(retriever)])
