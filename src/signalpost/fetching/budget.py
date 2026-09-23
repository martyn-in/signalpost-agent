"""Global request budget and cost accounting."""

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

    @property
    def total_network_attempts(self) -> int:
        return self.requests_made + self.redirects_followed + self.retries_attempted

    def can_request(self, priority: str = "normal") -> bool:
        with self._lock:
            if self.total_network_attempts >= self.max_requests:
                return False
            if priority == "low" and self.total_network_attempts >= self.soft_limit:
                return False
            if self.cost_spent_usd >= self.max_cost_usd:
                return False
            return True

    def record_request(
        self,
        *,
        is_redirect: bool = False,
        is_retry: bool = False,
        bytes_count: int = 0,
    ) -> None:
        with self._lock:
            if is_redirect:
                self.redirects_followed += 1
            elif is_retry:
                self.retries_attempted += 1
            else:
                self.requests_made += 1
            self.bytes_downloaded += bytes_count

    def record_cache_hit(self, bytes_count: int = 0) -> None:
        with self._lock:
            self.cache_hits += 1
            self.bytes_downloaded += bytes_count

    def record_cost(self, amount_usd: float) -> None:
        with self._lock:
            self.cost_spent_usd += round(amount_usd, 5)

    def summary(self) -> dict[str, Any]:
        with self._lock:
            return {
                "requests_made": self.requests_made,
                "redirects_followed": self.redirects_followed,
                "retries_attempted": self.retries_attempted,
                "total_outbound_requests": self.total_network_attempts,
                "cache_hits": self.cache_hits,
                "bytes_downloaded": self.bytes_downloaded,
                "cost_spent_usd": round(self.cost_spent_usd, 4),
                "remaining_budget": max(0, self.max_requests - self.total_network_attempts),
                "soft_limit_reached": self.total_network_attempts >= self.soft_limit,
                "hard_limit_reached": self.total_network_attempts >= self.max_requests,
            }
