#!/usr/bin/env python3
"""Coverage dashboard and per-company coverage matrix generator conforming to Signalpost contract."""

from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))


def analyze_envelopes(envelopes_path: Path, output_csv: Path | None = None) -> dict[str, Any]:
    lines = [line.strip() for line in envelopes_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    envelopes = [json.loads(line) for line in lines]
    total_companies = len(envelopes)

    if total_companies == 0:
        return {"total_companies": 0}

    stats = {
        "total_companies": total_companies,
        "company_details_count": 0,
        "people_count": 0,
        "locations_count": 0,
        "financial_count": 0,
        "website_count": 0,
        "jobs_count": 0,
        "activity_count": 0,
        "summary_count": 0,
        "all_categories_count": 0,
        "at_least_one_fact_count": 0,
        "total_available_facts": 0,
        "total_claims": 0,
        "availability_breakdown": {
            "available": 0,
            "not_available": 0,
            "not_applicable": 0,
            "ambiguous": 0,
            "blocked": 0,
            "failed": 0,
        },
    }

    matrix_rows = []

    for env in envelopes:
        org = env.get("organisation_number", "")
        claims = env.get("claims", [])
        claims_map = {c.get("field"): c for c in claims}
        summary_text = env.get("summary", {}).get("text", "") or ""

        # Check category availability
        has_details = any(
            claims_map.get(f, {}).get("availability") == "available"
            for f in ("legal_name", "legal_form", "registered_address", "municipality")
        )
        has_people = claims_map.get("people", {}).get("availability") == "available"
        has_locations = claims_map.get("locations", {}).get("availability") == "available"
        has_financials = any(
            claims_map.get(f, {}).get("availability") == "available"
            for f in ("annual_revenue", "operating_result", "accounting_obligation")
        )
        has_website = claims_map.get("official_website", {}).get("availability") == "available"
        has_jobs = claims_map.get("jobs", {}).get("availability") == "available"
        has_activity = claims_map.get("public_activity", {}).get("availability") == "available"
        has_summary = len(summary_text.strip()) > 30

        avail_count = sum(1 for c in claims if c.get("availability") == "available")
        for c in claims:
            avail = c.get("availability", "not_available")
            stats["availability_breakdown"][avail] = stats["availability_breakdown"].get(avail, 0) + 1
            stats["total_claims"] += 1

        stats["total_available_facts"] += avail_count
        if avail_count >= 1:
            stats["at_least_one_fact_count"] += 1
        if has_details:
            stats["company_details_count"] += 1
        if has_people:
            stats["people_count"] += 1
        if has_locations:
            stats["locations_count"] += 1
        if has_financials:
            stats["financial_count"] += 1
        if has_website:
            stats["website_count"] += 1
        if has_jobs:
            stats["jobs_count"] += 1
        if has_activity:
            stats["activity_count"] += 1
        if has_summary:
            stats["summary_count"] += 1

        is_all_cat = (has_details and has_people and has_locations and has_financials and has_website)
        if is_all_cat:
            stats["all_categories_count"] += 1

        matrix_rows.append({
            "organisation_number": org,
            "company_name": claims_map.get("legal_name", {}).get("value") or "",
            "legal_form": claims_map.get("legal_form", {}).get("value") or "",
            "available_facts": avail_count,
            "company_details": int(has_details),
            "people": int(has_people),
            "locations": int(has_locations),
            "financials": int(has_financials),
            "website": int(has_website),
            "jobs": int(has_jobs),
            "activity": int(has_activity),
            "summary": int(has_summary),
            "all_core_categories": int(is_all_cat),
        })

    if output_csv:
        output_csv.parent.mkdir(parents=True, exist_ok=True)
        with output_csv.open("w", newline="", encoding="utf-8") as f:
            fieldnames = [
                "organisation_number", "company_name", "legal_form", "available_facts",
                "company_details", "people", "locations", "financials", "website",
                "jobs", "activity", "summary", "all_core_categories",
            ]
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(matrix_rows)

    pct = lambda count: f"{(count / total_companies) * 100:.1f}%"  # noqa: E731
    stats["metrics"] = {
        "company_details_pct": pct(stats["company_details_count"]),
        "people_pct": pct(stats["people_count"]),
        "locations_pct": pct(stats["locations_count"]),
        "financials_pct": pct(stats["financial_count"]),
        "website_pct": pct(stats["website_count"]),
        "jobs_pct": pct(stats["jobs_count"]),
        "activity_pct": pct(stats["activity_count"]),
        "summary_pct": pct(stats["summary_count"]),
        "all_categories_pct": pct(stats["all_categories_count"]),
        "at_least_one_fact_pct": pct(stats["at_least_one_fact_count"]),
        "facts_per_company": f"{(stats['total_available_facts'] / total_companies):.2f}",
    }

    return stats


def main() -> None:
    parser = argparse.ArgumentParser(description="Signalpost Coverage Analytics")
    parser.add_argument("--envelopes", default="out/envelopes.jsonl", help="Path to envelopes JSONL")
    parser.add_argument("--output-csv", default="out/coverage_matrix.csv", help="Path to output CSV matrix")
    args = parser.parse_args()

    env_path = Path(args.envelopes)
    if not env_path.exists():
        print(f"Error: {env_path} does not exist.", file=sys.stderr)
        sys.exit(1)

    csv_path = Path(args.output_csv)
    stats = analyze_envelopes(env_path, csv_path)

    print("============================================================")
    print("SIGNALPOST COVERAGE DASHBOARD")
    print("============================================================")
    print(f"Total Companies Analyzed:      {stats['total_companies']}")
    print(f"Company Details Coverage:      {stats['metrics']['company_details_pct']}")
    print(f"People / Governance Coverage:  {stats['metrics']['people_pct']}")
    print(f"Locations Coverage:            {stats['metrics']['locations_pct']}")
    print(f"Financials Coverage:           {stats['metrics']['financials_pct']}")
    print(f"Verified Website Coverage:     {stats['metrics']['website_pct']}")
    print(f"Jobs / Vacancies Coverage:     {stats['metrics']['jobs_pct']}")
    print(f"Public Activity Coverage:      {stats['metrics']['activity_pct']}")
    print(f"Grounded Summary Coverage:     {stats['metrics']['summary_pct']}")
    print(f"All Core Categories Coverage:  {stats['metrics']['all_categories_pct']}")
    print(f"Companies with >= 1 Fact:      {stats['metrics']['at_least_one_fact_pct']}")
    print(f"Mean Verified Facts / Company: {stats['metrics']['facts_per_company']}")
    print("------------------------------------------------------------")
    print(f"Total Available Claims:        {stats['availability_breakdown']['available']}")
    print(f"Total Not Available Claims:    {stats['availability_breakdown']['not_available']}")
    print(f"Total Not Applicable Claims:   {stats['availability_breakdown']['not_applicable']}")
    print(f"Coverage matrix exported to:   {csv_path}")
    print("============================================================")


if __name__ == "__main__":
    main()
