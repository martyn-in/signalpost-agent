#!/usr/bin/env python3
"""Signalpost Failure-Driven Optimization and Diagnostic Tool.

Analyzes terminal envelopes from any evaluation or benchmark run:
- Clusters and ranks reasons points are lost across all field families
- Quantifies score impact per failure mode (NO_VERIFIED_WEBSITE, NO_PEOPLE, NO_FINANCIALS, NO_JOBS, etc.)
- Emits structured JSON diagnostics and Markdown analytics
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import Any

RUBRIC_FIELD_WEIGHTS = {
    "official_identity": {
        "fields": ["legal_name", "legal_form", "registered_address", "municipality"],
        "max_points": 10.0,
    },
    "workforce_and_locations": {
        "fields": ["employees", "locations"],
        "max_points": 8.0,
    },
    "financials": {
        "fields": ["annual_revenue", "operating_result", "accounting_obligation"],
        "max_points": 12.0,
    },
    "digital_and_governance": {
        "fields": ["official_website", "people", "jobs"],
        "max_points": 15.0,
    },
    "external_signals": {
        "fields": ["public_activity", "ratings_and_reviews"],
        "max_points": 10.0,
    },
}


def read_jsonl(path: Path | str) -> list[dict[str, Any]]:
    return [json.loads(line) for line in Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def analyze_envelopes(envelopes: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(envelopes)
    if n == 0:
        return {"error": "Empty envelope list"}

    field_counts: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    evidence_counts = []
    requests_counts = []
    runtimes_ms = []

    for env in envelopes:
        ops = env.get("operations") or {}
        requests_counts.append(ops.get("requests", 0))
        runtimes_ms.append(ops.get("runtime_ms", 0))
        evidence_counts.append(len(env.get("evidence", [])))

        for claim in env.get("claims", []):
            field = claim.get("field", "unknown")
            avail = claim.get("availability", "unknown")
            field_counts[field][avail] += 1

    # Aggregate statistics
    field_summary = {}
    failure_clusters = collections.Counter()

    for field, counts in sorted(field_counts.items()):
        avail = counts.get("available", 0)
        not_avail = counts.get("not_available", 0)
        not_app = counts.get("not_applicable", 0)
        blocked = counts.get("blocked", 0)
        ambig = counts.get("ambiguous", 0)
        failed = counts.get("failed", 0)

        rate = avail / n
        field_summary[field] = {
            "available": avail,
            "available_rate": round(rate, 4),
            "not_available": not_avail,
            "not_applicable": not_app,
            "blocked": blocked,
            "ambiguous": ambig,
            "failed": failed,
        }

        # Cluster failures
        if field == "official_website" and (not_avail + blocked + ambig + failed) > 0:
            failure_clusters["NO_VERIFIED_WEBSITE"] += (not_avail + blocked + ambig + failed)
        elif field == "people" and not_avail > 0:
            failure_clusters["NO_PEOPLE"] += not_avail
        elif field in {"annual_revenue", "operating_result"} and not_avail > 0:
            failure_clusters["NO_FINANCIALS"] += not_avail
        elif field == "jobs" and not_avail > 0:
            failure_clusters["NO_JOBS"] += not_avail
        elif field == "locations" and not_avail > 0:
            failure_clusters["NO_LOCATIONS"] += not_avail

        if blocked > 0:
            failure_clusters["SOURCE_BLOCKED"] += blocked
        if failed > 0:
            failure_clusters["PARSER_OR_SOURCE_FAILED"] += failed
        if ambig > 0:
            failure_clusters["IDENTITY_AMBIGUOUS"] += ambig

    # Ranked failure breakdown
    ranked_failures = [
        {
            "failure_code": code,
            "occurrences": count,
            "affected_rate": round(count / (n * (2 if code == "NO_FINANCIALS" else 1)), 4),
            "potential_score_impact": round(count / n * 5.0, 2),
        }
        for code, count in failure_clusters.most_common()
    ]

    sorted_lats = sorted(runtimes_ms)
    p50_runtime = sorted_lats[len(sorted_lats) // 2] if sorted_lats else 0
    p95_runtime = sorted_lats[min(len(sorted_lats) - 1, int(len(sorted_lats) * 0.95))] if sorted_lats else 0

    return {
        "envelopes_analyzed": n,
        "average_evidence_per_company": round(sum(evidence_counts) / n, 2),
        "total_requests": sum(requests_counts),
        "average_requests_per_company": round(sum(requests_counts) / n, 2),
        "p50_runtime_ms": p50_runtime,
        "p95_runtime_ms": p95_runtime,
        "field_availability_summary": field_summary,
        "ranked_failure_reasons": ranked_failures,
    }


def format_markdown_report(analysis: dict[str, Any], title: str = "Signalpost Diagnostic Report") -> str:
    n = analysis["envelopes_analyzed"]
    lines = [
        f"# {title}",
        "",
        f"**Companies Analyzed:** {n:,} | **Avg Requests/Company:** {analysis['average_requests_per_company']} | **Avg Evidence Items:** {analysis['average_evidence_per_company']}",
        "",
        "## 1. Ranked Point Loss Causes (Failure Clustering)",
        "",
        "| Rank | Failure Reason Code | Occurrences | Rate Across Batch | Estimated Point Impact | Priority |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ]

    for idx, item in enumerate(analysis["ranked_failure_reasons"], 1):
        code = item["failure_code"]
        occs = item["occurrences"]
        rate = item["affected_rate"]
        impact = item["potential_score_impact"]
        priority = "P0 (Critical)" if idx <= 2 else "P1 (High)" if idx <= 4 else "P2 (Medium)"
        lines.append(f"| {idx} | **`{code}`** | {occs:,} | {rate:.1%} | ~{impact:.1f} pts | {priority} |")

    lines.extend([
        "",
        "## 2. Field-by-Field Recall & Availability",
        "",
        "| Field Family | Available | Not Available | Not Applicable | Failed / Blocked / Ambiguous | Availability Recall |",
        "| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    for field, stats in analysis["field_availability_summary"].items():
        avail = stats["available"]
        not_avail = stats["not_available"]
        not_app = stats["not_applicable"]
        issues = stats["failed"] + stats["blocked"] + stats["ambiguous"]
        rate = stats["available_rate"]
        lines.append(f"| `{field}` | **{avail}** | {not_avail} | {not_app} | {issues} | **{rate:.1%}** |")

    lines.extend([
        "",
        "## 3. High-Leverage Strategic Action Items",
        "",
    ])

    for idx, item in enumerate(analysis["ranked_failure_reasons"][:4], 1):
        code = item["failure_code"]
        if code == "NO_VERIFIED_WEBSITE":
            lines.append(f"{idx}. **Attack `{code}`**: Activate search discovery (Brave/Google) and social cross-link back-propagation to lift website discovery beyond the ~11% Brreg default.")
        elif code == "NO_FINANCIALS":
            lines.append(f"{idx}. **Attack `{code}`**: Query live Regnskapsregisteret accounts API or extract from annual account copies for companies with filed accounts.")
        elif code == "NO_PEOPLE":
            lines.append(f"{idx}. **Attack `{code}`**: Query live Roller API or parse website management subpages (`/ledelse`, `/om-oss`) for leadership names.")
        elif code == "NO_JOBS":
            lines.append(f"{idx}. **Attack `{code}`**: Crawl careers subpages (`/karriere`, `/jobb`) and parse schema.org JobPosting structured data.")
        elif code == "NO_LOCATIONS":
            lines.append(f"{idx}. **Attack `{code}`**: Query Underenheter API and parse physical branch locations from contact pages.")

    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Signalpost failure diagnosis and point-loss ranking")
    parser.add_argument("--envelopes", required=True, help="Input terminal envelopes JSONL")
    parser.add_argument("--output", help="Optional JSON output path")
    parser.add_argument("--markdown", help="Optional Markdown output path")
    parser.add_argument("--title", default="Signalpost Failure-Driven Diagnostic Report")
    args = parser.parse_args()

    envelopes = read_jsonl(args.envelopes)
    analysis = analyze_envelopes(envelopes)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(json.dumps(analysis, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"Wrote diagnostic JSON to {args.output}")

    md_report = format_markdown_report(analysis, title=args.title)
    if args.markdown:
        Path(args.markdown).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown).write_text(md_report, encoding="utf-8")
        print(f"Wrote diagnostic Markdown report to {args.markdown}")
    else:
        print(md_report)


if __name__ == "__main__":
    main()
