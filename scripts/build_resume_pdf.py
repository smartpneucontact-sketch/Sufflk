#!/usr/bin/env python3
"""Generate Arsen's resume PDF.

Run:
    python3 scripts/build_resume_pdf.py

Output:
    Arsen_Khanguieldyan_Resume.pdf
"""

from __future__ import annotations

from pathlib import Path

from fpdf import FPDF

# Palette: deliberately conservative for ATS parseability.
INK = (15, 22, 38)
INK_SOFT = (60, 70, 90)
MUTED = (130, 140, 158)
RULE = (215, 220, 230)
ACCENT = (193, 79, 30)  # rust — only used in name + section headers

PAGE_W = 612
PAGE_H = 792
MARGIN_X = 48
MARGIN_TOP = 42
MARGIN_BOTTOM = 42
CONTENT_W = PAGE_W - 2 * MARGIN_X

FONT_DIR = "/System/Library/Fonts/Supplemental"
FONT = "Body"


# ---------- helpers ----------

def _register_fonts(pdf: FPDF) -> None:
    pdf.add_font(FONT, "", f"{FONT_DIR}/Arial.ttf")
    pdf.add_font(FONT, "B", f"{FONT_DIR}/Arial Bold.ttf")
    pdf.add_font(FONT, "I", f"{FONT_DIR}/Arial Italic.ttf")
    pdf.add_font(FONT, "BI", f"{FONT_DIR}/Arial Bold Italic.ttf")


def section(pdf: FPDF, title: str) -> None:
    pdf.ln(7)
    pdf.set_font(FONT, "B", 10)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 12, title.upper(), new_x="LMARGIN", new_y="NEXT")
    # Thin rule under the section header.
    y = pdf.get_y() + 1
    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.5)
    pdf.line(MARGIN_X, y, PAGE_W - MARGIN_X, y)
    pdf.ln(5)


def role_header(pdf: FPDF, company: str, location: str, dates: str, title: str) -> None:
    """Two-line role header: company (bold) + dates right-aligned, then italic title."""
    pdf.set_font(FONT, "B", 10.5)
    pdf.set_text_color(*INK)
    pdf.cell(CONTENT_W * 0.65, 14, company)
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(CONTENT_W * 0.35, 14, dates, align="R", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(FONT, "I", 9.5)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(CONTENT_W * 0.65, 12, f"{title}  ·  {location}", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def project_header(pdf: FPDF, name: str, year: str, links: list[tuple[str, str]]) -> None:
    pdf.set_font(FONT, "B", 10.5)
    pdf.set_text_color(*INK)
    pdf.cell(CONTENT_W * 0.65, 14, name)
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(CONTENT_W * 0.35, 14, year, align="R", new_x="LMARGIN", new_y="NEXT")

    # Links row
    pdf.set_font(FONT, "", 9)
    parts = []
    for i, (text, url) in enumerate(links):
        if i > 0:
            pdf.set_text_color(*MUTED)
            pdf.cell(pdf.get_string_width("   ·   "), 12, "   ·   ")
        pdf.set_text_color(*ACCENT)
        pdf.cell(pdf.get_string_width(text), 12, text, link=url)
        parts.append(text)
    pdf.ln(13)


def bullets(pdf: FPDF, items: list[str], size: float = 9.5, line_h: float = 12.5) -> None:
    pdf.set_font(FONT, "", size)
    for item in items:
        pdf.set_text_color(*INK)
        pdf.set_x(MARGIN_X + 10)
        pdf.cell(8, line_h, "•")
        pdf.set_x(MARGIN_X + 20)
        pdf.set_text_color(*INK_SOFT)
        pdf.multi_cell(CONTENT_W - 20, line_h, item, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


def skills_row(pdf: FPDF, label: str, items: str) -> None:
    pdf.set_font(FONT, "B", 9.5)
    pdf.set_text_color(*INK)
    pdf.cell(0, 13, label, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*INK_SOFT)
    pdf.set_x(MARGIN_X)
    pdf.multi_cell(CONTENT_W, 13, items, new_x="LMARGIN", new_y="NEXT")
    pdf.ln(1)


# ---------- build ----------

def build() -> Path:
    pdf = FPDF("portrait", "pt", "letter")
    pdf.set_margins(MARGIN_X, MARGIN_TOP, MARGIN_X)
    pdf.set_auto_page_break(True, margin=MARGIN_BOTTOM)
    _register_fonts(pdf)
    pdf.add_page()

    # ===== Header =====
    pdf.set_font(FONT, "B", 24)
    pdf.set_text_color(*ACCENT)
    pdf.cell(0, 30, "Arsen Khanguieldyan", align="C", new_x="LMARGIN", new_y="NEXT")

    pdf.set_font(FONT, "", 10)
    pdf.set_text_color(*INK_SOFT)
    contact = ("arsen.khanguieldyan@gmail.com",
               "+1 (617) 655-4650",
               "Boston, MA, USA")
    # Render contact line centered with mailto link on the email.
    sep = "   ·   "
    sep_w = pdf.get_string_width(sep)
    parts_w = [pdf.get_string_width(p) for p in contact]
    total_w = sum(parts_w) + sep_w * (len(contact) - 1)
    x = (PAGE_W - total_w) / 2
    pdf.set_x(x)
    for i, part in enumerate(contact):
        if i > 0:
            pdf.cell(sep_w, 14, sep)
        link = None
        if i == 0:
            link = f"mailto:{part}"
        pdf.set_text_color(*ACCENT if i == 0 else INK_SOFT[:3])
        pdf.cell(parts_w[i], 14, part, link=link if link else "")
        pdf.set_text_color(*INK_SOFT)
    pdf.ln(20)

    pdf.set_draw_color(*RULE)
    pdf.set_line_width(0.6)
    pdf.line(MARGIN_X, pdf.get_y(), PAGE_W - MARGIN_X, pdf.get_y())
    pdf.ln(6)

    # ===== Summary =====
    pdf.set_font(FONT, "", 10)
    pdf.set_text_color(*INK_SOFT)
    pdf.multi_cell(0, 13.5,
                   "AI engineer with 7 years shipping production AI/ML systems across autonomous robotics, "
                   "IoT, and enterprise data. Hands-on with Agentic RAG, LLM tool-use, computer vision, and "
                   "the full deploy spine (FastAPI, Docker, GitHub Actions, Terraform, AWS, Azure). Recent "
                   "focus: building and operationalizing LLM agents on AWS Bedrock-class stacks.",
                   new_x="LMARGIN", new_y="NEXT")

    # ===== Selected Projects =====
    section(pdf, "Selected Projects")
    project_header(pdf,
                   "Site Copilot — Agentic RFI & Daily Report Assistant",
                   "2026",
                   [
                       ("suffolk-construction.up.railway.app",
                        "https://suffolk-construction.up.railway.app"),
                       ("github.com/smartpneucontact-sketch/Sufflk",
                        "https://github.com/smartpneucontact-sketch/Sufflk"),
                   ])
    bullets(pdf, [
        "Designed and shipped two production-shaped LLM agents on Claude Sonnet 4.6 with Agentic RAG "
        "over a synthetic construction project corpus; tool-use loop portable to AWS Bedrock Converse "
        "with no code change.",
        "Hybrid retrieval (BM25 + dense vectors, fused via Reciprocal Rank Fusion) behind an "
        "OpenSearch-shaped VectorStore Protocol; FastAPI + Pydantic service, Docker image, GitHub "
        "Actions CI gating on a YAML eval suite.",
        "LLMOps spine: JSONL tracing (run_id, latency, tokens, cost) shaped for Databricks bronze, "
        "rolling drift detector, Terraform sketch (ECS Fargate + OpenSearch + Bedrock IAM).",
        "End-to-end RFI triage runs at ~$0.05 per call against a 27-chunk corpus, producing cited "
        "responses with urgency, multi-scenario cost/schedule impact, and EOR-escalation flag.",
    ])

    # ===== Experience =====
    section(pdf, "Professional Experience")

    role_header(pdf, "Hyperion", "Yerevan, Armenia", "Nov 2022 – Jun 2025", "Head of Engineering")
    bullets(pdf, [
        "Shipped a fully autonomous AI defense drone — acquired by strategic buyer; owned engineering "
        "across AI software, computer vision, firmware, hardware, and composites.",
        "Built edge-deployed computer vision for GPS-denied navigation at 96% accuracy and target "
        "engagement at 90% reliability under active jamming and hacking; validated across 3,000 "
        "flight-test hours.",
        "Led a multidisciplinary team (AI, CV, firmware, electronics, mechanical); trained, validated, "
        "and deployed CV models to on-device inference.",
        "Designed custom PCB in Altium for flight control and ESC; ran control-loop tuning in Simulink "
        "with hardware-in-the-loop validation.",
        "Developed a proprietary composite for structural components, reducing airframe weight while "
        "maintaining structural performance.",
    ])

    role_header(pdf, "Deloitte", "Luxembourg", "Apr 2021 – Jun 2022", "Data Analyst")
    bullets(pdf, [
        "Migrated multi-source enterprise data to a unified repository on Azure with static and dynamic "
        "metadata; exposed it via REST API to a single-page web app.",
        "Evaluated nine AutoML platforms (IaaS / PaaS / SaaS) against predefined test protocols; "
        "produced selection rationale for executive review.",
    ])

    role_header(pdf,
                "Forschungsgesellschaft Umformtechnik mbH",
                "Stuttgart, Germany",
                "May 2019 – Mar 2021",
                "Data Engineer")
    bullets(pdf, [
        "Shipped a tool-wear classifier (CNN, 82% accuracy) integrated into TRUMPF Group's "
        "next-generation punching machines; co-authored \"Data-Driven Tool Wear Classification with a "
        "Convolutional Neural Network in Punching Machines\" (Feb 2020).",
        "Built a sensor-fusion IoT pipeline for stamping presses (force, distance, sound, lubrication); "
        "developed an ML failure-prediction algorithm on Audi AG data.",
    ])

    role_header(pdf, "Audi AG", "Neckarsulm, Germany", "Apr 2018 – Dec 2018", "Software Developer")
    bullets(pdf, [
        "Built and deployed an Oracle APEX web application digitalizing die-cast tooling improvements; "
        "rolled out internationally across Audi sites.",
    ])

    # ===== Skills =====
    section(pdf, "Technical Skills")
    skills_row(pdf, "AI & ML",
               "LLMs (Claude, GPT), Agentic RAG, tool-use, prompt engineering, PyTorch, "
               "HuggingFace, YOLO, computer vision, CUDA, LLMOps")
    skills_row(pdf, "Backend & Cloud",
               "Python (expert), FastAPI, REST, C/C++, SQL · AWS (Bedrock-class), "
               "Azure (AZ-400, AZ-900, AZ-204), Docker, Kubernetes, Terraform, GitHub Actions, "
               "Databricks-shaped pipelines, ETL")
    skills_row(pdf, "Data & Retrieval",
               "Vector stores (Chroma), hybrid search (BM25 + dense, RRF), OpenSearch-shaped "
               "interfaces, Azure Data Factory")
    skills_row(pdf, "Electronics & Hardware",
               "Altium / PCB design, Arduino, sensor integration, SolidWorks, Simulink")

    # ===== Certifications =====
    section(pdf, "Certifications")
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*INK_SOFT)
    pdf.multi_cell(0, 13,
                   "AWS Cloud Practitioner  ·  TensorFlow Developer  ·  Deep Learning in Computer Vision  ·  Stochastic Processes",
                   new_x="LMARGIN", new_y="NEXT")

    # ===== Education =====
    section(pdf, "Education")
    pdf.set_font(FONT, "B", 10)
    pdf.set_text_color(*INK)
    pdf.cell(CONTENT_W * 0.7, 13, "Ecole Centrale d'Electronique  —  Paris, France")
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(CONTENT_W * 0.3, 13, "", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(CONTENT_W * 0.7, 12, "M.S. Computer Science & Engineering")
    pdf.cell(CONTENT_W * 0.3, 12, "Jun 2019", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.cell(CONTENT_W * 0.7, 12, "B.S. Mathematics & Electronics")
    pdf.cell(CONTENT_W * 0.3, 12, "Jun 2017", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(3)

    pdf.set_font(FONT, "B", 10)
    pdf.set_text_color(*INK)
    pdf.cell(CONTENT_W * 0.7, 13, "MIT Professional Education")
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(CONTENT_W * 0.3, 13, "Dec 2025 – Sep 2026", align="R", new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "I", 9.5)
    pdf.cell(0, 12, "Digital Transformation in the AI Age  (in progress)", new_x="LMARGIN", new_y="NEXT")

    # ===== Languages =====
    section(pdf, "Languages")
    pdf.set_font(FONT, "", 9.5)
    pdf.set_text_color(*INK_SOFT)
    pdf.cell(0, 13,
             "English (proficient)  ·  French (fluent)  ·  German (fluent)  ·  Armenian (native)",
             new_x="LMARGIN", new_y="NEXT")

    out = Path("Arsen_Khanguieldyan_Resume.pdf").resolve()
    pdf.output(str(out))
    return out


if __name__ == "__main__":
    path = build()
    print(f"Wrote: {path}")
