"""Deterministic, evidence-grounded company summary briefing."""

from __future__ import annotations

from typing import Any


def format_norwegian_currency(amount: float | None) -> str:
    if amount is None:
        return "N/A"
    if abs(amount) >= 1_000_000:
        return f"{amount / 1_000_000:.1f}M NOK"
    if abs(amount) >= 1_000:
        return f"{amount / 1_000:.1f}k NOK"
    return f"{amount:,.0f} NOK".replace(",", " ")


def generate_company_summary(profile: dict[str, Any]) -> str:
    """Generate concise, fact-grounded summary adhering to stored evidence.
    
    Explicitly reports missing/unobserved fields without fabricating claims.
    """
    name = profile.get("name") or "The company"
    org_number = profile.get("organisation_number")
    legal_form = profile.get("legal_form") or "entity"
    municipality = profile.get("municipality")
    industry_label = profile.get("industry_label") or "commercial operations"
    employees = profile.get("employees")

    lines = []

    # 1. Identity & Operations
    loc_part = f" based in {municipality}" if municipality else ""
    emp_part = f" with {employees} registered employee{'s' if employees != 1 else ''}" if employees is not None else ""
    lines.append(f"{name} ({org_number}) is a Norwegian {legal_form}{loc_part}{emp_part}, active in {industry_label}.")

    # 2. Leadership
    roles_evidence = profile.get("evidence", {}).get("roles", {})
    roles_value = roles_evidence.get("value", {}) if isinstance(roles_evidence, dict) else {}
    roles_list = roles_value.get("roles") or []
    leaders = [r for r in roles_list if r.get("role_code") in {"DAGL", "LEDE"} and not r.get("inactive")]
    if leaders:
        leader_descs = [f"{l.get('name')} ({l.get('role', 'Executive')})" for l in leaders[:2]]
        lines.append(f"Leadership: {', '.join(leader_descs)}.")
    elif roles_evidence.get("status") == "not_found":
        lines.append("Leadership: No official roles registered in the company register.")

    # 3. Financial Overview
    fin_evidence = profile.get("evidence", {}).get("financials", {})
    fin_value = fin_evidence.get("value", {}) if isinstance(fin_evidence, dict) else {}
    records = fin_value.get("records") or []
    if records:
        latest = records[0]
        period = latest.get("reporting_period") or "latest period"
        rev = format_norwegian_currency(latest.get("revenue"))
        op_res = format_norwegian_currency(latest.get("operating_result"))
        assets = format_norwegian_currency(latest.get("assets"))
        lines.append(f"Financials ({period}): Operating revenue of {rev}, operating result of {op_res}, total assets of {assets}.")
    elif profile.get("latest_submitted_accounts"):
        lines.append(f"Financials: Latest submitted annual accounts on record for year {profile.get('latest_submitted_accounts')}.")
    else:
        lines.append("Financials: No filed annual accounts observed in official register.")

    # 4. Web Presence & Locations
    website = profile.get("website")
    web_evidence = profile.get("evidence", {}).get("website", {})
    if website:
        if web_evidence.get("status") == "available":
            lines.append(f"Verified official web domain: {website}.")
        elif web_evidence.get("status") in {"not_found", "source_error"}:
            lines.append(f"Registered website URL ({website}) was uncontactable or failed to respond.")
    else:
        lines.append("Web Presence: No official website URL registered.")

    # 5. Missing / Uncertain Data Notice
    missing: list[str] = []
    if employees is None:
        missing.append("registered employee headcount")
    if not records:
        missing.append("detailed financial accounting breakdown")
    if not website:
        missing.append("verified official web domain")

    if missing:
        lines.append(f"Unobserved information: {', '.join(missing)}.")

    return " ".join(lines)
