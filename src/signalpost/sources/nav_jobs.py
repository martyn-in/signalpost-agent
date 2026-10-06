"""Public NAV Arbeidsplassen job lookup with exact-employer gating and rate pacing."""

from __future__ import annotations

import hashlib
import json
import re
import threading
import time
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from typing import Any

from norway_company_agent.evidence import evidence

SEARCH_URL = "https://arbeidsplassen.nav.no/stillinger/api/search"
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

_nav_lock = threading.Lock()
_nav_last_request_time = 0.0
_nav_backoff_until = 0.0


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


def fetch_nav_jobs(
    org_number: str,
    company_name: str | None = None,
    subunit_orgs: list[str] | None = None,
    *,
    timeout: float = 5.0,
    max_hits: int = 50,
) -> tuple[dict[str, Any], dict[str, Any]]:
    global _nav_last_request_time, _nav_backoff_until

    org = _norm_org(org_number)
    target_orgs = {org}
    if subunit_orgs:
        for sub in subunit_orgs:
            s_norm = _norm_org(sub)
            if len(s_norm) == 9:
                target_orgs.add(s_norm)

    query = urllib.parse.urlencode({"q": org, "size": max_hits})
    url = f"{SEARCH_URL}?{query}"

    # Rate limiting & backoff protection
    with _nav_lock:
        now = time.monotonic()
        if now < _nav_backoff_until:
            # Active rate-limit backoff: return honest not_found without network call
            return evidence(
                "nav_jobs", "not_found", "official_nav_arbeidsplassen", url,
                value={"jobs": [], "employer_org_number": org, "company_name": company_name},
                note="NAV lookup abstained during rate-limit cooldown",
                content_sha256="0" * 64,
            ), {"requests": 0, "bytes": 0, "latencies_ms": []}

        elapsed = now - _nav_last_request_time
        if elapsed < 1.1:
            time.sleep(1.1 - elapsed)
        _nav_last_request_time = time.monotonic()

    req = urllib.request.Request(url, headers={
        "User-Agent": UA,
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "nb,no;q=0.9,en;q=0.8",
    })
    try:
        t0 = time.monotonic()
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(2_000_000)
            latency = int((time.monotonic() - t0) * 1000)
            data = json.loads(raw.decode("utf-8", errors="replace"))

        hits = (((data or {}).get("hits") or {}).get("hits") or []) if isinstance(data, dict) else []
        today = datetime.now(timezone.utc).date().isoformat()
        jobs: list[dict[str, Any]] = []
        seen: set[str] = set()

        for hit in hits:
            src = hit.get("_source") if isinstance(hit, dict) else None
            if not isinstance(src, dict):
                continue
            hit_org = _find_org(src)
            # Match against target organisation number or registered subunits
            if hit_org and hit_org not in target_orgs:
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
                "title": title[:300],
                "location": location,
                "url": job_url,
                "date_posted": _iso_date(src.get("published")),
                "valid_through": expires,
                "status": "active",
                "job_id": uid or None,
                "source": "NAV Arbeidsplassen",
            })

        digest = hashlib.sha256(raw).hexdigest()
        status = "available" if jobs else "not_found"
        return evidence(
            "nav_jobs", status, "official_nav_arbeidsplassen", url,
            value={"jobs": jobs, "employer_org_number": org, "company_name": company_name},
            content_sha256=digest,
        ), {"requests": 1, "bytes": len(raw), "latencies_ms": [latency]}
    except Exception as exc:
        err_str = str(exc)
        if "429" in err_str:
            with _nav_lock:
                _nav_backoff_until = time.monotonic() + 30.0
        return evidence(
            "nav_jobs", "source_error", "official_nav_arbeidsplassen", url,
            note=f"{type(exc).__name__}: {err_str[:180]}",
        ), {"requests": 1, "bytes": 0, "latencies_ms": []}
