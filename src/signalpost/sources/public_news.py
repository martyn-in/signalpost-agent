"""Public News RSS Source Adapter with Exact Legal Entity Matching."""

from __future__ import annotations

import re
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from typing import Any

from .base import BaseSourceAdapter, SourceHealthMonitor, sha256_hash, utc_now

USER_AGENT = "SignalpostResearchAgent/1.0 (+https://builderr.ai)"
LEGAL_TOKENS = {"as", "asa", "sa", "ba", "da", "ans", "enk", "nuf", "sti"}


def exact_title_match(company_name: str, title: str) -> bool:
    """Verify company name appears in news headline with exact boundary matching."""
    company_tokens = [t for t in re.findall(r"[a-z0-9æøå]+", str(company_name or "").casefold()) if t not in LEGAL_TOKENS]
    title_tokens = re.findall(r"[a-z0-9æøå]+", str(title or "").rsplit(" - ", 1)[0].casefold())
    if not company_tokens or not title_tokens or len(company_tokens) > len(title_tokens):
        return False
    for idx in range(len(title_tokens) - len(company_tokens) + 1):
        if title_tokens[idx:idx + len(company_tokens)] == company_tokens:
            return True
    return False


class PublicNewsAdapter(BaseSourceAdapter):
    """Permitted Public News RSS adapter discovering verified news activity."""

    def __init__(self) -> None:
        super().__init__(
            name="public_news",
            source_class="public_news",
            priority=6,
            cost_usd_per_req=0.0,
        )

    def can_handle(self, profile: dict[str, Any]) -> bool:
        name = profile.get("name")
        return bool(name and len(name) >= 3)

    def fetch(
        self,
        profile: dict[str, Any],
        client: Any = None,
        budget: Any = None,
        monitor: SourceHealthMonitor | None = None,
    ) -> dict[str, Any]:
        company_name = str(profile.get("name") or "")
        query = urllib.parse.quote(f'"{company_name}" when:2y')
        url = f"https://news.google.com/rss/search?q={query}&hl=no&gl=NO&ceid=NO:no"

        if budget is not None and not budget.can_request():
            return {
                "status": "not_available",
                "source_url": url,
                "source_class": "public_news",
                "retrieved_at": utc_now(),
                "content_sha256": "0" * 64,
                "note": "Budget exhausted",
            }

        try:
            import time
            t0 = time.monotonic()
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "application/rss+xml, application/xml"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                raw = resp.read(500_000)
            lat_ms = int((time.monotonic() - t0) * 1000)
            if budget is not None:
                budget.record_request(cost_usd=0.0)

            root = ET.fromstring(raw)
            articles = []
            for item in root.findall(".//item")[:5]:
                title = str(item.findtext("title") or "").strip()
                link = str(item.findtext("link") or "").strip()
                pub_date = str(item.findtext("pubDate") or "").strip()
                source = str(item.findtext("source") or "").strip()
                if link and exact_title_match(company_name, title):
                    articles.append({
                        "title": title,
                        "url": link,
                        "published_at": pub_date,
                        "source": source,
                    })

            content_hash = sha256_hash(raw)
            if monitor:
                monitor.record_success(self.name, lat_ms, len(raw))

            return {
                "status": "available" if articles else "not_available",
                "source_url": url,
                "source_class": "public_news",
                "retrieved_at": utc_now(),
                "content_sha256": content_hash,
                "value": {"articles": articles},
            }
        except Exception as exc:
            if monitor:
                monitor.record_failure(self.name, str(exc))
            return {
                "status": "source_error",
                "source_url": url,
                "source_class": "public_news",
                "retrieved_at": utc_now(),
                "content_sha256": "0" * 64,
                "note": f"News fetch error: {exc}",
            }

    def extract_claims(
        self,
        evidence_record: dict[str, Any],
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        status = evidence_record.get("status")
        val = evidence_record.get("value") or {}
        articles = val.get("articles") or []
        org = str(profile.get("organisation_number"))
        ev_id = f"ev-{org}-news"

        if status == "available" and articles:
            return [{
                "field": "public_activity",
                "value": articles,
                "availability": "available",
                "confidence": 0.95,
                "evidence_ids": [ev_id],
            }]
        return []
