# Demo script — 5 minutes with a hiring panel

## Setup (offline, before the meeting)

```bash
pip install -e .[ui]
export ANTHROPIC_API_KEY=sk-ant-...   # or rely on SITE_COPILOT_USE_MOCK_LLM=1
streamlit run src/site_copilot/ui/streamlit_app.py
```

In a separate terminal:
```bash
uvicorn site_copilot.api.main:app --port 8000
```

Have these tabs ready:
1. Streamlit UI
2. `data/corpus/specs/03_30_00_cast_in_place_concrete.md` open in editor
3. `traces/traces-YYYY-MM-DD.jsonl` in a terminal (`tail -f`)
4. README and `docs/architecture.md`

## 0:00 — Frame

> "The JD calls for AI agents that cut down reporting and accelerate RFIs.
> I built both, on the stack you recruit on. Two minutes of demo, three of
> architecture."

## 0:30 — RFI demo

Open Streamlit → **RFI Triage** tab. Select **RFI-0184** (column cover at L11
transition).

Click **Triage RFI**. Show:
- **Tool invocations**: retrieve(spec section), retrieve(prior RFIs),
  classify_urgency, estimate_impact.
- **Output JSON**: cited `spec:03_30_00_concrete §3.04` + `prior_rfi:rfi_0142`
  (the analogous L9 case). Urgency `medium`. EOR review **yes**. Cost ≈ $0.
- **Telemetry**: input/output tokens, total cost ≈ $0.005, latency ≈ 2 sec.

Side-by-side with the spec file open: every cited section is real text in
the corpus. No hallucinations.

> "The agent retrieves before it drafts. Every claim has a citation. It
> flagged that this is the third time we've answered this same column-cover
> question — that's the signal Operations Excellence wants to standardize
> the drawing detail."

## 2:00 — DCR demo

Switch to **Daily Report** tab. Select 2026-05-22 field notes. Show how
sloppy the input is.

Click **Draft DCR**. Show:
- Normalized crews-on-site (numeric, not "concrete crew 16").
- Risks categorized: `quality` (UT failure CL-209), `material` (hinge lead
  time HW-12), `weather` (28°F forecast — ties to open RFI-0185).
- Follow-ups in imperative voice.
- Exec summary < 4 sentences.

> "The Super dictates this on the train home. The PE has a clean DCR in
> their inbox before they make dinner. Critical-path risks are tagged for
> the next morning's huddle."

## 3:30 — Architecture and stack

Open `docs/architecture.md`. Walk the Mermaid diagram:
- Tool-use loop, swappable LLM (Claude SDK today, Bedrock in prod).
- Hybrid RAG using RRF — same algorithm as OpenSearch hybrid search.
- JSONL traces → CloudWatch / Databricks bronze.

Open `infra/terraform/` — point to `ecs.tf`, `iam.tf` (`bedrock:InvokeModel`
allow), and `opensearch.tf`.

> "The local stack is provider-agnostic by design. Swap the constructor in
> `llm.py` to a Bedrock client and the agent loop doesn't change — the
> Bedrock Converse API matches the Anthropic tool-use schema 1:1."

## 4:30 — LLMOps

Show `tail -f traces/traces-*.jsonl`. Run a fresh RFI in another tab — events
stream live. Point out: `run_id`, `in_tokens`, `out_tokens`, span elapsed_ms,
tool call inputs.

Open `evals/rfi_cases.yaml`. Show that CI runs these on every PR and gates
merges on the scorer pass-rate.

> "Adoption, drift, and cost monitoring all start as fields on these JSONL
> events. The drift detector is a sketch — production wires this to
> Bedrock Evaluation."

## Close

> "Two agents, real LLMOps, the stack you hire on. Tell me which jobsite
> pain you want me to ship the third agent for."

## Anticipated questions

**Q: How do you handle hallucinations?**
The system prompt forbids invented spec text — the agent is told to write
"not found in retrieved corpus" instead. The eval scorer checks every
response for citation presence. A future enhancement is to enforce that
every numeric or quoted claim links to a chunk_id.

**Q: How would you scale this to 100 sites?**
Multi-tenant: each project gets its own OpenSearch index, traces tagged
with `project_id`. Agents stay shared. Cost per RFI is ~$0.005 at current
Claude pricing — at 50 RFIs/site/week, that's <$15/site/month.

**Q: What about Procore / OpenSpace integration?**
Procore has a documented REST API for RFIs and Daily Logs; Boomi connector
exists per Suffolk's own [case study](https://boomi.com/resources/resources-library/case-study-suffolk-construction/).
OpenSpace exports site documentation; that's the natural next integration
for the DCR agent (photo metadata → risk surfacing).

**Q: How would you handle adoption?**
Field tools die in the field, not on the dev machine. I'd run the same
playbook the JD asks for: AI Champion on each project, ship one agent at a
time, measure time saved per RFI/DCR, retire workflows that get displaced
rather than layering tools on top.
