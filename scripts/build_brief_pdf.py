#!/usr/bin/env python3
"""Generate the Site Copilot product brief PDF.

Run:
    python3 scripts/build_brief_pdf.py

Output:
    Site_Copilot_Brief.pdf  (in the repo root)
"""

from pathlib import Path

from fpdf import FPDF

# === Palette ===
INK = (20, 28, 48)
INK_SOFT = (72, 82, 105)
MUTED = (130, 140, 158)
ACCENT = (245, 158, 11)
ACCENT_SOFT = (255, 246, 226)
BORDER = (224, 228, 235)
CODE_BG = (244, 246, 250)
CODE_INK = (40, 50, 75)
ROW_ALT = (250, 251, 253)

# === Layout constants ===
PAGE_W = 612  # letter @ pt
PAGE_H = 792
MARGIN = 56
CONTENT_W = PAGE_W - 2 * MARGIN

FONT_DIR = "/System/Library/Fonts/Supplemental"
FONT_FAMILY = "Body"
MONO_FAMILY = "Mono"


# ---------- Helpers ----------

class Brief(FPDF):
    def footer(self):
        self.set_y(-32)
        self.set_font(FONT_FAMILY, size=8)
        self.set_text_color(*MUTED)
        self.set_draw_color(*BORDER)
        self.set_line_width(0.4)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.set_y(-26)
        self.cell(0, 10, "Site Copilot  ·  portfolio brief", align="L")
        self.set_y(-26)
        self.cell(0, 10, f"page {self.page_no()} of {{nb}}", align="R")


def _register_fonts(pdf: FPDF) -> None:
    pdf.add_font(FONT_FAMILY, style="", fname=f"{FONT_DIR}/Arial.ttf")
    pdf.add_font(FONT_FAMILY, style="B", fname=f"{FONT_DIR}/Arial Bold.ttf")
    pdf.add_font(FONT_FAMILY, style="I", fname=f"{FONT_DIR}/Arial Italic.ttf")
    pdf.add_font(FONT_FAMILY, style="BI", fname=f"{FONT_DIR}/Arial Bold Italic.ttf")
    pdf.add_font(MONO_FAMILY, style="", fname=f"{FONT_DIR}/Courier New.ttf")
    pdf.add_font(MONO_FAMILY, style="B", fname=f"{FONT_DIR}/Courier New Bold.ttf")


def rule(pdf: FPDF, width: float = 60, height: float = 2.5, color=ACCENT) -> None:
    pdf.set_fill_color(*color)
    pdf.rect(pdf.get_x(), pdf.get_y(), width, height, "F")
    pdf.ln(height + 14)


def h1(pdf: FPDF, text: str) -> None:
    pdf.set_font(FONT_FAMILY, "B", 30)
    pdf.set_text_color(*INK)
    pdf.cell(0, 36, text, new_x="LMARGIN", new_y="NEXT")


def h2(pdf: FPDF, text: str) -> None:
    pdf.ln(4)
    pdf.set_font(FONT_FAMILY, "B", 9)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 12, text.upper(), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def body(pdf: FPDF, text: str, size: int = 10.5, color=INK_SOFT) -> None:
    pdf.set_font(FONT_FAMILY, "", size)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, 15, text, new_x="LMARGIN", new_y="NEXT")


def bullets(pdf: FPDF, items: list[str], size: int = 10.5) -> None:
    pdf.set_font(FONT_FAMILY, "", size)
    pdf.set_text_color(*INK_SOFT)
    for item in items:
        x0 = pdf.get_x()
        pdf.set_x(x0 + 4)
        pdf.cell(10, 15, "•")
        pdf.set_x(x0 + 16)
        pdf.multi_cell(CONTENT_W - 16, 15, item, new_x="LMARGIN", new_y="NEXT")


def callout(pdf: FPDF, title: str, lines: list[tuple[str, str]]) -> None:
    y0 = pdf.get_y()
    height = 24 + 18 * len(lines) + 8
    pdf.set_fill_color(*ACCENT_SOFT)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.5)
    pdf.rect(MARGIN, y0, CONTENT_W, height, "DF")

    pdf.set_xy(MARGIN + 14, y0 + 10)
    pdf.set_font(FONT_FAMILY, "B", 9)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 12, title.upper(), new_x="LMARGIN", new_y="NEXT")
    for label, value in lines:
        pdf.set_x(MARGIN + 14)
        pdf.set_font(FONT_FAMILY, "B", 11)
        pdf.set_text_color(*INK)
        pdf.cell(80, 18, label)
        pdf.set_font(FONT_FAMILY, "", 11)
        pdf.set_text_color(*INK_SOFT)
        pdf.cell(0, 18, value, new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(y0 + height + 10)


def stack_table(pdf: FPDF, rows: list[tuple[str, str]]) -> None:
    col_w = CONTENT_W / 2
    row_h = 22

    pdf.set_fill_color(*INK)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font(FONT_FAMILY, "B", 9)
    pdf.cell(col_w, row_h, "  THIS DEMO", border=0, fill=True)
    pdf.cell(col_w, row_h, "  SUFFOLK PRODUCTION", new_x="LMARGIN", new_y="NEXT", border=0, fill=True)

    pdf.set_font(FONT_FAMILY, "", 10)
    for i, (left, right) in enumerate(rows):
        bg = ROW_ALT if i % 2 == 0 else (255, 255, 255)
        pdf.set_fill_color(*bg)
        pdf.set_text_color(*INK)
        pdf.set_draw_color(*BORDER)
        pdf.cell(col_w, row_h, "  " + left, border="B", fill=True)
        pdf.set_text_color(*INK_SOFT)
        pdf.cell(col_w, row_h, "  " + right, new_x="LMARGIN", new_y="NEXT", border="B", fill=True)
    pdf.ln(6)


def agent_card(pdf: FPDF, label: str, name: str, what: str, why: str) -> None:
    y0 = pdf.get_y()
    h = 112
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(*BORDER)
    pdf.rect(MARGIN, y0, CONTENT_W, h, "DF")
    pdf.set_fill_color(*ACCENT)
    pdf.rect(MARGIN, y0, 3, h, "F")

    pdf.set_xy(MARGIN + 16, y0 + 10)
    pdf.set_font(FONT_FAMILY, "B", 8)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 11, label.upper(), new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(MARGIN + 16)
    pdf.set_font(FONT_FAMILY, "B", 14)
    pdf.set_text_color(*INK)
    pdf.cell(0, 18, name, new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(MARGIN + 16)
    pdf.set_font(FONT_FAMILY, "", 10)
    pdf.set_text_color(*INK_SOFT)
    pdf.multi_cell(CONTENT_W - 32, 14, what)
    pdf.set_x(MARGIN + 16)
    pdf.set_font(FONT_FAMILY, "I", 9.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(CONTENT_W - 32, 13, why)

    pdf.set_y(y0 + h + 10)


def trace_block(pdf: FPDF, title: str, lines: list[str]) -> None:
    """Code-style block showing a sample agent reasoning trace."""
    y0 = pdf.get_y()
    line_h = 13
    pad_y = 12
    height = pad_y * 2 + line_h * len(lines) + 16

    pdf.set_fill_color(*CODE_BG)
    pdf.set_draw_color(*BORDER)
    pdf.set_line_width(0.4)
    pdf.rect(MARGIN, y0, CONTENT_W, height, "DF")

    pdf.set_xy(MARGIN + 14, y0 + 10)
    pdf.set_font(FONT_FAMILY, "B", 8)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 11, title.upper(), new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(MONO_FAMILY, "", 8.8)
    pdf.set_text_color(*CODE_INK)
    for line in lines:
        pdf.set_x(MARGIN + 14)
        pdf.cell(0, line_h, line, new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(y0 + height + 10)


def stat_grid(pdf: FPDF, cells: list[tuple[str, str, str]]) -> None:
    """Three-up stat grid: (label, big value, helper text)."""
    y0 = pdf.get_y()
    cell_w = CONTENT_W / len(cells)
    h = 64

    pdf.set_draw_color(*BORDER)
    pdf.set_line_width(0.5)
    pdf.set_fill_color(255, 255, 255)
    pdf.rect(MARGIN, y0, CONTENT_W, h, "DF")
    for i in range(1, len(cells)):
        x = MARGIN + cell_w * i
        pdf.line(x, y0 + 8, x, y0 + h - 8)

    for i, (label, value, helper) in enumerate(cells):
        x = MARGIN + cell_w * i + 14
        pdf.set_xy(x, y0 + 10)
        pdf.set_font(FONT_FAMILY, "B", 8)
        pdf.set_text_color(*MUTED)
        pdf.cell(cell_w - 28, 11, label.upper(), new_x="LMARGIN", new_y="NEXT")

        pdf.set_xy(x, y0 + 22)
        pdf.set_font(FONT_FAMILY, "B", 18)
        pdf.set_text_color(*INK)
        pdf.cell(cell_w - 28, 22, value, new_x="LMARGIN", new_y="NEXT")

        pdf.set_xy(x, y0 + 46)
        pdf.set_font(FONT_FAMILY, "", 9)
        pdf.set_text_color(*INK_SOFT)
        pdf.cell(cell_w - 28, 12, helper, new_x="LMARGIN", new_y="NEXT")

    pdf.set_y(y0 + h + 10)


# ---------- Content ----------

def build() -> Path:
    pdf = Brief("portrait", "pt", "letter")
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_auto_page_break(True, margin=66)
    pdf.alias_nb_pages()
    _register_fonts(pdf)
    pdf.add_page()

    # === PAGE 1 ===
    # Header
    h1(pdf, "Site Copilot")
    pdf.set_font(FONT_FAMILY, "", 13)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(0, 18, "Agentic RFI and Daily Report assistant for construction jobsites.",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    rule(pdf, width=72)

    # Author block
    pdf.set_font(FONT_FAMILY, "B", 10)
    pdf.set_text_color(*INK)
    pdf.cell(0, 14, "Arsen Khanguieldyan", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT_FAMILY, "", 10)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(0, 14, "arsen.khanguieldyan@gmail.com", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 14, "Portfolio piece for Suffolk Construction",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Live demo callout
    callout(pdf, "Try it live", [
        ("Live demo", "suffolk-construction.up.railway.app"),
        ("Source code", "github.com/smartpneucontact-sketch/Sufflk"),
        ("Model", "Anthropic Claude Sonnet 4.6  ·  ~$0.05 per RFI triage"),
    ])

    # Summary
    h2(pdf, "Summary")
    body(pdf,
         "Site Copilot is a working portfolio demo built on the same stack Suffolk's AI Studio runs on. "
         "Two production-shaped AI agents — RFI triage and Daily Construction Report drafting — run on "
         "Claude Sonnet 4.6 with Agentic RAG over a synthetic project corpus. Every component has a 1:1 "
         "production target: FastAPI stays the same, hybrid retrieval maps directly onto OpenSearch, "
         "JSONL telemetry ingests into Databricks bronze, and a Terraform sketch deploys the whole thing "
         "to AWS Bedrock + ECS Fargate. Built in a week. Live and demoable in a browser.")

    # Problem
    h2(pdf, "The problem this solves")
    body(pdf,
         "On a Suffolk-scale project, project engineers field hundreds of RFIs. Industry baseline for "
         "response is around 9.7 days. End-of-shift, a superintendent spends 30 to 60 minutes turning "
         "sloppy field notes into a structured Daily Construction Report. Both are high-frequency, "
         "citation-heavy, and bound entirely by the project's own documents — the textbook shape of an "
         "Agentic RAG workflow.")

    # Agent cards
    h2(pdf, "What it ships")
    agent_card(pdf, "Agent 01",
               "RFI Triage",
               "Reads an incoming RFI, retrieves relevant spec sections and similar prior RFIs from the "
               "project corpus, drafts a citation-backed response, classifies urgency, estimates rough cost "
               "and schedule impact across multiple resolution scenarios, and flags whether escalation to "
               "the Structural Engineer of Record is required.",
               "Why it matters: compresses the 9.7-day industry baseline to roughly 30 seconds and "
               "$0.05 per RFI. Every claim is cited. Refuses to over-escalate when the spec is "
               "unambiguous and prior EOR rulings are already on record.")

    agent_card(pdf, "Agent 02",
               "Daily Construction Report",
               "Takes raw, fragmented end-of-shift superintendent notes and produces a structured DCR — "
               "normalized crews, areas worked, equipment, deliveries, follow-ups, and an executive summary. "
               "Risks are bucketed into a fixed taxonomy (safety, schedule, quality, weather, material, "
               "coordination) so downstream BI can aggregate across the portfolio.",
               "Why it matters: turns 30 to 60 minutes of nightly paperwork into a 30-second review. "
               "Open RFIs in the notes are auto-extracted; weather forecasts are flagged against pending work.")

    # === PAGE 2 ===
    pdf.add_page()

    # Stack mapping
    h2(pdf, "How it maps to Suffolk's named stack")
    body(pdf,
         "Every component in this demo has a 1:1 production target. The swap from local demo to "
         "deployed AWS is mechanical, not architectural. The LLMClient interface mirrors Bedrock's "
         "Converse API, the VectorStore Protocol mirrors OpenSearch's kNN, and the trace JSONL format "
         "ingests directly into Databricks bronze with no transformation.")
    pdf.ln(4)

    stack_table(pdf, [
        ("Anthropic SDK + Claude Sonnet 4.6", "AWS Bedrock — anthropic.claude-sonnet-4-6"),
        ("BM25 (+ optional Chroma), fused via RRF", "OpenSearch hybrid (BM25 + kNN)"),
        ("FastAPI + Pydantic", "FastAPI + Pydantic"),
        ("JSONL traces on disk", "CloudWatch Logs → Databricks bronze"),
        ("Single-page HTML UI", "Teams / SharePoint apps"),
        ("GitHub Actions CI (lint + tests + eval gate)", "Same"),
        ("infra/terraform/ sketch (ECS Fargate)", "Production Terraform / CloudFormation"),
        ("Tool-use loop in agents/base.py", "Bedrock Converse multi-tool loop"),
    ])

    # Sample trace block
    h2(pdf, "Sample agent reasoning (real run)")
    body(pdf,
         "Here is the actual tool sequence the RFI agent ran on the question 'Drawing shows column "
         "cover at 1-1/4 in., spec calls for 1-1/2 in., which governs?' Every retrieval, classification, "
         "and impact estimate is captured in the trace.")
    trace_block(pdf, "run_783c6865ed17  ·  3 steps  ·  15,023 in / 1,819 out tokens  ·  $0.072", [
        "step 0  retrieve(query=\"concrete cover requirements columns spec 03 30 00\",",
        "                  source_type=\"spec\")",
        "        -> 7 chunks. top: spec:03_30_00_concrete §3.04 (score 8.36)",
        "",
        "step 0  retrieve(query=\"column concrete cover conflict drawing vs spec\",",
        "                  source_type=\"prior_rfi\")",
        "        -> 6 chunks. top: prior_rfi:rfi_0089 (score 16.01)",
        "",
        "step 0  classify_urgency(is_safety=true, is_critical_path=true)",
        "        -> urgency=\"high\"",
        "",
        "step 1  estimate_impact(scenario=\"catch before placement\",",
        "                         labor_hours=4, material_usd=50)",
        "        -> cost=$430, delay=0d",
        "",
        "step 1  estimate_impact(scenario=\"rebar already tied, must reset\",",
        "                         labor_hours=16, material_usd=200)",
        "        -> cost=$1,720, delay=1d",
        "",
        "step 2  final answer (cited): spec governs, 1-1/2 in. minimum.",
    ])

    # Cost / scale economics
    h2(pdf, "Economics at scale")
    body(pdf,
         "Inference cost stays trivial even at portfolio scale. At current Sonnet 4.6 pricing and "
         "typical project RFI volume:")
    stat_grid(pdf, [
        ("PER RFI", "$0.05", "real measured cost"),
        ("PER SITE / WEEK", "~$2.50", "at 50 RFIs/week"),
        ("PER SITE / MONTH", "<$15", "Anthropic bill"),
    ])

    # === PAGE 3 ===
    pdf.add_page()

    # LLMOps story
    h2(pdf, "LLMOps")
    body(pdf,
         "The role asks for monitoring latency, cost, adoption, and drift. The demo ships all four:")
    bullets(pdf, [
        "Latency: every LLM call and tool call is wrapped in a span with elapsed_ms. p50 / p95 per "
        "agent is a one-line awk on the JSONL trace.",
        "Cost: per-call cost_usd is computed from per-million-token pricing in llm.py. Every run "
        "carries its cost in the response payload — visible in the UI telemetry strip.",
        "Adoption: each run carries actor_id and source_surface tags. Weekly active users per project "
        "and auto-resolution rate (share of RFIs the agent answered without human edit) are one query away.",
        "Drift: a rolling window watches three signals — response length, citation count, and "
        "escalation rate — and emits an alert on a 3-sigma move. Production target is Bedrock "
        "Evaluation or Databricks ML monitoring with a labeled baseline window.",
        "Eval gate: four RFI cases with expected behaviors live in evals/rfi_cases.yaml. CI runs them "
        "in mock-LLM mode on every PR; merges block on scorer failures.",
    ])

    # Why this approach
    h2(pdf, "Why this approach")
    body(pdf,
         "Suffolk's AI Studio runs a 'walk the jobsite, ship MVPs in days, hand off to central engineering' "
         "playbook. Site Copilot is precisely the artifact that playbook produces: pick a workflow pain, "
         "build the agent against the project's own corpus, ship it on the central platform's stack, stand "
         "up the LLMOps spine, hand off cleanly. The two agents shipped here are the two most-cited use "
         "cases in Suffolk's hiring materials — RFIs and daily reports. The same loop trivially extends to "
         "lookahead planning, materials tracking, or submittal log review: new system prompt, maybe one new "
         "tool, ~80 lines of code.")

    # What is intentionally not built
    h2(pdf, "What is intentionally not built")
    body(pdf,
         "This is a one-week portfolio demo, not a production deploy. The README's gap list is direct:")
    bullets(pdf, [
        "Corpus is synthetic but realistic. Real specs would need OCR, table extraction, and "
        "drawing-callout linking.",
        "Terraform deploys infra but no autoscaling, alarms, or multi-account boundaries.",
        "No Procore or OpenSpace integration yet. Procore for RFI/DCR submission and OpenSpace for "
        "photo metadata feeding the DCR risk surfacing are the natural next two integrations.",
        "Drift detector is the smallest thing that could plausibly trigger an alert. Production "
        "needs proper distribution tests (KS, PSI) against a labeled baseline.",
    ])

    # Closing
    h2(pdf, "In one line")
    pdf.set_font(FONT_FAMILY, "I", 11.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 16,
                   "Working agentic AI on Suffolk's exact stack vocabulary, against Suffolk's most-cited "
                   "use cases, shippable to a real jobsite in a sprint.",
                   new_x="LMARGIN", new_y="NEXT")

    out = Path("Site_Copilot_Brief.pdf").resolve()
    pdf.output(str(out))
    return out


if __name__ == "__main__":
    path = build()
    print(f"Wrote: {path}")
