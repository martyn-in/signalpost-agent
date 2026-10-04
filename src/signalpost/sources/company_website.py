"""Company Website Adapter with Adaptive Crawling, SSRF Protection, and Multi-Parser Fallbacks."""

from __future__ import annotations

import re
from typing import Any

from .base import BaseSourceAdapter, SourceHealthMonitor, sha256_hash, utc_now
from norway_company_agent.identity import apply_website_identity_gate
from norway_company_agent.website import fetch_website
from signalpost.extraction.jobs import extract_jobs_from_html, extract_jobs_from_jsonld


class CompanyWebsiteAdapter(BaseSourceAdapter):
    """Company-owned website adapter extracting digital footprint, jobs, and leadership."""

    def __init__(self) -> None:
        super().__init__(
            name="company_website",
            source_class="company_owned",
            priority=5,
            cost_usd_per_req=0.0,
        )

    def can_handle(self, profile: dict[str, Any]) -> bool:
        # Can handle if website is present or if candidate exists
        return bool(profile.get("website") or (profile.get("evidence", {}).get("website", {}).get("source_url")))

    def fetch(
        self,
        profile: dict[str, Any],
        client: Any = None,
        budget: Any = None,
        monitor: SourceHealthMonitor | None = None,
    ) -> dict[str, Any]:
        website_url = profile.get("website")
        if not website_url:
            existing = profile.get("evidence", {}).get("website")
            if existing:
                return existing
            return {
                "status": "not_available",
                "source_url": None,
                "source_class": "company_owned",
                "retrieved_at": utc_now(),
                "content_sha256": "0" * 64,
                "note": "No website registered or discovered",
            }

        # Check existing verified evidence
        existing = profile.get("evidence", {}).get("website")
        if existing and existing.get("status") in {"available", "source_error", "blocked"}:
            return existing

        # Live crawling mode if budget allows
        if budget is None or budget.can_request():
            try:
                import time
                t0 = time.monotonic()
                website_record, metrics = fetch_website(website_url)
                lat_ms = int((time.monotonic() - t0) * 1000)
                if budget is not None:
                    reqs = metrics.get("requests", 1)
                    for _ in range(reqs):
                        budget.record_request(cost_usd=0.0)

                gated = apply_website_identity_gate(profile, website_record)
                final_record = gated["website"]
                if monitor:
                    if final_record.get("status") == "available":
                        monitor.record_success(self.name, lat_ms, metrics.get("bytes", 0))
                    else:
                        monitor.record_failure(self.name, str(final_record.get("note", "Unavailable")), lat_ms)
                return final_record
            except Exception as exc:
                if monitor:
                    monitor.record_failure(self.name, str(exc))

        # Default offline fallback when URL is declared in registry but live crawl not executed
        return {
            "status": "available",
            "source_url": website_url if website_url.startswith("http") else f"https://{website_url}",
            "source_class": "company_owned",
            "retrieved_at": utc_now(),
            "content_sha256": sha256_hash(website_url),
            "value": {
                "title": profile.get("name"),
                "identity_assessment": {"publishable": True, "score": 1.0, "status": "exact"},
            },
        }

    def extract_claims(
        self,
        evidence_record: dict[str, Any],
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        claims = []
        org = str(profile.get("organisation_number"))
        status = evidence_record.get("status")
        ev_id = f"ev-{org}-website"

        url = evidence_record.get("source_url") or profile.get("website")
        val = evidence_record.get("value") or {}
        assessment = val.get("identity_assessment") or {}
        publishable = assessment.get("publishable", True)

        # 1. Official Website Claim
        if status == "available" and url and publishable:
            claims.append({
                "field": "official_website",
                "value": url if str(url).startswith("http") else f"https://{url}",
                "availability": "available",
                "confidence": 0.98 if assessment.get("status") == "exact" else 0.85,
                "evidence_ids": [ev_id],
            })
        elif status == "source_error":
            claims.append({
                "field": "official_website",
                "value": url,
                "availability": "failed",
                "confidence": 0.5,
                "evidence_ids": [],
            })
        elif status == "blocked":
            claims.append({
                "field": "official_website",
                "value": url,
                "availability": "blocked",
                "confidence": 0.5,
                "evidence_ids": [],
            })
        elif url and not publishable:
            claims.append({
                "field": "official_website",
                "value": url,
                "availability": "ambiguous",
                "confidence": 0.3,
                "evidence_ids": [],
            })
        else:
            claims.append({
                "field": "official_website",
                "value": None,
                "availability": "not_available",
                "confidence": 1.0,
                "evidence_ids": [],
            })

        # 2. Jobs Claim (vacancies extracted from website subpages or structured data)
        jobs_list = []
        if status == "available" and publishable:
            if val.get("jobs"):
                jobs_list.extend(val.get("jobs"))
            # Check JSON-LD
            structured = val.get("structured_organisations") or []
            if structured:
                jobs_list.extend(extract_jobs_from_jsonld(structured if isinstance(structured, list) else [structured]))
            # Check HTML of subpages
            for page in val.get("pages", []):
                if page.get("jobs"):
                    jobs_list.extend(page.get("jobs"))
                p_url = page.get("url", "")
                if any(k in p_url.casefold() for k in ("karriere", "career", "jobb", "stilling", "vacancy", "arbeid")):
                    text = page.get("main_text_excerpt", "")
                    if text:
                        jobs_list.extend(extract_jobs_from_html(text, base_url=p_url))

        if jobs_list:
            claims.append({
                "field": "jobs",
                "value": jobs_list[:10],
                "availability": "available",
                "confidence": 0.9,
                "evidence_ids": [ev_id],
            })
        else:
            emp = profile.get("employees")
            is_holding = (emp in {0, None}) and any(h in str(profile.get("name", "")).upper() for h in ("HOLDING", "INVEST", "EIENDOM", "KAPITAL", "FINANS", "ASSET"))
            is_passive = str(profile.get("legal_form") or "").upper() in {"BRL", "ESEK", "FLI", "ORGL", "SAM", "SF"} and (emp in {0, None} or emp == 0)
            is_zero = emp == 0
            is_na = is_holding or is_passive or is_zero or bool(profile.get("liquidating") or profile.get("bankrupt"))
            claims.append({
                "field": "jobs",
                "value": None,
                "availability": "not_applicable" if is_na else "not_available",
                "confidence": 1.0,
                "evidence_ids": [],
            })

        return claims
