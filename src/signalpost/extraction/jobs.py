"""Careers and job opening extraction and fingerprinting."""

from __future__ import annotations

import hashlib
import re
import urllib.parse
from datetime import datetime, timezone
from typing import Any
from bs4 import BeautifulSoup


def extract_jobs_from_jsonld(json_data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract JobPosting items from schema.org JSON-LD structured data."""
    jobs: list[dict[str, Any]] = []

    def _recurse(node: Any) -> None:
        if isinstance(node, dict):
            node_type = str(node.get("@type") or "")
            if node_type == "JobPosting":
                title = node.get("title")
                valid_through = str(node.get("validThrough") or "").strip() or None
                expiry = re.match(r"(20\\d{2}-\\d{2}-\\d{2})", valid_through or "")
                if expiry and expiry.group(1) < datetime.now(timezone.utc).date().isoformat():
                    title = None
                if title:
                    loc = node.get("jobLocation")
                    address = loc.get("address", {}) if isinstance(loc, dict) else {}
                    loc_str = address.get("addressLocality") if isinstance(address, dict) else str(loc or "")
                    jobs.append({
                        "title": str(title).strip(),
                        "location": str(loc_str).strip() or None,
                        "department": str(node.get("department") or "").strip() or None,
                        "employment_type": str(node.get("employmentType") or "").strip() or None,
                        "url": str(node.get("url") or "").strip() or None,
                        "date_posted": str(node.get("datePosted") or "").strip() or None,
                        "valid_through": valid_through,
                        "status": "active",
                    })
            for child in node.values():
                _recurse(child)
        elif isinstance(node, list):
            for item in node:
                _recurse(item)

    _recurse(json_data)
    return list({(str(j.get("url") or ""), str(j.get("title") or "")): j for j in jobs}.values())[:30]


def extract_jobs_from_html(html_text: str, base_url: str = "") -> list[dict[str, Any]]:
    """Deterministic heuristic extraction of job vacancies from careers page HTML."""
    soup = BeautifulSoup(html_text, "html.parser")
    jobs: list[dict[str, Any]] = []

    # Look for common job card containers
    card_selectors = [
        "li[class*='job']", "div[class*='job-item']", "div[class*='career-card']",
        "div[class*='vacancy']", "article[class*='job']", "tr[class*='job']"
    ]

    elements = soup.select(", ".join(card_selectors))
    for el in elements[:30]:  # Cap at 30 items
        title_el = el.find(["h2", "h3", "h4", "a", "strong"])
        if not title_el:
            continue
        title = title_el.get_text(strip=True)
        if len(title) < 4 or len(title) > 100:
            continue

        # Look for link
        link_el = el if el.name == "a" else el.find("a")
        href = link_el.get("href") if link_el else None
        if href and base_url:
            import urllib.parse
            href = urllib.parse.urljoin(base_url, href)

        text = el.get_text(" ", strip=True)
        # Check for location keywords in Norway
        loc_match = re.search(r"\b(Oslo|Bergen|Trondheim|Stavanger|Tromsø|Kristiansand|Drammen|Sandnes)\b", text, re.I)
        location = loc_match.group(1) if loc_match else None

        fingerprint = hashlib.sha256(f"{title}:{location}:{href}".encode()).hexdigest()
        jobs.append({
            "title": title,
            "location": location,
            "url": href,
            "fingerprint": fingerprint,
            "status": "active",
        })

    # Many Norwegian career pages use ordinary links rather than job-card classes.
    # Require vacancy-like URL/text signals and never treat the careers landing page itself as a vacancy.
    landing_paths = {"/karriere", "/career", "/careers", "/jobb", "/jobber", "/jobs", "/ledige-stillinger", "/stillinger"}
    vacancy_terms = re.compile(r"(ledig.?stilling|stilling|jobb|job|career|position|vacanc|soker|søker)", re.I)
    ats_hosts = ("teamtailor.", "jobbnorge.", "webcruiter.", "reachmee.", "easycruit.", "workday.", "greenhouse.", "lever.", "smartrecruiters.")
    seen_urls = {str(j.get("url") or "") for j in jobs}
    for a in soup.select("a[href]")[:300]:
        raw = str(a.get("href") or "").strip()
        full = urllib.parse.urljoin(base_url, raw)
        parsed = urllib.parse.urlparse(full)
        path = parsed.path.rstrip("/").casefold() or "/"
        text = a.get_text(" ", strip=True)
        if path in landing_paths:
            continue
        signal = vacancy_terms.search(path + " " + text) or any(host in parsed.netloc.casefold() for host in ats_hosts)
        if not signal or full in seen_urls:
            continue
        title = text.strip()
        if len(title) < 4 or len(title) > 120:
            slug = path.rsplit("/", 1)[-1].replace("-", " ").replace("_", " ").strip()
            title = slug.title()
        if len(title) < 4 or len(title) > 120:
            continue
        # Avoid navigation labels that are categories, not concrete vacancies.
        if title.casefold() in {"jobb", "jobber", "jobs", "career", "careers", "karriere", "stillinger", "ledige stillinger"}:
            continue
        seen_urls.add(full)
        jobs.append({
            "title": title,
            "location": None,
            "url": full,
            "fingerprint": hashlib.sha256(f"{title}:None:{full}".encode()).hexdigest(),
            "status": "active",
        })

    return list({(str(j.get("url") or ""), str(j.get("title") or "")): j for j in jobs}.values())[:30]
