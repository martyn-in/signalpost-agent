"""Brønnøysundregistrene Regnskapsregisteret (Annual Accounts) Adapter."""

from __future__ import annotations

from typing import Any

from .base import BaseSourceAdapter, SourceHealthMonitor, sha256_hash, utc_now
from signalpost.extraction.financials import normalize_financial_statement


class BrregFinancialsAdapter(BaseSourceAdapter):
    """Authoritative Regnskapsregisteret adapter for financial accounts and P&L statements."""

    def __init__(self) -> None:
        super().__init__(
            name="brreg_financials",
            source_class="official_annual_accounts",
            priority=2,
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
        url = f"https://data.brreg.no/regnskapsregisteret/regnskap/{org}"

        # 1. Check existing evidence in profile
        existing = profile.get("evidence", {}).get("financials")
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
                    raw_records = data if isinstance(data, list) else [data]
                    records = [normalize_financial_statement(r) for r in raw_records[:3]]
                    content_hash = resp.content_sha256 if hasattr(resp, "content_sha256") else sha256_hash(resp.text)
                    rec = {
                        "status": "available",
                        "source_url": url,
                        "source_class": "official_annual_accounts",
                        "retrieved_at": getattr(resp, "retrieved_at", utc_now()),
                        "content_sha256": content_hash,
                        "value": {"records": records},
                    }
                    if monitor:
                        monitor.record_success(self.name, lat_ms, len(resp.text.encode()))
                    return rec
                elif resp.status_code in {404, 410}:
                    if monitor:
                        monitor.record_success(self.name, lat_ms)
                    return {
                        "status": "not_available" if legal_form not in {"ENK", "FLI"} else "not_applicable",
                        "source_url": url,
                        "source_class": "official_annual_accounts",
                        "retrieved_at": utc_now(),
                        "content_sha256": "0" * 64,
                        "note": f"No annual accounts filed (HTTP {resp.status_code})",
                    }
                else:
                    if monitor:
                        monitor.record_failure(self.name, f"HTTP {resp.status_code}", lat_ms)
            except Exception as exc:
                if monitor:
                    monitor.record_failure(self.name, str(exc))

        # 3. Offline / Unfiled fallback
        return {
            "status": "not_applicable" if legal_form in {"ENK", "FLI"} else "not_available",
            "source_url": url,
            "source_class": "official_annual_accounts",
            "retrieved_at": utc_now(),
            "content_sha256": "0" * 64,
            "note": "Accounts unobserved in offline mode",
        }

    def extract_claims(
        self,
        evidence_record: dict[str, Any],
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        claims = []
        org = str(profile.get("organisation_number"))
        legal_form = str(profile.get("legal_form") or "").upper()
        status = evidence_record.get("status")
        ev_id = f"ev-{org}-financials"

        val = evidence_record.get("value") or {}
        records = val.get("records") or []

        if status == "available" and records:
            latest = records[0]
            # Annual Revenue
            rev = latest.get("revenue")
            claims.append({
                "field": "annual_revenue",
                "value": rev,
                "availability": "available" if rev is not None else "not_available",
                "confidence": 1.0,
                "evidence_ids": [ev_id] if rev is not None else [],
            })

            # Operating Result
            op_res = latest.get("operating_result")
            claims.append({
                "field": "operating_result",
                "value": op_res,
                "availability": "available" if op_res is not None else "not_available",
                "confidence": 1.0,
                "evidence_ids": [ev_id] if op_res is not None else [],
            })
        else:
            default_avail = "not_applicable" if legal_form in {"ENK", "FLI"} else "not_available"
            claims.append({
                "field": "annual_revenue",
                "value": None,
                "availability": default_avail,
                "confidence": 1.0,
                "evidence_ids": [],
            })
            claims.append({
                "field": "operating_result",
                "value": None,
                "availability": default_avail,
                "confidence": 1.0,
                "evidence_ids": [],
            })

        return claims
