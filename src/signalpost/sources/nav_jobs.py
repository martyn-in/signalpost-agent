"""Public NAV Arbeidsplassen job lookup with exact-employer gating."""

from __future__ import annotations

import hashlib
import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from norway_company_agent.evidence import evidence

SEARCH_URL = "https://arbeidsplassen.nav.no/stillinger/api/search"
UA = "builderr-signalpost/1.0 (+https://builderr.ai)"


def _norm_org(value: Any) -> str:
    return re.sub(r"\D", "", str(value or ""))


def _find_org(src: dict[str, Any]) -> str:
    employer = src.get("employer") if isinstance(src.get("employer"), dict) else {}
    props = src.get("properties") if isinstance(src.get("properties"), dict) else {}
    for value in (
        employer.get("orgnr"), employer.get("orgNr"), employer.get("organizationNumber"),
        employer.get("organisationNumber"), props.get("employerorgnr"), props.get("orgnr"),
        src.get("employerOrgNr"), src.get("employerorgnr"),
    ):
        org = _norm_org(value)
        if len(org) == 9:
            return org
    return ""


def _iso_date(value: Any) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    m = re.match(r"(20\d{2}-\d{2}-\d{2})", text)
    return m.group(1) if m else None


def fetch_nav_jobs(org_number: str, company_name: str | None = None, *, timeout: float = 6.0, max_hits: int = 50) -> tuple[dict[str, Any], dict[str, Any]]:
    org = _norm_org(org_number)
    query = urllib.parse.urlencode({"q": org, "size": max_hits})
    url = f"{SEARCH_URL}?{query}"
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(2_000_000)
            data = json.loads(raw.decode("utf-8", errors="replace"))
        hits = (((data or {}).get("hits") or {}).get("hits") or []) if isinstance(data, dict) else []
        today = datetime.now(timezone.utc).date().isoformat()
        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()
        for hit in hits:
            src = hit.get("_source") if isinstance(hit, dict) else None
            if not isinstance(src, dict) or _find_org(src) != org:
                continue
            expires = _iso_date(src.get("expires") or src.get("applicationDue"))
            if expires and expires < today:
                continue
            uid = str(src.get("uuid") or hit.get("_id") or "").strip()
            title = str(src.get("title") or "").strip()
            if not title:
                continue
            if uid and uid in seen:
                continue
            seen.add(uid or title)
            location_obj = src.get("location") if isinstance(src.get("location"), dict) else {}
            location = str(location_obj.get("city") or location_obj.get("municipal") or src.get("workLocations") or "").strip() or None
            job_url = f"https://arbeidsplassen.nav.no/stillinger/stilling/{uid}" if uid else url
            jobs.append({
                "title": title[:300], "location": location, "url": job_url,
                "date_posted": _iso_date(src.get("published")), "valid_through": expires,
                "status": "active", "job_id": uid or None, "source": "NAV Arbeidsplassen",
            })
        digest = hashlib.sha256(raw).hexdigest()
        status = "available" if jobs else "not_found"
        return evidence(
            "nav_jobs", status, "official_nav_arbeidsplassen", url,
            value={"jobs": jobs, "employer_org_number": org, "company_name": company_name},
            content_sha256=digest,
        ), {"requests": 1, "bytes": len(raw), "latencies_ms": []}
    except Exception as exc:
        return evidence(
            "nav_jobs", "source_error", "official_nav_arbeidsplassen", url,
            note=f"{type(exc).__name__}: {str(exc)[:180]}",
        ), {"requests": 1, "bytes": 0, "latencies_ms": []}
