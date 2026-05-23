from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class CheckResult:
    name: str
    passed: bool
    detail: str = ""


def _cited_source_types(parsed: dict[str, Any]) -> set[str]:
    out: set[str] = set()
    for c in (parsed.get("citations") or []):
        src = (c.get("source") or "")
        if ":" in src:
            out.add(src.split(":", 1)[0])
    return out


def score_rfi(result_parsed: dict[str, Any] | None, raw_text: str, expect: dict[str, Any]) -> list[CheckResult]:
    checks: list[CheckResult] = []

    if result_parsed is None:
        checks.append(CheckResult("parsed_json", False, "agent did not return valid JSON"))
        return checks
    checks.append(CheckResult("parsed_json", True))

    cited = _cited_source_types(result_parsed)

    if "must_cite_source_type" in expect:
        want = expect["must_cite_source_type"]
        ok = want in cited
        checks.append(CheckResult(f"cites_{want}", ok, f"cited: {sorted(cited)}"))

    if "must_cite_source_type_any" in expect:
        want_any = expect["must_cite_source_type_any"]
        ok = bool(set(want_any) & cited)
        checks.append(CheckResult(f"cites_any_of_{want_any}", ok, f"cited: {sorted(cited)}"))

    if "urgency_in" in expect:
        urg = result_parsed.get("urgency")
        ok = urg in expect["urgency_in"]
        checks.append(CheckResult(f"urgency_in_{expect['urgency_in']}", ok, f"got: {urg}"))

    if "needs_eor_review" in expect:
        ok = bool(result_parsed.get("needs_eor_review")) == bool(expect["needs_eor_review"])
        checks.append(
            CheckResult(
                f"eor_review=={expect['needs_eor_review']}",
                ok,
                f"got: {result_parsed.get('needs_eor_review')}",
            )
        )

    if "response_keywords_any" in expect:
        body = (result_parsed.get("draft_response") or "") + " " + raw_text
        lowered = body.lower()
        hit = next((kw for kw in expect["response_keywords_any"] if kw.lower() in lowered), None)
        checks.append(
            CheckResult(
                "response_keyword_present",
                hit is not None,
                f"matched: {hit}" if hit else f"none of {expect['response_keywords_any']}",
            )
        )

    return checks


def summarize(per_case: list[tuple[str, list[CheckResult], int]]) -> dict[str, Any]:
    total_checks = sum(len(c) for _, c, _ in per_case)
    passed = sum(1 for _, c, _ in per_case for ck in c if ck.passed)
    case_pass = sum(1 for _, c, _ in per_case if all(ck.passed for ck in c))
    return {
        "cases": len(per_case),
        "cases_passed": case_pass,
        "checks_total": total_checks,
        "checks_passed": passed,
        "checks_pass_rate": round(passed / max(total_checks, 1), 3),
    }
