"""Base architecture for modular source adapters, source health monitoring, and request-value scoring."""

from __future__ import annotations

import abc
import datetime
import hashlib
import time
from typing import Any


def utc_now() -> str:
    """Return ISO-8601 current UTC timestamp with trailing Z."""
    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_hash(content: str | bytes) -> str:
    """Return 64-character SHA-256 hexadecimal hash."""
    if isinstance(content, str):
        content = content.encode("utf-8", errors="replace")
    return hashlib.sha256(content).hexdigest()


class SourceHealthMonitor:
    """Monitors the operational health, latency percentiles, and error rates of adapters.
    
    Provides circuit breaker protection against downstream failures or aggressive rate limits.
    """

    def __init__(self, failure_threshold: int = 4, recovery_seconds: float = 30.0) -> None:
        self.failure_threshold = failure_threshold
        self.recovery_seconds = recovery_seconds
        self._stats: dict[str, dict[str, Any]] = {}

    def _get_entry(self, source_name: str) -> dict[str, Any]:
        if source_name not in self._stats:
            self._stats[source_name] = {
                "requests": 0,
                "successes": 0,
                "errors": 0,
                "consecutive_failures": 0,
                "circuit_open_until": 0.0,
                "latencies_ms": [],
                "bytes_transferred": 0,
                "last_error": None,
            }
        return self._stats[source_name]

    def is_healthy(self, source_name: str) -> bool:
        entry = self._get_entry(source_name)
        if time.monotonic() < entry["circuit_open_until"]:
            return False
        return True

    def record_success(self, source_name: str, latency_ms: int, bytes_count: int = 0) -> None:
        entry = self._get_entry(source_name)
        entry["requests"] += 1
        entry["successes"] += 1
        entry["consecutive_failures"] = 0
        entry["bytes_transferred"] += bytes_count
        entry["latencies_ms"].append(latency_ms)
        if len(entry["latencies_ms"]) > 100:
            entry["latencies_ms"].pop(0)

    def record_failure(self, source_name: str, error_msg: str, latency_ms: int = 0) -> None:
        entry = self._get_entry(source_name)
        entry["requests"] += 1
        entry["errors"] += 1
        entry["consecutive_failures"] += 1
        entry["last_error"] = error_msg
        if latency_ms > 0:
            entry["latencies_ms"].append(latency_ms)
        if entry["consecutive_failures"] >= self.failure_threshold:
            entry["circuit_open_until"] = time.monotonic() + self.recovery_seconds

    def summary(self) -> dict[str, Any]:
        result = {}
        for name, data in self._stats.items():
            lats = sorted(data["latencies_ms"])
            p50 = lats[len(lats) // 2] if lats else 0
            p95 = lats[min(len(lats) - 1, int(len(lats) * 0.95))] if lats else 0
            result[name] = {
                "requests": data["requests"],
                "successes": data["successes"],
                "errors": data["errors"],
                "healthy": self.is_healthy(name),
                "p50_ms": p50,
                "p95_ms": p95,
                "last_error": data["last_error"],
            }
        return result


class RequestValueScorer:
    """Adaptive request-value scoring engine.
    
    Evaluates expected information yield per HTTP request based on company attributes
    to prioritize requests under constrained budgets.
    """

    @staticmethod
    def expected_value(adapter_name: str, profile: dict[str, Any], budget_remaining: int) -> float:
        """Compute relative value (0.0 - 100.0) for executing an adapter on a profile."""
        legal_form = str(profile.get("legal_form") or "").upper()
        emp = profile.get("employees")
        has_website = bool(profile.get("website"))
        accounts_year = profile.get("latest_submitted_accounts")

        # Official registers are foundation: highest score yield per request
        if adapter_name == "brreg_official":
            return 100.0

        if adapter_name == "brreg_financials":
            if legal_form in {"ENK", "FLI"} and not accounts_year:
                return 5.0  # Unlikely to have filed accounts
            return 85.0

        if adapter_name == "brreg_roles":
            # Roles are mandatory for AS/ASA/STI, less informative for ENK
            if legal_form in {"AS", "ASA", "STI", "BRL"}:
                return 75.0
            return 30.0

        if adapter_name == "brreg_subunits":
            # Subunits are most common for employers with > 1 employee or multi-branch
            if emp is not None and emp > 0:
                return 65.0
            return 25.0

        if adapter_name == "company_website":
            if has_website:
                return 70.0
            return 20.0

        if adapter_name == "public_news":
            # News has highest yield for larger or well-known entities
            if emp is not None and emp >= 10:
                return 40.0
            return 15.0

        if adapter_name == "public_reviews":
            # Reviews relevant for B2C / trade / consumer businesses
            return 25.0

        return 10.0


class BaseSourceAdapter(abc.ABC):
    """Abstract base class for all Signalpost source adapters."""

    def __init__(
        self,
        name: str,
        source_class: str,
        priority: int = 10,
        cost_usd_per_req: float = 0.0,
    ) -> None:
        self.name = name
        self.source_class = source_class
        self.priority = priority
        self.cost_usd_per_req = cost_usd_per_req

    @abc.abstractmethod
    def can_handle(self, profile: dict[str, Any]) -> bool:
        """Check if this adapter can process the given profile."""
        pass

    @abc.abstractmethod
    def fetch(
        self,
        profile: dict[str, Any],
        client: Any = None,
        budget: Any = None,
        monitor: SourceHealthMonitor | None = None,
    ) -> dict[str, Any]:
        """Fetch raw evidence from source or return cached/offline representation."""
        pass

    @abc.abstractmethod
    def extract_claims(
        self,
        evidence_record: dict[str, Any],
        profile: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Extract structured claims with cryptographic provenance from evidence."""
        pass
