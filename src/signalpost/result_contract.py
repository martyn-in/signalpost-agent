"""Output envelope builder and validator conforming to OUTPUT_CONTRACT.md."""

from __future__ import annotations

import datetime
from typing import Any

VALID_AVAILABILITIES = {
    "available",
    "not_available",
    "blocked",
    "not_applicable",
    "ambiguous",
    "failed",
}


def build_output_envelope(
    profile: dict[str, Any],
    run_id: str,
    started_at: str,
    completed_at: str,
    requests_count: int = 0,
    runtime_ms: int = 0,
    cost_usd: float = 0.0,
    changes: list[dict[str, Any]] | None = None,
    errors: list[str] | None = None,
) -> dict[str, Any]:
    """Build standardized terminal output envelope conforming strictly to Builderr's contract."""
    org_number = profile.get("organisation_number")
    evidence_items: list[dict[str, Any]] = []
    claim_items: list[dict[str, Any]] = []
    ev_counter = 0

    # 1. Official Registry Claims
    reg_evidence = profile.get("evidence", {}).get("registry_live") or profile.get("evidence", {}).get("registry") or {}
    reg_status = reg_evidence.get("status")
    reg_val = reg_evidence.get("value") or {}

    ev_id = f"ev-{org_number}-{ev_counter}"
    ev_counter += 1
    evidence_items.append({
        "id": ev_id,
        "source_url": reg_evidence.get("source_url") or f"https://data.brreg.no/enhetsregisteret/api/enheter/{org_number}",
        "source_class": reg_evidence.get("source_class") or "official_registry",
        "retrieved_at": reg_evidence.get("retrieved_at") or completed_at,
        "content_sha256": reg_evidence.get("content_sha256") or ("0" * 64),
        "claim_span": f"{profile.get('name', '')}, {org_number}",
    })

    # Legal Name
    claim_items.append({
        "field": "legal_name",
        "value": profile.get("name") or reg_val.get("name"),
        "availability": "available" if profile.get("name") else "not_available",
        "confidence": 1.0,
        "evidence_ids": [ev_id],
    })

    # Legal Form
    claim_items.append({
        "field": "legal_form",
        "value": profile.get("legal_form") or reg_val.get("legal_form"),
        "availability": "available" if profile.get("legal_form") else "not_available",
        "confidence": 1.0,
        "evidence_ids": [ev_id],
    })

    # Employees
    emp_val = profile.get("employees") if profile.get("employees") is not None else reg_val.get("employees")
    claim_items.append({
        "field": "employees",
        "value": emp_val,
        "availability": "available" if emp_val is not None else "not_available",
        "confidence": 1.0,
        "evidence_ids": [ev_id] if emp_val is not None else [],
    })

    # Municipality / Location
    muni_val = profile.get("municipality") or reg_val.get("municipality")
    if muni_val:
        claim_items.append({
            "field": "municipality",
            "value": muni_val,
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": [ev_id],
        })

    # 2. Financial Accounts
    fin_evidence = profile.get("evidence", {}).get("financials", {})
    fin_status = fin_evidence.get("status")
    fin_val = fin_evidence.get("value") or {}
    fin_records = fin_val.get("records") or []

    if fin_records:
        fin_ev_id = f"ev-{org_number}-{ev_counter}"
        ev_counter += 1
        evidence_items.append({
            "id": fin_ev_id,
            "source_url": fin_evidence.get("source_url") or f"https://data.brreg.no/regnskapsregisteret/regnskap/{org_number}",
            "source_class": "official_annual_accounts",
            "retrieved_at": fin_evidence.get("retrieved_at") or completed_at,
            "content_sha256": fin_evidence.get("content_sha256") or ("0" * 64),
            "claim_span": f"Annual accounts filed for {fin_records[0].get('reporting_period', '2025')}",
        })
        claim_items.append({
            "field": "annual_revenue",
            "value": fin_records[0].get("revenue"),
            "availability": "available" if fin_records[0].get("revenue") is not None else "not_available",
            "confidence": 1.0,
            "evidence_ids": [fin_ev_id] if fin_records[0].get("revenue") is not None else [],
        })
        claim_items.append({
            "field": "operating_result",
            "value": fin_records[0].get("operating_result"),
            "availability": "available" if fin_records[0].get("operating_result") is not None else "not_available",
            "confidence": 1.0,
            "evidence_ids": [fin_ev_id] if fin_records[0].get("operating_result") is not None else [],
        })
    else:
        claim_items.append({
            "field": "annual_revenue",
            "value": None,
            "availability": "not_applicable" if profile.get("legal_form") in {"ENK", "FLI"} else "not_available",
            "confidence": 1.0,
            "evidence_ids": [],
        })

    # 3. Official Website
    web_evidence = profile.get("evidence", {}).get("website", {})
    web_val = web_evidence.get("value") or {}
    website_url = profile.get("website") or web_evidence.get("source_url")

    if website_url and web_evidence.get("status") == "available":
        web_ev_id = f"ev-{org_number}-{ev_counter}"
        ev_counter += 1
        evidence_items.append({
            "id": web_ev_id,
            "source_url": website_url,
            "source_class": "company_owned",
            "retrieved_at": web_evidence.get("retrieved_at") or completed_at,
            "content_sha256": web_evidence.get("content_sha256") or ("0" * 64),
            "claim_span": web_val.get("title") or f"Official site for {profile.get('name')}",
        })
        claim_items.append({
            "field": "official_website",
            "value": website_url,
            "availability": "available",
            "confidence": 0.95,
            "evidence_ids": [web_ev_id],
        })
    elif website_url and web_evidence.get("status") == "source_error":
        claim_items.append({
            "field": "official_website",
            "value": website_url,
            "availability": "failed",
            "confidence": 0.5,
            "evidence_ids": [],
        })
    elif website_url:
        # Website registered in official registry record
        claim_items.append({
            "field": "official_website",
            "value": website_url,
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": [ev_id],
        })
    else:
        claim_items.append({
            "field": "official_website",
            "value": None,
            "availability": "not_available",
            "confidence": 1.0,
            "evidence_ids": [],
        })


    return {
        "organisation_number": str(org_number),
        "run": {
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "terminal_status": "completed",
        },
        "claims": claim_items,
        "evidence": evidence_items,
        "changes": changes or [],
        "errors": errors or [],
        "operations": {
            "requests": requests_count,
            "runtime_ms": runtime_ms,
            "third_party_cost_usd": cost_usd,
        },
    }


def validate_contract_envelope(envelope: dict[str, Any]) -> list[str]:
    """Validate a terminal result envelope against OUTPUT_CONTRACT.md rules."""
    errors: list[str] = []

    if not isinstance(envelope, dict):
        return ["Envelope must be a JSON object"]

    org = envelope.get("organisation_number")
    if not org or len(str(org)) != 9 or not str(org).isdigit():
        errors.append(f"Invalid organisation_number: {org!r}")

    run = envelope.get("run")
    if not isinstance(run, dict) or not run.get("run_id") or not run.get("started_at") or not run.get("completed_at"):
        errors.append("Envelope missing valid 'run' section")

    claims = envelope.get("claims")
    if not isinstance(claims, list):
        errors.append("Envelope 'claims' must be a list")
    else:
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                errors.append(f"Claim #{index} is not an object")
                continue
            if not claim.get("field"):
                errors.append(f"Claim #{index} missing 'field'")
            avail = claim.get("availability")
            if avail not in VALID_AVAILABILITIES:
                errors.append(f"Claim #{index} has invalid availability: {avail!r}")

    evidence = envelope.get("evidence")
    if not isinstance(evidence, list):
        errors.append("Envelope 'evidence' must be a list")
    else:
        for index, ev in enumerate(evidence):
            if not isinstance(ev, dict):
                errors.append(f"Evidence #{index} is not an object")
                continue
            if not ev.get("id") or not ev.get("source_url") or not ev.get("retrieved_at"):
                errors.append(f"Evidence #{index} missing required fields (id, source_url, retrieved_at)")

    ops = envelope.get("operations")
    if not isinstance(ops, dict) or "requests" not in ops or "runtime_ms" not in ops:
        errors.append("Envelope missing valid 'operations' section")

    return errors
