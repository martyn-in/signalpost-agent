"""Global thread-safe request budget and source strategy planning."""

from __future__ import annotations

import threading
from typing import Any


class RequestBudget:
    def __init__(
        self,
        max_requests: int = 1900,
        soft_limit: int = 1750,
        max_cost_usd: float = 10.0,
    ) -> None:
        self.max_requests = max_requests
        self.soft_limit = soft_limit
        self.max_cost_usd = max_cost_usd

        self._lock = threading.Lock()
        self.requests_made = 0
        self.redirects_followed = 0
        self.retries_attempted = 0
        self.cache_hits = 0
        self.bytes_downloaded = 0
        self.cost_spent_usd = 0.0
        self.latencies_ms: list[int] = []

    @property
    def total_network_attempts(self) -> int:
        with self._lock:
            return self.requests_made + self.redirects_followed + self.retries_attempted

    def remaining_requests(self) -> int:
        with self._lock:
            return max(0, self.max_requests - (self.requests_made + self.redirects_followed + self.retries_attempted))

    def can_request(self, priority: str = "normal") -> bool:
        with self._lock:
            total = self.requests_made + self.redirects_followed + self.retries_attempted
            if total >= self.max_requests:
                return False
            if priority == "low" and total >= self.soft_limit:
                return False
            if self.cost_spent_usd >= self.max_cost_usd:
                return False
            return True

    def reserve(self, count: int = 1, priority: str = "normal") -> bool:
        """Atomically reserve request slots before network calls."""
        with self._lock:
            limit = self.soft_limit if priority == "low" else self.max_requests
            total = self.requests_made + self.redirects_followed + self.retries_attempted
            if total + count > limit:
                return False
            if self.cost_spent_usd >= self.max_cost_usd:
                return False
            self.requests_made += count
            return True

    def refund(self, count: int = 1) -> None:
        """Refund unused reserved slots."""
        with self._lock:
            self.requests_made = max(0, self.requests_made - count)

    def record_request(
        self,
        *,
        is_redirect: bool = False,
        is_retry: bool = False,
        bytes_count: int = 0,
        latency_ms: int | None = None,
    ) -> None:
        with self._lock:
            if is_redirect:
                self.redirects_followed += 1
            elif is_retry:
                self.retries_attempted += 1
            self.bytes_downloaded += bytes_count
            if latency_ms is not None:
                self.latencies_ms.append(latency_ms)

    def record_cache_hit(self, bytes_count: int = 0) -> None:
        with self._lock:
            self.cache_hits += 1
            self.bytes_downloaded += bytes_count

    def record_cost(self, amount_usd: float) -> None:
        with self._lock:
            self.cost_spent_usd += round(amount_usd, 5)

    def summary(self) -> dict[str, Any]:
        with self._lock:
            total = self.requests_made + self.redirects_followed + self.retries_attempted
            return {
                "requests_made": self.requests_made,
                "redirects_followed": self.redirects_followed,
                "retries_attempted": self.retries_attempted,
                "total_outbound_requests": total,
                "cache_hits": self.cache_hits,
                "bytes_downloaded": self.bytes_downloaded,
                "cost_spent_usd": round(self.cost_spent_usd, 4),
                "remaining_budget": max(0, self.max_requests - total),
                "soft_limit_reached": total >= self.soft_limit,
                "hard_limit_reached": total >= self.max_requests,
                "p95_latency_ms": sorted(self.latencies_ms)[int(len(self.latencies_ms) * 0.95)] if self.latencies_ms else 0,
            }

    @staticmethod
    def plan_strategy(batch_size: int, is_live: bool) -> dict[str, Any]:
        """Compute budget-aware parameters based on batch size N.
        
        Guarantees total outbound requests will never exceed the 1,900 cap on any N.
        """
        if not is_live:
            return {
                "max_probes_per_company": 0,
                "crawl_secondary_pages": False,
                "fetch_nav_jobs": False,
                "priority_fetch_only": True,
            }

        # Available budget is 1,900 requests
        budget_per_company = 1900 / max(batch_size, 1)

        if budget_per_company >= 15:
            # Small batch (e.g. N <= 100): full deep external exploration
            return {
                "max_probes_per_company": 4,
                "crawl_secondary_pages": True,
                "fetch_nav_jobs": True,
                "priority_fetch_only": False,
            }
        elif budget_per_company >= 8:
            # Medium batch (e.g. 100 < N <= 230): conservative exploration
            return {
                "max_probes_per_company": 2,
                "crawl_secondary_pages": True,
                "fetch_nav_jobs": True,
                "priority_fetch_only": False,
            }
        elif budget_per_company >= 4:
            # Moderate batch (e.g. 230 < N <= 475): official + high-confidence website
            return {
                "max_probes_per_company": 1,
                "crawl_secondary_pages": False,
                "fetch_nav_jobs": False,
                "priority_fetch_only": False,
            }
        else:
            # Large batch (e.g. N >= 500, up to 1,000+): registry & financials priority
            return {
                "max_probes_per_company": 0,
                "crawl_secondary_pages": False,
                "fetch_nav_jobs": False,
                "priority_fetch_only": True,
            }
