"""Run RFI eval cases and print a pass/fail report.

Usage:
    python -m evals.run_evals                       # uses real LLM if ANTHROPIC_API_KEY set
    SITE_COPILOT_USE_MOCK_LLM=1 python -m evals.run_evals   # offline / CI

Exits non-zero if any case fails any check.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import yaml

from evals.scorers import score_rfi, summarize
from site_copilot.api.deps import build_app_state


def main() -> int:
    state = build_app_state()
    cases_path = Path("evals/rfi_cases.yaml")
    cases = yaml.safe_load(cases_path.read_text())

    per_case: list[tuple[str, list, int]] = []
    total_cost = 0.0
    total_steps = 0

    for case in cases:
        cid = case["id"]
        result = state.rfi_agent.run_rfi(case["rfi"])
        total_cost += result.cost_usd
        total_steps += result.steps
        checks = score_rfi(result.parsed, result.final_text, case["expect"])
        per_case.append((cid, checks, result.steps))

        passed_marks = "".join("." if c.passed else "X" for c in checks)
        print(f"[{cid}] {passed_marks}  steps={result.steps}  cost=${result.cost_usd:.4f}")
        for c in checks:
            if not c.passed:
                print(f"    FAIL {c.name}: {c.detail}")

    summary = summarize(per_case)
    summary["total_cost_usd"] = round(total_cost, 4)
    summary["avg_steps"] = round(total_steps / max(len(cases), 1), 2)

    print("\n=== Summary ===")
    print(json.dumps(summary, indent=2))

    return 0 if summary["cases_passed"] == summary["cases"] else 1


if __name__ == "__main__":
    sys.exit(main())
