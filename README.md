# Site Copilot

An agentic **RFI triage** and **Daily Construction Report** assistant for jobsite teams.

Built as a portfolio demo for [Suffolk Construction's Site AI Engineer](https://suffolk.com) role. Aligned to Suffolk's "Seamless Platform" and "Construction Site of the Future" vision: two MVP agents you could walk onto a project and stand up in a sprint.

> The Site AI Engineer JD names five high-impact use cases: reporting, RFIs, lookahead planning, progress updates, and materials tracking. Site Copilot ships working agents for the two highest-frequency pains — **RFIs and daily reports** — on the same stack vocabulary Suffolk recruits on.

## What it does

| Agent | Input | Output |
| --- | --- | --- |
| **RFI Triage** | Incoming RFI (question, references, discipline) | Citation-backed draft response, urgency, schedule and cost impact, EOR-escalation flag |
| **Daily Report** | Raw end-of-shift field notes from a Super | Structured DCR with normalized crews, equipment, deliveries, risks, follow-ups, exec summary |

Both agents share a single **Agentic RAG layer** over a synthetic project corpus (5 spec sections, 8 prior RFIs, 3 daily reports) for the fictional Allerton Tower — a 32-story Boston project named after Suffolk's HQ address.

## Demo (60 seconds)

Requires Python 3.11+. If you have [uv](https://docs.astral.sh/uv/) installed
(`curl -LsSf https://astral.sh/uv/install.sh | sh`), `uv venv && uv pip install -e .[ui,dev]` is the fastest path.

```bash
# 1. Install
make install

# 2. Try the eval suite — runs offline with mocked LLM, exercises the full agent loop
make eval

# 3. Real run with Claude
export ANTHROPIC_API_KEY=sk-ant-...
make install-ui
make ui          # Streamlit
# or
make serve       # FastAPI on :8000
```

Then POST an RFI:

```bash
curl -X POST http://localhost:8000/agents/rfi/triage \
  -H "Content-Type: application/json" \
  -d @data/samples/rfi_inbox.json
```

## How it maps to Suffolk's stack

| This demo | Production target (per JD) |
| --- | --- |
| Anthropic Claude SDK | **AWS Bedrock** `anthropic.claude-sonnet-4-6-v1:0` (drop-in via `LLMClient`) |
| BM25 + optional Chroma | **OpenSearch** hybrid (BM25 + kNN) — `Retriever._rrf` is the same RRF fusion |
| FastAPI + Pydantic | Same |
| Streamlit demo UI | **Teams / SharePoint** apps for field consumption |
| JSONL traces on disk | **CloudWatch Logs** → **Databricks Lakehouse** bronze |
| GitHub Actions CI | Same |
| `infra/terraform/` stub | Production Terraform / CloudFormation |
| Python eval harness | Bedrock Evaluation / Databricks ML monitoring |

See [`docs/architecture.md`](docs/architecture.md) for the full diagram.

## Why these two agents

The JD calls out **"cut down reporting" and "accelerate RFIs"** by name. Industry baseline: RFI responses average ~9.7 days; a typical superintendent spends 30–60 minutes nightly on the DCR. Both are high-frequency, citation-heavy, and bound by project documents — the textbook agentic RAG shape.

The agents are intentionally narrow but real:

- **RFI agent** runs a 3-tool loop (`retrieve` → `classify_urgency` → `estimate_impact`) before drafting. Every spec claim must come from a retrieved chunk; if the spec is silent it says so rather than hallucinating.
- **DCR agent** retrieves the last 1–2 daily reports for continuity, normalizes shorthand, and surfaces risks categorized into a fixed taxonomy (safety / schedule / quality / weather / material / coordination) so downstream BI can aggregate.

Both share the same agent loop (`agents/base.py`) — adding a third agent (lookahead planning, materials tracking, submittal log) is ~80 lines of code.

## What's in the box

```
src/site_copilot/
  agents/         # base loop + RFI + DCR agents
  rag/            # store interface, BM25 + Chroma, hybrid RRF retriever
  tools/          # retrieve, classify_urgency, estimate_impact
  observability/  # JSONL tracer, cost estimator, drift detector
  api/            # FastAPI app + lifespan-built agents
  ui/             # Streamlit demo
  llm.py          # Anthropic client + mock-LLM mode for offline runs

data/corpus/      # 5 specs, 8 prior RFIs, 3 daily reports
data/samples/     # 5 incoming RFIs + 2 field-note blobs to demo

evals/            # YAML test cases + scorers + runner (CI-gated)
infra/            # Dockerfile, docker-compose, Terraform stub
.github/          # CI (lint + tests + evals on every PR) + deploy workflow
docs/             # architecture, stack mapping, demo script, LLMOps notes
```

## LLMOps story

- **Tracing**: every LLM call, tool call, and agent span lands in `traces/traces-YYYY-MM-DD.jsonl` with run_id, token counts, latency, and cost. Same shape as the records you'd feed Databricks bronze.
- **Cost**: per-call `cost_usd` computed against per-million-token pricing tables in `llm.py`.
- **Eval gate**: `evals/run_evals.py` runs 4 RFI cases through the agent on every CI run; failures block merges.
- **Drift**: `observability/drift.py` watches response length, citation count, and escalation-rate distributions over a rolling window. Sketch only — the production wire is to Bedrock Evaluation or Databricks ML monitoring.

## Why Claude

The JD lists **"Hands-on expertise with Claude Code"** as required. Site Copilot is built *in* Claude Code, uses Claude as the agent runtime, and the agent loop is portable to Claude on Bedrock with zero code changes (Bedrock Converse API matches the Anthropic tool-use schema 1:1).

## Honest limits

This is a one-week demo, not a production app. Specifically:

- The corpus is **synthetic but realistic** — real specs would need OCR, table extraction, and drawing-callout linking.
- The Terraform deploys infra but no autoscaling, alarms, or multi-account boundaries — those are stubbed in the README, not the `.tf` files.
- The DCR agent doesn't ingest **OpenSpace** photos or **Procore** RFI submissions yet — those are the next two integrations.
- The drift detector is the smallest thing that could plausibly trigger an alert; production needs proper distribution tests (KS or population-stability index) and a baseline window.

What it *is*: a working, end-to-end agentic system on the exact stack Suffolk hires on, with the LLMOps spine in place. Pick a real workflow, point it at real specs, and the bones don't change.

---

Contact: see CV.
