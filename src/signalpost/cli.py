"""Production Command Line Interface for Signalpost Agent."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from signalpost.config import settings
from signalpost.fetching.budget import RequestBudget
from signalpost.fetching.cache import ResponseCache
from signalpost.fetching.client import SafeHttpClient, utc_now
from signalpost.identity.resolver import assess_website_identity
from signalpost.result_contract import build_output_envelope, validate_contract_envelope
from signalpost.synthesis.summary import generate_company_summary


def research_single_company(org_number: str, budget: RequestBudget | None = None) -> dict:
    """Execute end-to-end research on a single Norwegian organisation number."""
    start_time = time.monotonic()
    started_at = utc_now()
    budget = budget or RequestBudget()
    cache = ResponseCache()
    client = SafeHttpClient(budget=budget, cache=cache)

    org_clean = "".join(c for c in str(org_number) if c.isdigit())
    if len(org_clean) != 9:
        raise ValueError(f"Invalid Norwegian organisation number: {org_number}")

    # 1. Fetch Authoritative Brreg Record
    brreg_url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{org_clean}"
    reg_resp = client.get(brreg_url)

    profile: dict = {
        "organisation_number": org_clean,
        "name": None,
        "legal_form": None,
        "employees": None,
        "municipality": None,
        "website": None,
        "latest_submitted_accounts": None,
        "evidence": {},
    }

    if reg_resp.status_code == 200:
        data = reg_resp.json()
        profile["name"] = data.get("navn")
        profile["legal_form"] = (data.get("organisasjonsform") or {}).get("kode")
        profile["employees"] = data.get("antallAnsatte")
        profile["municipality"] = (data.get("forretningsadresse") or {}).get("kommune")
        profile["website"] = data.get("hjemmeside")
        profile["latest_submitted_accounts"] = data.get("sisteInnsendteAarsregnskap")

        profile["evidence"]["registry_live"] = {
            "status": "available",
            "source_url": brreg_url,
            "source_class": "official_registry",
            "retrieved_at": reg_resp.retrieved_at,
            "content_sha256": reg_resp.content_sha256,
            "value": data,
        }
    else:
        profile["evidence"]["registry_live"] = {
            "status": "not_found" if reg_resp.status_code == 404 else "source_error",
            "source_url": brreg_url,
            "source_class": "official_registry",
            "retrieved_at": reg_resp.retrieved_at,
            "content_sha256": reg_resp.content_sha256,
            "note": reg_resp.error or f"HTTP {reg_resp.status_code}",
        }

    # 2. Fetch Official Financials
    fin_url = f"https://data.brreg.no/regnskapsregisteret/regnskap/{org_clean}"
    fin_resp = client.get(fin_url)
    if fin_resp.status_code == 200:
        fin_data = fin_resp.json()
        from signalpost.extraction.financials import normalize_financial_statement
        records = [normalize_financial_statement(rec) for rec in (fin_data if isinstance(fin_data, list) else [fin_data])[:3]]
        profile["evidence"]["financials"] = {
            "status": "available",
            "source_url": fin_url,
            "source_class": "official_annual_accounts",
            "retrieved_at": fin_resp.retrieved_at,
            "content_sha256": fin_resp.content_sha256,
            "value": {"records": records},
        }
    else:
        profile["evidence"]["financials"] = {
            "status": "not_found" if fin_resp.status_code in {404, 410} else "source_error",
            "source_url": fin_url,
            "source_class": "official_annual_accounts",
            "retrieved_at": fin_resp.retrieved_at,
            "content_sha256": fin_resp.content_sha256,
            "note": fin_resp.error or f"HTTP {fin_resp.status_code}",
        }

    # 3. Fetch Registered Website if present
    website_url = profile.get("website")
    if website_url:
        if not website_url.startswith("http"):
            website_url = "https://" + website_url
        web_resp = client.get(website_url)
        if web_resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(web_resp.text, "html.parser")
            title = soup.title.string.strip() if soup.title and soup.title.string else ""
            desc_tag = soup.find("meta", attrs={"name": "description"})
            description = desc_tag["content"].strip() if desc_tag and desc_tag.get("content") else ""
            body_text = soup.get_text(" ", strip=True)[:1500]

            assessment = assess_website_identity(
                company_name=profile["name"] or "",
                target_org_number=org_clean,
                page_data={"title": title, "description": description, "text": body_text},
            )

            profile["evidence"]["website"] = {
                "status": "available" if assessment["publishable"] else "ambiguous",
                "source_url": website_url,
                "source_class": "company_owned",
                "retrieved_at": web_resp.retrieved_at,
                "content_sha256": web_resp.content_sha256,
                "value": {
                    "title": title,
                    "description": description,
                    "identity_assessment": assessment,
                },
            }
        else:
            profile["evidence"]["website"] = {
                "status": "source_error",
                "source_url": website_url,
                "source_class": "company_owned",
                "retrieved_at": web_resp.retrieved_at,
                "content_sha256": web_resp.content_sha256,
                "note": web_resp.error or f"HTTP {web_resp.status_code}",
            }

    completed_at = utc_now()
    runtime_ms = int((time.monotonic() - start_time) * 1000)
    summary_text = generate_company_summary(profile)
    profile["summary"] = summary_text

    budget_stats = budget.summary()
    envelope = build_output_envelope(
        profile=profile,
        run_id="run-local-001",
        started_at=started_at,
        completed_at=completed_at,
        requests_count=budget_stats["total_outbound_requests"],
        runtime_ms=runtime_ms,
        cost_usd=budget_stats["cost_spent_usd"],
    )

    return envelope


def main() -> None:
    parser = argparse.ArgumentParser(description="Signalpost Company Intelligence Agent CLI")
    subparsers = parser.add_subparsers(dest="command", help="Sub-commands")

    # Research Single Company
    research_parser = subparsers.add_parser("research", help="Research a single Norwegian organisation number")
    research_parser.add_argument("--org-number", required=True, help="9-digit Norwegian organisation number")
    research_parser.add_argument("--output", help="Optional output JSON file")

    args = parser.parse_args()

    if args.command == "research":
        envelope = research_single_company(args.org_number)
        val_errors = validate_contract_envelope(envelope)
        if val_errors:
            print(f"Validation warnings: {val_errors}", file=sys.stderr)

        json_out = json.dumps(envelope, indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(json_out + "\n", encoding="utf-8")
            print(f"Wrote terminal envelope to {args.output}")
        else:
            print(json_out)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
