"""Brønnøysundregistrene Roller (Corporate Leadership & Board) Adapter."""

from __future__ import annotations

from typing import Any

from .base import BaseSourceAdapter, SourceHealthMonitor, sha256_hash, utc_now
from norway_company_agent.official import normalize_roles


class BrregRolesAdapter(BaseSourceAdapter):
    """Authoritative Roller adapter for executive management and board leadership."""

    def __init__(self) -> None:
        super().__init__(
            name="brreg_roles",
            source_class="official_roles",
            priority=3,
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
        url = f"https://data.brreg.no/enhetsregisteret/api/enheter/{org}/roller"

        # 1. Check existing evidence in profile
        existing = profile.get("evidence", {}).get("roles")
        if existing and existing.get("status") == "available":
            return existing

        # 2. Live fetch if client available and budget permits
        legal_form = str(profile.get("legal_form") or "").upper()
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
                    normalized = normalize_roles(data)
                    content_hash = resp.content_sha256 if hasattr(resp, "content_sha256") else sha256_hash(resp.text)
                    rec = {
                        "status": "available",
                        "source_url": url,
                        "source_class": "official_roles",
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
                        "status": "not_applicable" if legal_form in {"ENK"} else "not_available",
                        "source_url": url,
                        "source_class": "official_roles",
                        "retrieved_at": utc_now(),
                        "content_sha256": "0" * 64,
                        "note": f"No roles registered (HTTP {resp.status_code})",
                    }
                else:
                    if monitor:
                        monitor.record_failure(self.name, f"HTTP {resp.status_code}", lat_ms)
            except Exception as exc:
                if monitor:
                    monitor.record_failure(self.name, str(exc))

        # 3. Offline fallback
        return {
            "status": "not_applicable" if legal_form in {"ENK"} else "not_available",
            "source_url": url,
            "source_class": "official_roles",
            "retrieved_at": utc_now(),
            "content_sha256": "0" * 64,
            "note": "Roles unobserved in offline mode",
        }

    def extract_claims(
        self,
        evidence_record: dict[str, Any],
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        org = str(profile.get("organisation_number"))
        legal_form = str(profile.get("legal_form") or "").upper()
        status = evidence_record.get("status")
        ev_id = f"ev-{org}-roles"

        val = evidence_record.get("value") or {}
        roles = [r for r in val.get("roles") or [] if not r.get("inactive")]

        if status == "available" and roles:
            people_summary = [
                {
                    "name": r.get("name"),
                    "role": r.get("role") or r.get("group"),
                    "role_code": r.get("role_code"),
                }
                for r in roles[:10]
                if r.get("name")
            ]
            return [{
                "field": "people",
                "value": people_summary if people_summary else None,
                "availability": "available" if people_summary else "not_available",
                "confidence": 1.0,
                "evidence_ids": [ev_id] if people_summary else [],
            }]
        else:
            default_avail = "not_applicable" if legal_form in {"ENK"} else "not_available"
            return [{
                "field": "people",
                "value": None,
                "availability": default_avail,
                "confidence": 1.0,
                "evidence_ids": [],
            }]
