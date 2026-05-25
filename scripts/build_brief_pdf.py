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
ROW_ALT = (250, 251, 253)

# === Layout constants ===
PAGE_W = 612  # letter @ pt
PAGE_H = 792
MARGIN = 56


# ---------- Helpers ----------

class Brief(FPDF):
    def footer(self):
        self.set_y(-32)
        self.set_font("Body", size=8)
        self.set_text_color(*MUTED)
        self.set_draw_color(*BORDER)
        self.set_line_width(0.4)
        self.line(MARGIN, self.get_y(), PAGE_W - MARGIN, self.get_y())
        self.set_y(-26)
        self.cell(0, 10, "Site Copilot  ·  portfolio brief", align="L")
        self.set_y(-26)
        self.cell(0, 10, f"page {self.page_no()} of {{nb}}", align="R")


def rule(pdf: FPDF, width: float = 60, height: float = 2.5, color=ACCENT) -> None:
    pdf.set_fill_color(*color)
    pdf.rect(pdf.get_x(), pdf.get_y(), width, height, "F")
    pdf.ln(height + 14)


def h1(pdf: FPDF, text: str) -> None:
    pdf.set_font("Body", "B", 30)
    pdf.set_text_color(*INK)
    pdf.cell(0, 36, text, new_x="LMARGIN", new_y="NEXT")


def h2(pdf: FPDF, text: str) -> None:
    pdf.ln(6)
    pdf.set_font("Body", "B", 9)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 12, text.upper(), new_x="LMARGIN", new_y="NEXT")
    pdf.ln(2)


def body(pdf: FPDF, text: str, size: int = 10.5, color=INK_SOFT) -> None:
    pdf.set_font("Body", "", size)
    pdf.set_text_color(*color)
    pdf.multi_cell(0, 15, text, new_x="LMARGIN", new_y="NEXT")


def bullets(pdf: FPDF, items: list[str], size: int = 10.5) -> None:
    pdf.set_font("Body", "", size)
    pdf.set_text_color(*INK_SOFT)
    for item in items:
        x0 = pdf.get_x()
        pdf.set_x(x0 + 4)
        pdf.cell(10, 15, "•")
        pdf.set_x(x0 + 16)
        pdf.multi_cell(PAGE_W - 2 * MARGIN - 16, 15, item, new_x="LMARGIN", new_y="NEXT")


def callout(pdf: FPDF, title: str, lines: list[tuple[str, str]]) -> None:
    """Amber-bordered callout box."""
    y0 = pdf.get_y()
    height = 24 + 18 * len(lines) + 8
    pdf.set_fill_color(*ACCENT_SOFT)
    pdf.set_draw_color(*ACCENT)
    pdf.set_line_width(0.5)
    pdf.rect(MARGIN, y0, PAGE_W - 2 * MARGIN, height, "DF")

    pdf.set_xy(MARGIN + 14, y0 + 10)
    pdf.set_font("Body", "B", 9)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 12, title.upper(), new_x="LMARGIN", new_y="NEXT")
    for label, value in lines:
        pdf.set_x(MARGIN + 14)
        pdf.set_font("Body", "B", 11)
        pdf.set_text_color(*INK)
        # Two-column: label fixed width, value flexes
        pdf.cell(80, 18, label)
        pdf.set_font("Body", "", 11)
        pdf.set_text_color(*INK_SOFT)
        pdf.cell(0, 18, value, new_x="LMARGIN", new_y="NEXT")
    pdf.set_y(y0 + height + 12)


def stack_table(pdf: FPDF, rows: list[tuple[str, str]]) -> None:
    col_w = (PAGE_W - 2 * MARGIN) / 2
    row_h = 22

    # Header
    pdf.set_fill_color(*INK)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Body", "B", 9)
    pdf.cell(col_w, row_h, "  THIS DEMO", border=0, fill=True)
    pdf.cell(col_w, row_h, "  SUFFOLK PRODUCTION", new_x="LMARGIN", new_y="NEXT", border=0, fill=True)

    pdf.set_font("Body", "", 10)
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
    h = 110
    pdf.set_fill_color(255, 255, 255)
    pdf.set_draw_color(*BORDER)
    pdf.rect(MARGIN, y0, PAGE_W - 2 * MARGIN, h, "DF")
    # accent stripe
    pdf.set_fill_color(*ACCENT)
    pdf.rect(MARGIN, y0, 3, h, "F")

    pdf.set_xy(MARGIN + 16, y0 + 10)
    pdf.set_font("Body", "B", 8)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 11, label.upper(), new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(MARGIN + 16)
    pdf.set_font("Body", "B", 14)
    pdf.set_text_color(*INK)
    pdf.cell(0, 18, name, new_x="LMARGIN", new_y="NEXT")

    pdf.set_x(MARGIN + 16)
    pdf.set_font("Body", "", 10)
    pdf.set_text_color(*INK_SOFT)
    pdf.multi_cell(PAGE_W - 2 * MARGIN - 32, 14, what)
    pdf.set_x(MARGIN + 16)
    pdf.set_font("Body", "I", 9.5)
    pdf.set_text_color(*MUTED)
    pdf.multi_cell(PAGE_W - 2 * MARGIN - 32, 13, why)

    pdf.set_y(y0 + h + 10)


# ---------- Content ----------

FONT_DIR = "/System/Library/Fonts/Supplemental"
FONT_FAMILY = "Body"


def _register_fonts(pdf: FPDF) -> None:
    """Embed Arial (Unicode-capable TTF on macOS) under the name 'Body' so
    every cell() / multi_cell() / set_font() call in the rest of the script
    works unchanged. fpdf2 embeds the subset into the PDF — readers don't
    need the font installed."""
    pdf.add_font(FONT_FAMILY, style="", fname=f"{FONT_DIR}/Arial.ttf")
    pdf.add_font(FONT_FAMILY, style="B", fname=f"{FONT_DIR}/Arial Bold.ttf")
    pdf.add_font(FONT_FAMILY, style="I", fname=f"{FONT_DIR}/Arial Italic.ttf")
    pdf.add_font(FONT_FAMILY, style="BI", fname=f"{FONT_DIR}/Arial Bold Italic.ttf")


def build() -> Path:
    pdf = Brief("portrait", "pt", "letter")
    pdf.set_margins(MARGIN, MARGIN, MARGIN)
    pdf.set_auto_page_break(True, margin=72)
    pdf.alias_nb_pages()
    _register_fonts(pdf)
    pdf.add_page()

    # === Header ===
    h1(pdf, "Site Copilot")
    pdf.set_font("Body", "", 13)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(0, 18, "Agentic RFI and Daily Report assistant for construction jobsites.",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(4)
    rule(pdf, width=72)

    # Author / context line
    pdf.set_font("Body", "B", 10)
    pdf.set_text_color(*INK)
    pdf.cell(0, 14, "Arsen Khanguieldyan", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Body", "", 10)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(0, 14, "smartpneu.contact@gmail.com", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 14, "Portfolio submission for Suffolk Construction — Site AI Engineer (Boston, MA)",
             new_x="LMARGIN", new_y="NEXT")
    pdf.ln(8)

    # Live demo callout
    callout(pdf, "Try it live", [
        ("Live demo", "suffolk-construction.up.railway.app"),
        ("Source code", "github.com/smartpneucontact-sketch/Sufflk"),
        ("Model", "Anthropic Claude Sonnet 4.6 · ~$0.05 per RFI triage"),
    ])

    # === Summary ===
    h2(pdf, "Summary")
    body(pdf,
         "Site Copilot is a working portfolio demo aligned to the Suffolk Site AI Engineer role. "
         "Two production-shaped AI agents — RFI triage and Daily Construction Report drafting — "
         "run on Claude Sonnet 4.6 with Agentic RAG over a synthetic project corpus. "
         "The stack uses every component named in the JD: FastAPI, hybrid retrieval mapped 1:1 to "
         "OpenSearch, JSONL telemetry mapped to Databricks bronze, and a Terraform sketch for an "
         "AWS Bedrock deployment.")

    # === The problem ===
    h2(pdf, "The problem")
    body(pdf,
         "On a typical Suffolk-scale project, project engineers field hundreds of RFIs. Industry "
         "baseline for response is ~9.7 days. End-of-shift, a superintendent spends 30–60 minutes "
         "translating sloppy field notes into a structured Daily Construction Report. Both are "
         "high-frequency, citation-heavy, and bound by the project's own documents — the textbook "
         "shape of an Agentic RAG workflow. Suffolk's own JD names both use cases by name.")

    # === The two agents ===
    h2(pdf, "What it ships")
    agent_card(pdf, "Agent 01",
               "RFI Triage",
               "Reads an incoming RFI, retrieves relevant spec sections and similar prior RFIs from the "
               "project corpus, drafts a citation-backed response, classifies urgency, estimates rough "
               "cost and schedule impact (multiple scenarios), and flags whether escalation to the "
               "Structural Engineer of Record is required.",
               "Why it matters: compresses ~9.7-day industry baseline to ~30 seconds and ~$0.05 per RFI. "
               "Cites every claim. Refuses to over-escalate when the spec is unambiguous and prior EOR "
               "rulings are on record.")

    agent_card(pdf, "Agent 02",
               "Daily Construction Report",
               "Takes raw, fragmented end-of-shift superintendent notes and produces a structured DCR with "
               "normalized crews, areas worked, equipment, deliveries, follow-ups, and an executive summary. "
               "Risks are bucketed into a fixed taxonomy (safety, schedule, quality, weather, material, "
               "coordination) so downstream BI can aggregate.",
               "Why it matters: turns 30–60 minutes of nightly paperwork into a 30-second review. Open RFIs "
               "in the notes are auto-extracted; weather forecasts are flagged against pending work.")

    # === Page 2 ===
    pdf.add_page()

    # === Stack mapping ===
    h2(pdf, "How it maps to Suffolk's named stack")
    body(pdf,
         "Every component in this demo has a 1:1 production target. The swap from local demo to "
         "deployed AWS is mechanical, not architectural — the LLMClient interface mirrors Bedrock's "
         "Converse API, the VectorStore Protocol mirrors OpenSearch's kNN, and the trace JSONL "
         "format ingests directly into Databricks bronze with no transformation.")
    pdf.ln(4)

    stack_table(pdf, [
        ("Anthropic SDK + Claude Sonnet 4.6", "AWS Bedrock — anthropic.claude-sonnet-4-6"),
        ("BM25 (+ optional Chroma), fused via RRF", "OpenSearch hybrid (BM25 + kNN)"),
        ("FastAPI + Pydantic", "FastAPI + Pydantic"),
        ("JSONL traces on disk", "CloudWatch Logs → Databricks bronze"),
        ("Streamlit / HTML single-page UI", "Teams / SharePoint apps"),
        ("GitHub Actions CI (lint + tests + eval gate)", "Same"),
        ("infra/terraform/ sketch (ECS Fargate)", "Production Terraform / CloudFormation"),
        ("Tool-use loop in agents/base.py", "Bedrock Converse multi-tool loop"),
    ])

    # === LLMOps ===
    h2(pdf, "LLMOps story")
    body(pdf,
         "The JD calls out 'monitor latency, cost, adoption, and drift'. The demo ships all four:")
    bullets(pdf, [
        "Latency: every LLM call and tool call is wrapped in a span with elapsed_ms. "
        "p50 / p95 per agent is a one-line awk on the JSONL.",
        "Cost: per-call cost_usd computed from per-million-token pricing in llm.py. "
        "Cost per RFI is ~$0.05 at current Sonnet 4.6 pricing — at 50 RFIs/site/week, "
        "Anthropic bill is under $15/site/month.",
        "Adoption: every run carries actor_id + source_surface tags; weekly active users and "
        "auto-resolution rate are one query away.",
        "Drift: rolling window watches response length, citation count, and escalation rate "
        "for >3-sigma moves. Production target is Bedrock Evaluation or Databricks ML monitoring.",
        "Eval gate: 4 RFI cases with expected behaviors in evals/rfi_cases.yaml. CI runs them in "
        "mock-LLM mode on every PR; merges block on scorer failures.",
    ])

    # === Why this fits ===
    h2(pdf, "Why this fits the Site AI Engineer role")
    body(pdf,
         "The JD describes a 'walk-the-jobsite, ship MVP agents in days' role partnered with project "
         "AI Champions. Site Copilot is exactly the artifact that role produces: pick a workflow pain, "
         "build the agent against the project's own corpus, ship it on the central AI Studio's stack, "
         "stand up the LLMOps spine, hand off cleanly. The JD also lists 'Hands-on expertise with "
         "Claude Code' as required — this entire project was built in Claude Code with Claude as the "
         "runtime, which doubles as a credibility signal.")

    # === Honest limits ===
    h2(pdf, "What is intentionally not built")
    body(pdf,
         "This is a one-week portfolio demo, not a production deploy. The README's gap list is direct:")
    bullets(pdf, [
        "Corpus is synthetic but realistic — real specs would need OCR, table extraction, "
        "and drawing-callout linking.",
        "Terraform deploys infra but no autoscaling, alarms, or multi-account boundaries — "
        "those are stubbed in the README, not the .tf files.",
        "No Procore or OpenSpace integration yet — those are the natural next two integrations "
        "(Procore for RFI/DCR submission, OpenSpace for photo metadata feeding the DCR risk surfacing).",
        "Drift detector is the smallest thing that could plausibly trigger an alert; production "
        "needs proper distribution tests (KS, PSI) against a labeled baseline window.",
    ])

    # === Closing ===
    h2(pdf, "In one line")
    pdf.set_font("Body", "I", 11.5)
    pdf.set_text_color(*INK)
    pdf.multi_cell(0, 16,
                   "Working agentic AI on Suffolk's exact stack vocabulary, against Suffolk's exact "
                   "named use cases, shippable to a real jobsite in a sprint.",
                   new_x="LMARGIN", new_y="NEXT")

    out = Path("Site_Copilot_Brief.pdf").resolve()
    pdf.output(str(out))
    return out


if __name__ == "__main__":
    path = build()
    print(f"Wrote: {path}")
