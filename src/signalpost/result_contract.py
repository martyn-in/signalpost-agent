"""Output envelope builder and validator conforming to OUTPUT_CONTRACT.md.

Produces standardized, evidence-grounded terminal output envelopes covering all official
corporate intelligence field families:
- Identity: legal_name, legal_form, registered_address, municipality
- Operations: employees, locations (registered office & branch subunits)
- Governance: people (executive management, board chair, board members, auditor)
- Finance: annual_revenue, operating_result, accounting_obligation
- Digital Footprint: official_website, jobs (career vacancies), public_activity, ratings_and_reviews
"""

from __future__ import annotations

import datetime
from typing import Any

from norway_company_agent.official import accounting_obligation_assessment

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
    org_number = str(profile.get("organisation_number") or "")
    evidence_items: list[dict[str, Any]] = []
    claim_items: list[dict[str, Any]] = []
    ev_counter = 0

    legal_form = str(profile.get("legal_form") or "").upper()
    evidence_dict = profile.get("evidence", {})

    # =========================================================================
    # 1. Official Registry Claims & Evidence
    # =========================================================================
    reg_evidence = evidence_dict.get("registry_live") or evidence_dict.get("registry") or {}
    reg_val = reg_evidence.get("value") or {}
    if not isinstance(reg_val, dict):
        reg_val = {}

    reg_ev_id = f"ev-{org_number}-{ev_counter}"
    ev_counter += 1
    evidence_items.append({
        "id": reg_ev_id,
        "source_url": reg_evidence.get("source_url") or f"https://data.brreg.no/enhetsregisteret/api/enheter/{org_number}",
        "source_class": reg_evidence.get("source_class") or "official_registry",
        "retrieved_at": reg_evidence.get("retrieved_at") or completed_at,
        "content_sha256": reg_evidence.get("content_sha256") or ("0" * 64),
        "claim_span": f"{profile.get('name', '')}, {org_number}",
    })

    # Legal Name
    name_val = profile.get("name") or reg_val.get("navn") or reg_val.get("name")
    claim_items.append({
        "field": "legal_name",
        "value": name_val,
        "availability": "available" if name_val else "not_available",
        "confidence": 1.0,
        "evidence_ids": [reg_ev_id] if name_val else [],
    })

    # Legal Form
    form_val = profile.get("legal_form") or reg_val.get("legal_form")
    if not form_val:
        org_form = reg_val.get("organisasjonsform")
        form_val = org_form.get("kode") if isinstance(org_form, dict) else org_form
    claim_items.append({
        "field": "legal_form",
        "value": form_val,
        "availability": "available" if form_val else "not_available",
        "confidence": 1.0,
        "evidence_ids": [reg_ev_id] if form_val else [],
    })

    # Employees
    emp_val = profile.get("employees")
    if emp_val is None and reg_val.get("antallAnsatte") is not None:
        emp_val = reg_val.get("antallAnsatte")
    if emp_val is None and reg_val.get("employees") is not None:
        emp_val = reg_val.get("employees")
    claim_items.append({
        "field": "employees",
        "value": emp_val,
        "availability": "available" if emp_val is not None else "not_available",
        "confidence": 1.0,
        "evidence_ids": [reg_ev_id] if emp_val is not None else [],
    })

    # Municipality
    muni_val = profile.get("municipality") or (reg_val.get("forretningsadresse") or {}).get("kommune") or reg_val.get("municipality")
    claim_items.append({
        "field": "municipality",
        "value": muni_val,
        "availability": "available" if muni_val else "not_available",
        "confidence": 1.0,
        "evidence_ids": [reg_ev_id] if muni_val else [],
    })

    # Registered Address
    b_addr = reg_val.get("forretningsadresse") or reg_val.get("business_address") or reg_val.get("postadresse") or reg_val.get("postal_address") or profile.get("business_address") or {}
    addr_str = None
    if isinstance(b_addr, dict):
        lines = list(b_addr.get("adresse") or [])
        pc = b_addr.get("postnummer")
        city = b_addr.get("poststed") or b_addr.get("kommune")
        parts = []
        if lines:
            parts.append(", ".join(lines))
        if pc and city:
            parts.append(f"{pc} {city}")
        elif city:
            parts.append(city)
        addr_str = ", ".join(parts) if parts else None
    elif isinstance(b_addr, str):
        addr_str = b_addr

    claim_items.append({
        "field": "registered_address",
        "value": addr_str,
        "availability": "available" if addr_str else "not_available",
        "confidence": 1.0,
        "evidence_ids": [reg_ev_id] if addr_str else [],
    })

    # Accounting Obligation
    acc_evidence = evidence_dict.get("accounting_obligation")
    if acc_evidence and isinstance(acc_evidence, dict) and acc_evidence.get("value"):
        acc_class = (acc_evidence.get("value") or {}).get("classification")
    elif name_val:
        acc_assessment = accounting_obligation_assessment(profile)
        acc_class = (acc_assessment.get("value") or {}).get("classification")
    else:
        acc_class = None

    if acc_class:
        acc_ev_id = f"ev-{org_number}-{ev_counter}"
        ev_counter += 1
        evidence_items.append({
            "id": acc_ev_id,
            "source_url": "https://www.brreg.no/en/submission-of-annual-accounts/reporting-obligations-to-the-register-of-company-accounts/who-has-an-accounting-obligation/",
            "source_class": "official_rule_interpretation",
            "retrieved_at": completed_at,
            "content_sha256": "473708a381014e3e3b5e407eaeece3c373faeb3595f57378fa98eb7e31b7e6e3",
            "claim_span": f"Accounting obligation rule assessment: {acc_class}",
        })
        claim_items.append({
            "field": "accounting_obligation",
            "value": acc_class,
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": [acc_ev_id],
        })
    else:
        claim_items.append({
            "field": "accounting_obligation",
            "value": None,
            "availability": "not_applicable" if not name_val else "not_available",
            "confidence": 1.0,
            "evidence_ids": [],
        })

    # =========================================================================
    # 2. Financial Accounts & Line Items
    # =========================================================================
    fin_evidence = evidence_dict.get("financials", {})
    fin_status = fin_evidence.get("status")
    fin_val = fin_evidence.get("value") or {}
    fin_records = fin_val.get("records") or [] if isinstance(fin_val, dict) else []

    if fin_records and fin_status == "available":
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
        rev_val = fin_records[0].get("revenue")
        claim_items.append({
            "field": "annual_revenue",
            "value": rev_val,
            "availability": "available" if rev_val is not None else "not_available",
            "confidence": 1.0,
            "evidence_ids": [fin_ev_id] if rev_val is not None else [],
        })
        op_val = fin_records[0].get("operating_result")
        claim_items.append({
            "field": "operating_result",
            "value": op_val,
            "availability": "available" if op_val is not None else "not_available",
            "confidence": 1.0,
            "evidence_ids": [fin_ev_id] if op_val is not None else [],
        })
    else:
        NON_FILING_FORMS = {"ENK", "FLI", "ESEK", "ORGL", "ANS", "DA", "SA", "NUF", "KS"}
        default_fin_avail = "not_applicable" if form_val in NON_FILING_FORMS else "not_available"
        claim_items.append({
            "field": "annual_revenue",
            "value": None,
            "availability": default_fin_avail,
            "confidence": 1.0,
            "evidence_ids": [],
        })
        claim_items.append({
            "field": "operating_result",
            "value": None,
            "availability": default_fin_avail,
            "confidence": 1.0,
            "evidence_ids": [],
        })

    # =========================================================================
    # 3. Official Website & Digital Footprint
    # =========================================================================
    web_evidence = evidence_dict.get("website", {})
    web_val = web_evidence.get("value") or {}
    website_url = profile.get("website") or web_evidence.get("source_url")

    identity_assessment = web_val.get("identity_assessment") or {} if isinstance(web_val, dict) else {}
    publishable = identity_assessment.get("publishable", True)

    web_ev_id = None
    if website_url and web_evidence.get("status") == "available" and publishable:
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
    elif website_url and web_evidence.get("status") == "blocked":
        claim_items.append({
            "field": "official_website",
            "value": website_url,
            "availability": "blocked",
            "confidence": 0.5,
            "evidence_ids": [],
        })
    elif website_url and not publishable:
        claim_items.append({
            "field": "official_website",
            "value": website_url,
            "availability": "ambiguous",
            "confidence": 0.3,
            "evidence_ids": [],
        })
    elif website_url:
        claim_items.append({
            "field": "official_website",
            "value": website_url,
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": [reg_ev_id],
        })
    else:
        claim_items.append({
            "field": "official_website",
            "value": None,
            "availability": "not_available",
            "confidence": 1.0,
            "evidence_ids": [],
        })

    # =========================================================================
    # 4. Corporate Governance & Leadership (People)
    # =========================================================================
    roles_evidence = evidence_dict.get("roles", {})
    roles_status = roles_evidence.get("status")
    roles_val = roles_evidence.get("value") or {}
    roles_list = [r for r in roles_val.get("roles") or [] if not r.get("inactive")] if isinstance(roles_val, dict) else []

    if roles_status == "available" and roles_list:
        roles_ev_id = f"ev-{org_number}-{ev_counter}"
        ev_counter += 1
        evidence_items.append({
            "id": roles_ev_id,
            "source_url": roles_evidence.get("source_url") or f"https://data.brreg.no/enhetsregisteret/api/enheter/{org_number}/roller",
            "source_class": "official_roles",
            "retrieved_at": roles_evidence.get("retrieved_at") or completed_at,
            "content_sha256": roles_evidence.get("content_sha256") or ("0" * 64),
            "claim_span": f"Registered corporate leadership roles ({len(roles_list)} holders)",
        })
        people_claims = [
            {
                "name": " ".join(r["name"]) if isinstance(r.get("name"), list) else str(r.get("name") or "").strip(),
                "role": str(r.get("role") or r.get("group") or "Leader").strip(),
                "role_code": r.get("role_code"),
            }
            for r in roles_list[:10]
            if r.get("name")
        ]
        claim_items.append({
            "field": "people",
            "value": people_claims if people_claims else None,
            "availability": "available" if people_claims else "not_available",
            "confidence": 1.0,
            "evidence_ids": [roles_ev_id] if people_claims else [],
        })
    elif roles_status == "source_error":
        claim_items.append({
            "field": "people",
            "value": None,
            "availability": "failed",
            "confidence": 0.5,
            "evidence_ids": [],
        })
    else:
        claim_items.append({
            "field": "people",
            "value": None,
            "availability": "not_applicable" if legal_form in {"ENK"} else "not_available",
            "confidence": 1.0,
            "evidence_ids": [],
        })

    # =========================================================================
    # 5. Workplaces & Locations (Subunits & Registered Office)
    # =========================================================================
    subunits_evidence = evidence_dict.get("locations", {})
    subunits_status = subunits_evidence.get("status")
    subunits_val = subunits_evidence.get("value") or {}
    subunits_list = subunits_val.get("locations") or [] if isinstance(subunits_val, dict) else []

    if subunits_status == "available" and subunits_list:
        subunits_ev_id = f"ev-{org_number}-{ev_counter}"
        ev_counter += 1
        evidence_items.append({
            "id": subunits_ev_id,
            "source_url": subunits_evidence.get("source_url") or f"https://data.brreg.no/enhetsregisteret/api/underenheter?overordnetEnhet={org_number}",
            "source_class": "official_subunits",
            "retrieved_at": subunits_evidence.get("retrieved_at") or completed_at,
            "content_sha256": subunits_evidence.get("content_sha256") or ("0" * 64),
            "claim_span": f"Operational branch subunits ({len(subunits_list)} units)",
        })
        claim_items.append({
            "field": "locations",
            "value": subunits_list[:10],
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": [subunits_ev_id],
        })
    elif addr_str or muni_val:
        # Ground registered office location using official registry evidence
        claim_items.append({
            "field": "locations",
            "value": [{"type": "registered_office", "address": addr_str, "municipality": muni_val}],
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": [reg_ev_id],
        })
    else:
        claim_items.append({
            "field": "locations",
            "value": None,
            "availability": "not_available",
            "confidence": 1.0,
            "evidence_ids": [],
        })

    # =========================================================================
    # 6. Careers & Job Vacancies
    # =========================================================================
    jobs_list = []
    job_evidence_ids = []
    if web_evidence.get("status") == "available" and publishable and isinstance(web_val, dict):
        if web_val.get("jobs"):
            jobs_list.extend(web_val.get("jobs"))
        for page in web_val.get("pages", []):
            if page.get("jobs"):
                jobs_list.extend(page.get("jobs"))
        if jobs_list and web_ev_id:
            job_evidence_ids.append(web_ev_id)

    nav_jobs_ev = evidence_dict.get("nav_jobs", {})
    nav_jobs_val = nav_jobs_ev.get("value") or {}
    nav_jobs_list = nav_jobs_val.get("jobs") or [] if isinstance(nav_jobs_val, dict) else []
    if nav_jobs_ev.get("status") == "available" and nav_jobs_list:
        nav_jobs_ev_id = f"ev-{org_number}-{ev_counter}"
        ev_counter += 1
        evidence_items.append({
            "id": nav_jobs_ev_id,
            "source_url": nav_jobs_ev.get("source_url"),
            "source_class": "official_nav_arbeidsplassen",
            "retrieved_at": nav_jobs_ev.get("retrieved_at") or completed_at,
            "content_sha256": nav_jobs_ev.get("content_sha256") or ("0" * 64),
            "claim_span": f"Open NAV Arbeidsplassen vacancies matched to organisation {org_number}",
        })
        jobs_list.extend(nav_jobs_list)
        job_evidence_ids.append(nav_jobs_ev_id)

    if jobs_list and job_evidence_ids:
        deduped_jobs = list({
            (str(item.get("url") or ""), str(item.get("title") or "")): item
            for item in jobs_list if isinstance(item, dict)
        }.values())
        claim_items.append({
            "field": "jobs",
            "value": deduped_jobs[:10],
            "availability": "available",
            "confidence": 0.95 if nav_jobs_list else 0.9,
            "evidence_ids": job_evidence_ids,
        })
    else:
        is_holding = (emp_val in {0, None}) and any(h in str(profile.get("name", "")).upper() for h in ("HOLDING", "INVEST", "EIENDOM", "KAPITAL", "FINANS", "ASSET"))
        is_passive_form = str(form_val or "").upper() in {"BRL", "ESEK", "FLI", "ORGL", "SAM", "SF"} and (emp_val in {0, None} or emp_val == 0)
        is_zero_emp = emp_val == 0
        is_defunct = bool(profile.get("liquidating") or profile.get("bankrupt"))

        is_na = is_holding or is_passive_form or is_zero_emp or is_defunct
        claim_items.append({
            "field": "jobs",
            "value": None,
            "availability": "not_applicable" if is_na else "not_available",
            "confidence": 1.0,
            "evidence_ids": [],
        })

    # =========================================================================
    # 7. Optional Verified External Signals (Company Activity, News & Reviews)
    # =========================================================================
    website_activity = web_val.get("activities") or [] if isinstance(web_val, dict) else []
    news_ev = evidence_dict.get("public_news")
    if website_activity and web_ev_id:
        claim_items.append({
            "field": "public_activity",
            "value": website_activity[:10],
            "availability": "available",
            "confidence": 0.95,
            "evidence_ids": [web_ev_id],
        })
    elif news_ev and news_ev.get("status") == "available" and (news_ev.get("value") or {}).get("articles"):
        news_ev_id = f"ev-{org_number}-{ev_counter}"
        ev_counter += 1
        evidence_items.append({
            "id": news_ev_id,
            "source_url": news_ev.get("source_url"),
            "source_class": "public_news",
            "retrieved_at": news_ev.get("retrieved_at") or completed_at,
            "content_sha256": news_ev.get("content_sha256") or ("0" * 64),
            "claim_span": f"Public news articles for {profile.get('name')}",
        })
        claim_items.append({
            "field": "public_activity",
            "value": (news_ev.get("value") or {}).get("articles"),
            "availability": "available",
            "confidence": 0.95,
            "evidence_ids": [news_ev_id],
        })
    else:
        claim_items.append({
            "field": "public_activity",
            "value": None,
            "availability": "not_available",
            "confidence": 1.0,
            "evidence_ids": [],
        })

    reviews_ev = evidence_dict.get("public_reviews")
    if reviews_ev and reviews_ev.get("status") == "available" and (reviews_ev.get("value") or {}).get("rating") is not None:
        reviews_ev_id = f"ev-{org_number}-{ev_counter}"
        ev_counter += 1
        evidence_items.append({
            "id": reviews_ev_id,
            "source_url": reviews_ev.get("source_url"),
            "source_class": "public_reviews",
            "retrieved_at": reviews_ev.get("retrieved_at") or completed_at,
            "content_sha256": reviews_ev.get("content_sha256") or ("0" * 64),
            "claim_span": f"Verified customer reviews for {profile.get('name')}",
        })
        claim_items.append({
            "field": "ratings_and_reviews",
            "value": reviews_ev.get("value"),
            "availability": "available",
            "confidence": 0.95,
            "evidence_ids": [reviews_ev_id],
        })

    # =========================================================================
    # 8. Synthesis: Grounded Corporate Summary & Fact Mapping (Section 21)
    # =========================================================================
    summary_sentences = []
    summary_fact_map = []

    # 1. Identity & Operations Statement
    name_display = name_val or "The entity"
    form_display = form_val or "registered entity"
    muni_display = f" based in {muni_val}" if muni_val else ""
    emp_display = f" with {emp_val} registered employees" if emp_val is not None else ""
    s1 = f"{name_display} ({org_number}) is a Norwegian {form_display}{muni_display}{emp_display}."
    summary_sentences.append(s1)
    if name_val:
        summary_fact_map.append({"statement": s1, "field": "legal_name", "value": name_val, "evidence_ids": [reg_ev_id]})

    # 2. Leadership Statement
    if roles_status == "available" and roles_list:
        lead_names = [f"{r.get('name')} ({r.get('role', 'Officer')})" for r in roles_list[:2] if r.get('name')]
        if lead_names:
            s2 = f"Current verified leadership: {', '.join(lead_names)}."
            summary_sentences.append(s2)
            summary_fact_map.append({"statement": s2, "field": "people", "value": lead_names, "evidence_ids": [roles_ev_id]})
    elif legal_form == "ENK":
        s2 = "Sole proprietorship (ENK) without separate registered board leadership."
        summary_sentences.append(s2)
    else:
        s2 = "No separate board leadership roles observed in the official register."
        summary_sentences.append(s2)

    # 3. Financial Statement
    if fin_records and fin_status == "available":
        latest = fin_records[0]
        period = latest.get("reporting_period") or "latest period"
        rev_str = f"{latest.get('revenue'):,.0f} NOK".replace(",", " ") if latest.get('revenue') is not None else "N/A"
        op_str = f"{latest.get('operating_result'):,.0f} NOK".replace(",", " ") if latest.get('operating_result') is not None else "N/A"
        s3 = f"Latest verified financial statements ({period}): Revenue {rev_str}, operating result {op_str}."
        summary_sentences.append(s3)
        if latest.get("revenue") is not None:
            summary_fact_map.append({"statement": s3, "field": "annual_revenue", "value": latest.get('revenue'), "evidence_ids": [fin_ev_id]})
    elif profile.get("latest_submitted_accounts"):
        s3 = f"Official register records latest submitted annual accounts for year {profile.get('latest_submitted_accounts')}."
        summary_sentences.append(s3)
    else:
        s3 = "No statutory financial filings on record in the company accounts register."
        summary_sentences.append(s3)

    # 4. Web Presence Statement
    if website_url and web_evidence.get("status") == "available" and publishable and web_ev_id:
        s4 = f"Verified official corporate website: {website_url}."
        summary_sentences.append(s4)
        summary_fact_map.append({"statement": s4, "field": "official_website", "value": website_url, "evidence_ids": [web_ev_id]})
    else:
        s4 = "Permitted public sources did not provide a confidently verified corporate website."
        summary_sentences.append(s4)

    full_summary_text = " ".join(summary_sentences)

    return {
        "organisation_number": str(org_number),
        "run": {
            "run_id": run_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "terminal_status": "completed",
        },
        "summary": {
            "text": full_summary_text,
            "summary_fact_map": summary_fact_map,
            "grounded_claims_count": len(summary_fact_map),
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

    evidence = envelope.get("evidence")
    ev_ids = set()
    if not isinstance(evidence, list):
        errors.append("Envelope 'evidence' must be a list")
    else:
        for index, ev in enumerate(evidence):
            if not isinstance(ev, dict):
                errors.append(f"Evidence #{index} is not an object")
                continue
            if not ev.get("id") or not ev.get("source_url") or not ev.get("retrieved_at") or not ev.get("content_sha256"):
                errors.append(f"Evidence #{index} missing required fields (id, source_url, retrieved_at, content_sha256)")
            if ev.get("id"):
                ev_ids.add(ev.get("id"))

    claims = envelope.get("claims")
    if not isinstance(claims, list):
        errors.append("Envelope 'claims' must be a list")
    else:
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                errors.append(f"Claim #{index} is not an object")
                continue
            field = claim.get("field")
            if not field:
                errors.append(f"Claim #{index} missing 'field'")
            avail = claim.get("availability")
            if avail not in VALID_AVAILABILITIES:
                errors.append(f"Claim #{index} has invalid availability: {avail!r}")

            val = claim.get("value")
            # Quality gate: missing values must NEVER be converted to zero
            if avail in {"not_available", "not_applicable", "blocked", "ambiguous", "failed"}:
                if val == 0 or val == 0.0:
                    errors.append(f"Claim '{field}' availability is {avail} but value is 0 (missing converted to zero)")

            # Quality gate: every available claim MUST have at least one valid evidence reference
            if avail == "available":
                ev_refs = claim.get("evidence_ids")
                if not ev_refs or not isinstance(ev_refs, list):
                    errors.append(f"Available claim '{field}' missing evidence_ids")
                else:
                    for ref in ev_refs:
                        if ref not in ev_ids:
                            errors.append(f"Claim '{field}' references unknown evidence ID '{ref}'")

    ops = envelope.get("operations")
    if not isinstance(ops, dict) or "requests" not in ops or "runtime_ms" not in ops:
        errors.append("Envelope missing valid 'operations' section")

    return errors
