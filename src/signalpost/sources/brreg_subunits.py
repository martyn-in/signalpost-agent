"""Brønnøysundregistrene Underenheter (Operational Subunits & Locations) Adapter."""

from __future__ import annotations

from typing import Any

from .base import BaseSourceAdapter, SourceHealthMonitor, sha256_hash, utc_now
from norway_company_agent.official import normalize_locations


class BrregSubunitsAdapter(BaseSourceAdapter):
    """Authoritative Underenheter adapter for operational subunits and physical branch locations."""

    def __init__(self) -> None:
        super().__init__(
            name="brreg_subunits",
            source_class="official_subunits",
            priority=4,
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
        url = f"https://data.brreg.no/enhetsregisteret/api/underenheter?overordnetEnhet={org}&size=1000"

        # 1. Check existing evidence in profile
        existing = profile.get("evidence", {}).get("locations")
        if existing and existing.get("status") == "available":
            return existing

        # 2. Live fetch if client available and budget permits
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
                    normalized = normalize_locations(data)
                    content_hash = resp.content_sha256 if hasattr(resp, "content_sha256") else sha256_hash(resp.text)
                    rec = {
                        "status": "available",
                        "source_url": url,
                        "source_class": "official_subunits",
                        "retrieved_at": getattr(resp, "retrieved_at", utc_now()),
                        "content_sha256": content_hash,
                        "value": normalized,
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
                        "source_class": "official_subunits",
                        "retrieved_at": utc_now(),
                        "content_sha256": "0" * 64,
                        "note": f"No subunits registered (HTTP {resp.status_code})",
                    }
                else:
                    if monitor:
                        monitor.record_failure(self.name, f"HTTP {resp.status_code}", lat_ms)
            except Exception as exc:
                if monitor:
                    monitor.record_failure(self.name, str(exc))

        # 3. Offline fallback
        return {
            "status": "not_available",
            "source_url": url,
            "source_class": "official_subunits",
            "retrieved_at": utc_now(),
            "content_sha256": "0" * 64,
            "note": "Subunits unobserved in offline mode",
        }

    def extract_claims(
        self,
        evidence_record: dict[str, Any],
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        org = str(profile.get("organisation_number"))
        status = evidence_record.get("status")
        ev_id = f"ev-{org}-subunits"

        val = evidence_record.get("value") or {}
        subunits = val.get("locations") or []

        locations = []
        for sub in subunits[:10]:
            name = sub.get("name")
            addr_obj = sub.get("address")
            addr_str = None
            if isinstance(addr_obj, dict):
                lines = list(addr_obj.get("adresse") or [])
                pc = addr_obj.get("postnummer")
                city = addr_obj.get("poststed") or addr_obj.get("kommune")
                parts = []
                if lines:
                    parts.append(", ".join(lines))
                if pc and city:
                    parts.append(f"{pc} {city}")
                elif city:
                    parts.append(city)
                addr_str = ", ".join(parts) if parts else None
            elif isinstance(addr_obj, str):
                addr_str = addr_obj

            locations.append({
                "type": "subunit",
                "organisation_number": sub.get("organisation_number"),
                "name": name,
                "address": addr_str,
                "employees": sub.get("employees"),
            })

        if status == "available" and locations:
            return [{
                "field": "locations",
                "value": locations,
                "availability": "available",
                "confidence": 1.0,
                "evidence_ids": [ev_id],
            }]
        else:
            # Fall back to registered office from profile/registry if present
            muni = profile.get("municipality")
            if muni:
                reg_ev_id = f"ev-{org}-registry"
                return [{
                    "field": "locations",
                    "value": [{"type": "registered_office", "municipality": muni}],
                    "availability": "available",
                    "confidence": 1.0,
                    "evidence_ids": [reg_ev_id],
                }]
            return [{
                "field": "locations",
                "value": None,
                "availability": "not_available",
                "confidence": 1.0,
                "evidence_ids": [],
            }]
