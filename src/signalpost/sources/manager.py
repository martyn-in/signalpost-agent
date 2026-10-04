"""Central Source Pipeline Manager orchestrating adapters, priorities, health monitoring, and conflict resolution."""

from __future__ import annotations

from typing import Any

from .base import BaseSourceAdapter, RequestValueScorer, SourceHealthMonitor, utc_now
from .brreg_official import BrregOfficialAdapter
from .brreg_financials import BrregFinancialsAdapter
from .brreg_roles import BrregRolesAdapter
from .brreg_subunits import BrregSubunitsAdapter
from .company_website import CompanyWebsiteAdapter
from .public_news import PublicNewsAdapter
from .public_reviews import PublicReviewsAdapter


class SourcePipelineManager:
    """Orchestrates modular adapters with adaptive priority, request-value scoring, and health monitoring."""

    def __init__(
        self,
        health_monitor: SourceHealthMonitor | None = None,
        enable_external_signals: bool = True,
    ) -> None:
        self.monitor = health_monitor or SourceHealthMonitor()
        self.adapters: list[BaseSourceAdapter] = [
            BrregOfficialAdapter(),
            BrregFinancialsAdapter(),
            BrregRolesAdapter(),
            BrregSubunitsAdapter(),
            CompanyWebsiteAdapter(),
        ]
        if enable_external_signals:
            self.adapters.extend([
                PublicNewsAdapter(),
                PublicReviewsAdapter(),
            ])

    def enrich_profile(
        self,
        profile: dict[str, Any],
        client: Any = None,
        budget: Any = None,
        offline_only: bool = False,
    ) -> dict[str, Any]:
        """Execute applicable adapters in priority order and update profile evidence."""
        profile.setdefault("evidence", {})
        remaining_requests = budget.remaining_requests() if budget else 2000

        # Sort adapters by expected request value
        ranked = sorted(
            [a for a in self.adapters if a.can_handle(profile)],
            key=lambda a: -RequestValueScorer.expected_value(a.name, profile, remaining_requests),
        )

        for adapter in ranked:
            # Skip if circuit breaker is open
            if not self.monitor.is_healthy(adapter.name):
                continue

            # If budget exhausted, only run offline capable adapters
            if budget is not None and not budget.can_request() and not offline_only:
                continue

            effective_client = None if offline_only else client
            try:
                evidence_rec = adapter.fetch(
                    profile=profile,
                    client=effective_client,
                    budget=budget if not offline_only else None,
                    monitor=self.monitor,
                )
                if evidence_rec:
                    # Map to evidence key
                    key = adapter.name.replace("brreg_", "")
                    profile["evidence"][key] = evidence_rec
            except Exception as exc:
                self.monitor.record_failure(adapter.name, str(exc))

        return profile

    def extract_all_claims(
        self,
        profile: dict[str, Any],
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Extract unified claims and evidence items from all adapters with conflict handling."""
        claims_map: dict[str, dict[str, Any]] = {}
        evidence_items: list[dict[str, Any]] = []
        evidence_seen: set[str] = set()
        org = str(profile.get("organisation_number"))

        for adapter in self.adapters:
            key = adapter.name.replace("brreg_", "")
            evidence_rec = profile.get("evidence", {}).get(key)
            if not evidence_rec:
                # Synthesize default claim if not checked
                extracted = adapter.extract_claims({"status": "not_available"}, profile)
            else:
                extracted = adapter.extract_claims(evidence_rec, profile)
                # Register evidence record if not already recorded
                ev_id = f"ev-{org}-{key}"
                if ev_id not in evidence_seen and evidence_rec.get("source_url"):
                    evidence_seen.add(ev_id)
                    evidence_items.append({
                        "id": ev_id,
                        "source_url": evidence_rec.get("source_url"),
                        "source_class": evidence_rec.get("source_class") or adapter.source_class,
                        "retrieved_at": evidence_rec.get("retrieved_at") or utc_now(),
                        "content_sha256": evidence_rec.get("content_sha256") or ("0" * 64),
                        "claim_span": f"{adapter.name} evidence for {profile.get('name', org)}",
                    })

            for claim in extracted:
                field = claim["field"]
                # Conflict resolution: higher priority adapters supersede lower priority
                if field not in claims_map or claim.get("availability") == "available":
                    claims_map[field] = claim

        return list(claims_map.values()), evidence_items
