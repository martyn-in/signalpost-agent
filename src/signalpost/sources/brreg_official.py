"""Brønnøysundregistrene Enhetsregisteret (Official Registry) Adapter."""

from __future__ import annotations

import json
from typing import Any

from .base import BaseSourceAdapter, SourceHealthMonitor, sha256_hash, utc_now
from norway_company_agent.official import accounting_obligation_assessment


class BrregOfficialAdapter(BaseSourceAdapter):
    """Authoritative Enhetsregisteret adapter for foundational corporate identity."""

    def __init__(self) -> None:
        super().__init__(
            name="brreg_official",
            source_class="official_registry",
            priority=1,
            cost_usd_per_req=0.0,
        )

    def can_handle(self, profile: dict[str, Any]) -> bool:
        org = str(profile.get("organisation_number") or "")
        return len(org) == 9 and org.isdigit()

    def fetch(
        self,
        profile: dict[str, Any],
        client: Any = None,
        budget: Any = None,
        monitor: SourceHealthMonitor | None = None,
    ) -> dict[str, Any]:
        org = str(profile["organisation_number"])
        url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{org}"

        # 1. Check if profile already has live registry evidence or offline snapshot
        existing = profile.get("evidence", {}).get("registry_live")
        if existing and existing.get("status") == "available":
            return existing

        # If client is provided and budget allows, fetch live
        if client is not None and (budget is None or budget.can_request()):
            try:
                import time
                t0 = time.monotonic()
                resp = client.get(url)
                lat_ms = int((time.monotonic() - t0) * 1000)
                if budget is not None:
                    budget.record_request(cost_usd=0.0)

                if resp.status_code == 200:
                    data = resp.json()
                    content_hash = resp.content_sha256 if hasattr(resp, "content_sha256") else sha256_hash(resp.text)
                    rec = {
                        "status": "available",
                        "source_url": url,
                        "source_class": "official_registry",
                        "retrieved_at": getattr(resp, "retrieved_at", utc_now()),
                        "content_sha256": content_hash,
                        "value": data,
                    }
                    if monitor:
                        monitor.record_success(self.name, lat_ms, len(resp.text.encode()))
                    return rec
                elif resp.status_code in {404, 410}:
                    if monitor:
                        monitor.record_success(self.name, lat_ms)
                    return {
                        "status": "not_available",
                        "source_url": url,
                        "source_class": "official_registry",
                        "retrieved_at": utc_now(),
                        "content_sha256": "0" * 64,
                        "note": f"Entity not found in register (HTTP {resp.status_code})",
                    }
                else:
                    if monitor:
                        monitor.record_failure(self.name, f"HTTP {resp.status_code}", lat_ms)
            except Exception as exc:
                if monitor:
                    monitor.record_failure(self.name, str(exc))

        # 2. Offline snapshot fallback from bulk profile
        bulk_evidence = profile.get("evidence", {}).get("registry")
        if bulk_evidence:
            return bulk_evidence

        # 3. Construct minimal snapshot evidence if profile fields are populated
        if profile.get("name"):
            raw_data = {
                "organisasjonsnummer": org,
                "navn": profile.get("name"),
                "organisasjonsform": {"kode": profile.get("legal_form")},
                "antallAnsatte": profile.get("employees"),
                "forretningsadresse": {"kommune": profile.get("municipality")},
                "hjemmeside": profile.get("website"),
                "sisteInnsendteAarsregnskap": profile.get("latest_submitted_accounts"),
            }
            raw_json = json.dumps(raw_data, sort_keys=True)
            return {
                "status": "available",
                "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/lastned/csv",
                "source_class": "official_registry_bulk",
                "retrieved_at": utc_now(),
                "content_sha256": sha256_hash(raw_json),
                "value": raw_data,
            }

        return {
            "status": "not_available",
            "source_url": url,
            "source_class": "official_registry",
            "retrieved_at": utc_now(),
            "content_sha256": "0" * 64,
            "note": "Registry evidence unavailable",
        }

    def extract_claims(
        self,
        evidence_record: dict[str, Any],
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        claims = []
        org = str(profile.get("organisation_number"))
        status = evidence_record.get("status")
        ev_id = f"ev-{org}-registry"

        if status != "available":
            for field in ("legal_name", "legal_form", "employees", "municipality", "registered_address"):
                claims.append({
                    "field": field,
                    "value": None,
                    "availability": "not_available",
                    "confidence": 1.0,
                    "evidence_ids": [],
                })
            return claims

        val = evidence_record.get("value") or {}
        name = profile.get("name") or val.get("navn") or val.get("name")
        form = profile.get("legal_form") or (val.get("organisasjonsform") or {}).get("kode") if isinstance(val.get("organisasjonsform"), dict) else val.get("organisasjonsform")
        emp = profile.get("employees") if profile.get("employees") is not None else val.get("antallAnsatte") or val.get("employees")
        muni = profile.get("municipality") or (val.get("forretningsadresse") or {}).get("kommune") or val.get("municipality")

        # Address extraction
        b_addr = val.get("forretningsadresse") or {}
        address_str = None
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
            address_str = ", ".join(parts) if parts else None

        # Legal Name
        claims.append({
            "field": "legal_name",
            "value": name,
            "availability": "available" if name else "not_available",
            "confidence": 1.0,
            "evidence_ids": [ev_id] if name else [],
        })

        # Legal Form
        claims.append({
            "field": "legal_form",
            "value": form,
            "availability": "available" if form else "not_available",
            "confidence": 1.0,
            "evidence_ids": [ev_id] if form else [],
        })

        # Employees
        claims.append({
            "field": "employees",
            "value": emp,
            "availability": "available" if emp is not None else "not_available",
            "confidence": 1.0,
            "evidence_ids": [ev_id] if emp is not None else [],
        })

        # Municipality
        claims.append({
            "field": "municipality",
            "value": muni,
            "availability": "available" if muni else "not_available",
            "confidence": 1.0,
            "evidence_ids": [ev_id] if muni else [],
        })

        # Registered Address
        claims.append({
            "field": "registered_address",
            "value": address_str,
            "availability": "available" if address_str else "not_available",
            "confidence": 1.0,
            "evidence_ids": [ev_id] if address_str else [],
        })

        # Accounting Obligation
        acc_assessment = accounting_obligation_assessment(profile)
        acc_val = acc_assessment.get("value", {})
        claims.append({
            "field": "accounting_obligation",
            "value": acc_val.get("classification"),
            "availability": "available",
            "confidence": 1.0,
            "evidence_ids": [ev_id],
        })

        return claims
