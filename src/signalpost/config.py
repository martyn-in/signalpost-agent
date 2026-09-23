"""Configuration and environment settings for Signalpost."""

from __future__ import annotations

import os
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Settings:
    # Evaluation Constraints
    batch_size: int = 100
    max_requests_global: int = 1900  # Hard internal safety cap below Builderr's 2,000 limit
    soft_requests_cap: int = 1750    # Haults optional/low-priority crawls
    max_requests_per_company: int = 18
    max_api_cost_usd: float = 10.0

    # Network Timeouts (Seconds)
    timeout_connect: float = 5.0
    timeout_read: float = 10.0
    timeout_total: float = 15.0
    max_concurrency: int = 12
    per_domain_concurrency: int = 2

    # Storage & Cache
    cache_dir: Path = field(default_factory=lambda: Path(os.environ.get("CACHE_DIR", "data/cache")))
    data_dir: Path = field(default_factory=lambda: Path("data"))

    # Security & Politeness
    user_agent: str = os.environ.get(
        "HTTP_USER_AGENT",
        "SignalpostAgent/1.0 (+https://builderr.ai/challenges/signalpost; bot@builderr.ai)"
    )
    max_body_bytes: int = 5 * 1024 * 1024  # 5 MB max HTML
    max_pdf_bytes: int = 15 * 1024 * 1024  # 15 MB max PDF

    # Optional External Integrations (Default $0)
    search_api_key: str | None = os.environ.get("SEARCH_API_KEY")
    llm_api_key: str | None = os.environ.get("LLM_API_KEY")
    llm_model: str = os.environ.get("LLM_MODEL", "gpt-4o-mini")

    log_level: str = os.environ.get("LOG_LEVEL", "INFO")


settings = Settings()
