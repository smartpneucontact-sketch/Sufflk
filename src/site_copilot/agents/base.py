from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from site_copilot.llm import LLMClient, estimate_cost_usd
from site_copilot.observability import Tracer, new_run_id
from site_copilot.tools import ToolRegistry


@dataclass
class AgentResult:
    run_id: str
    final_text: str
    parsed: dict[str, Any] | None
    steps: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    tool_invocations: list[dict[str, Any]] = field(default_factory=list)


class Agent:
    """Base agent — runs a tool-use loop against the LLM client.

    The loop is intentionally simple: model proposes tool calls, we execute
    them, feed the results back, and continue until the model emits a final
    text response or we hit max_steps. This is the same loop shape Bedrock's
    Converse API and Azure OpenAI's tool-use surface use, which keeps the
    abstraction portable."""

    name: str = "agent"
    system_prompt: str = ""

    def __init__(
        self,
        *,
        llm: LLMClient,
        tools: ToolRegistry,
        tracer: Tracer,
        max_steps: int = 6,
    ):
        self.llm = llm
        self.tools = tools
        self.tracer = tracer
        self.max_steps = max_steps

    def run(self, user_payload: str) -> AgentResult:
        run_id = new_run_id()
        self.tracer.event("agent.start", agent=self.name, payload_preview=user_payload[:160])

        messages: list[dict[str, Any]] = [{"role": "user", "content": user_payload}]
        tool_invocations: list[dict[str, Any]] = []
        total_in = 0
        total_out = 0
        final_text = ""

        for step in range(self.max_steps):
            with self.tracer.span("llm.call", agent=self.name, step=step):
                resp = self.llm.complete(
                    system=self.system_prompt,
                    messages=messages,
                    tools=self.tools.to_anthropic(),
                    max_tokens=1500,
                )
            total_in += resp.input_tokens
            total_out += resp.output_tokens
            self.tracer.event(
                "llm.usage",
                agent=self.name,
                step=step,
                in_tokens=resp.input_tokens,
                out_tokens=resp.output_tokens,
                stop_reason=resp.stop_reason,
            )

            if resp.tool_calls:
                # Echo the assistant turn (text + tool_use blocks) back into messages,
                # then append a tool_result user turn.
                assistant_blocks: list[dict[str, Any]] = []
                if resp.text:
                    assistant_blocks.append({"type": "text", "text": resp.text})
                for tc in resp.tool_calls:
                    assistant_blocks.append(
                        {"type": "tool_use", "id": tc["id"], "name": tc["name"], "input": tc["input"]}
                    )
                messages.append({"role": "assistant", "content": assistant_blocks})

                tool_result_blocks: list[dict[str, Any]] = []
                for tc in resp.tool_calls:
                    with self.tracer.span("tool.call", tool_name=tc["name"], step=step):
                        result = self.tools.call(tc["name"], tc["input"])
                    tool_invocations.append({"step": step, "name": tc["name"], "input": tc["input"], "result": result})
                    tool_result_blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tc["id"],
                            "content": json.dumps(result, default=str),
                        }
                    )
                messages.append({"role": "user", "content": tool_result_blocks})
                continue

            final_text = resp.text
            break

        parsed = _maybe_parse_json(final_text)
        cost = estimate_cost_usd(self.llm.model, total_in, total_out)
        self.tracer.event(
            "agent.end",
            agent=self.name,
            steps=step + 1,
            in_tokens=total_in,
            out_tokens=total_out,
            cost_usd=round(cost, 6),
        )

        return AgentResult(
            run_id=run_id,
            final_text=final_text,
            parsed=parsed,
            steps=step + 1,
            input_tokens=total_in,
            output_tokens=total_out,
            cost_usd=cost,
            tool_invocations=tool_invocations,
        )


def _maybe_parse_json(text: str) -> dict[str, Any] | None:
    """Pull a JSON object out of arbitrary LLM text.

    Handles: pure JSON, JSON in ```json ... ``` fences, JSON inside an
    explanatory paragraph, and JSON with a 'Here is the output:' preamble.
    Picks the longest balanced top-level {...} block as the candidate.
    """
    if not text:
        return None

    # First try: clean strip + fence removal.
    candidate = text.strip()
    if candidate.startswith("```"):
        first = candidate.find("\n")
        last = candidate.rfind("```")
        if first != -1 and last != -1 and last > first:
            candidate = candidate[first + 1 : last].strip()
    if candidate.startswith("{") and candidate.endswith("}"):
        try:
            return json.loads(candidate)
        except json.JSONDecodeError:
            pass

    # Second try: scan the original text for the largest balanced {...} block.
    best: str | None = None
    depth = 0
    start = -1
    in_str = False
    esc = False
    for i, ch in enumerate(text):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            if depth > 0:
                depth -= 1
                if depth == 0 and start != -1:
                    block = text[start : i + 1]
                    if best is None or len(block) > len(best):
                        best = block
                    start = -1

    if best:
        try:
            return json.loads(best)
        except json.JSONDecodeError:
            return None
    return None
