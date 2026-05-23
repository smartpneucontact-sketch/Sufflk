# LLMOps notes

This is the "monitor latency, cost, adoption, and drift" line from the JD —
how Site Copilot operationalizes those four signals.

## Latency

Every LLM call and tool call is wrapped in a `Tracer.span(...)`. The
resulting JSONL events carry `elapsed_ms` per span and per agent run:

```json
{"ts": "...", "run_id": "run_a1b2c3d4", "kind": "span.end", "name": "llm.call", "elapsed_ms": 1240.7}
```

p50/p95 per agent is a one-line `awk` away. In prod those events go to
CloudWatch Logs; the Insights query is a `parse + stats avg, percentile(elapsed_ms, 95) by name`.

## Cost

`llm.py` carries per-million-token pricing for Claude Opus / Sonnet / Haiku.
Each agent run emits its `cost_usd` total. Track it by:

- Project (tag `project_id`)
- Agent (tag `agent`)
- Outcome (escalated vs auto-resolved)

This is the input to the ROI conversation: "Site Copilot resolved 47 RFIs
last week for $0.23 in inference, saving an estimated 31 PE-hours."

## Adoption

Tag every run with `actor_id` (the PE/Super who triggered it) and
`source_surface` (Streamlit, Teams app, Procore plugin). Two reports:

- **Weekly active users per project** — adoption curve.
- **Auto-resolution rate** — share of RFIs the agent answered without
  human edit. If this is dropping, the agent is degrading; if it's
  climbing, the agent is replacing manual workflow.

## Drift

Three rolling signals in `observability/drift.py`:

1. **Response length**: sudden long-tail = hallucination or scope creep.
2. **Citation count**: drop = retrieval regression.
3. **Escalation rate**: spike = unfamiliar question pattern (good — the
   agent is being cautious); drop with low-citation = bad (the agent is
   being lazy).

Production swap is **Bedrock Evaluation** or **Databricks ML monitoring**
with proper population-stability index (PSI) on these distributions
against a labeled baseline.

## Evaluation

`evals/rfi_cases.yaml` defines 4 cases with expected behaviors. The runner
exercises the full agent loop, the scorer in `evals/scorers.py` checks:

- Did the agent return valid JSON?
- Did it cite the required source type?
- Is the urgency in the acceptable set?
- Does the EOR-escalation flag match?
- Does the draft response mention the required keywords (anti-hallucination)?

CI runs this on every PR with `SITE_COPILOT_USE_MOCK_LLM=1`. Production
gates merges on a real-LLM run against a held-out test set.

## What's deliberately *not* here

- Full RAG eval (faithfulness, answer relevancy, context precision) — would
  add ragas or a custom scorer when the corpus is real and labeled.
- Red-teaming for adversarial RFIs (prompt injection from subs) — needs an
  attacker-corpus and a separate eval.
- Online human feedback loop — needs a PE thumbs-up/edit channel before
  it's worth building.

These belong on the LLMOps roadmap, not in the demo.
