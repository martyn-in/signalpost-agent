"""Public Reviews Source Adapter with Exact Norwegian Organisation Attribution."""

from __future__ import annotations

import json
import re
import unicodedata
import urllib.request
from typing import Any

from bs4 import BeautifulSoup
from .base import BaseSourceAdapter, SourceHealthMonitor, sha256_hash, utc_now

USER_AGENT = "SignalpostResearchAgent/1.0 (+https://builderr.ai)"


def slug(value: object) -> str:
    text = str(value or "").translate(str.maketrans({"ø": "o", "å": "a", "æ": "ae", "Ø": "O", "Å": "A", "Æ": "AE"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode().casefold()
    return "-".join(re.findall(r"[a-z0-9]+", text))


class PublicReviewsAdapter(BaseSourceAdapter):
    """Permitted Public Reviews adapter extracting verified customer rating signals."""

    def __init__(self) -> None:
        super().__init__(
            name="public_reviews",
            source_class="public_reviews",
            priority=7,
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
        name = profile.get("name") or ""
        company_slug = slug(name)
        url = f"https://www.fagfolkguiden.no/bedrift/{company_slug}-{org}"

        if budget is not None and not budget.can_request():
            return {
                "status": "not_available",
                "source_url": url,
                "source_class": "public_reviews",
                "retrieved_at": utc_now(),
                "content_sha256": "0" * 64,
                "note": "Budget exhausted",
            }

        try:
            import time
            t0 = time.monotonic()
            req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": "text/html"})
            with urllib.request.urlopen(req, timeout=8) as resp:
                raw = resp.read(500_000)
            lat_ms = int((time.monotonic() - t0) * 1000)
            if budget is not None:
                budget.record_request(cost_usd=0.0)

            soup = BeautifulSoup(raw, "html.parser")
            text = soup.get_text(" ", strip=True)

            # Strict verification: Org number and name must appear in page
            if org not in re.sub(r"\D", "", text) or name.casefold() not in text.casefold():
                return {
                    "status": "not_available",
                    "source_url": url,
                    "source_class": "public_reviews",
                    "retrieved_at": utc_now(),
                    "content_sha256": sha256_hash(raw),
                    "note": "Page did not match exact legal entity",
                }

            # Extract aggregateRating from JSON-LD
            rating_val = None
            review_count = None
            for node in soup.find_all("script", attrs={"type": "application/ld+json"}):
                try:
                    data = json.loads(node.string or node.get_text() or "{}")
                    candidates = data if isinstance(data, list) else [data]
                    for item in candidates:
                        agg = (item or {}).get("aggregateRating")
                        if isinstance(agg, dict):
                            rating_val = float(agg.get("ratingValue"))
                            review_count = int(agg.get("ratingCount") or agg.get("reviewCount") or 0)
                            break
                except Exception:
                    continue

            content_hash = sha256_hash(raw)
            if monitor:
                monitor.record_success(self.name, lat_ms, len(raw))

            if rating_val is not None:
                return {
                    "status": "available",
                    "source_url": url,
                    "source_class": "public_reviews",
                    "retrieved_at": utc_now(),
                    "content_sha256": content_hash,
                    "value": {
                        "rating": rating_val,
                        "review_count": review_count,
                    },
                }
            return {
                "status": "not_available",
                "source_url": url,
                "source_class": "public_reviews",
                "retrieved_at": utc_now(),
                "content_sha256": content_hash,
                "note": "No aggregate rating found",
            }
        except Exception as exc:
            if monitor:
                monitor.record_failure(self.name, str(exc))
            return {
                "status": "not_available",
                "source_url": url,
                "source_class": "public_reviews",
                "retrieved_at": utc_now(),
                "content_sha256": "0" * 64,
                "note": f"Reviews lookup error: {exc}",
            }

    def extract_claims(
        self,
        evidence_record: dict[str, Any],
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        status = evidence_record.get("status")
        val = evidence_record.get("value") or {}
        org = str(profile.get("organisation_number"))
        ev_id = f"ev-{org}-reviews"

        if status == "available" and val.get("rating") is not None:
            return [{
                "field": "ratings_and_reviews",
                "value": val,
                "availability": "available",
                "confidence": 0.95,
                "evidence_ids": [ev_id],
            }]
        return []
