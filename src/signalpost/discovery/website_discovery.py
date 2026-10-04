"""Bounded autonomous discovery of official company websites.

Discovery is deliberately conservative: guessed domains are never published directly.
Every candidate is fetched through the existing safe crawler and must pass the existing
exact-company identity gate before it can become evidence.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Any

from norway_company_agent.identity import apply_website_identity_gate
from norway_company_agent.website import fetch_website

LEGAL_SUFFIXES = {
    "as", "asa", "enk", "da", "ans", "nuf", "sa", "ba", "iks", "kf", "fkf",
    "brl", "esek", "orgl", "sti", "stiftelsen",
}
GENERIC_TAILS = {
    "holding", "invest", "eiendom", "group", "gruppen", "norge", "norway",
    "technologies", "technology", "solutions", "consulting", "drift", "service",
    "tjenester", "utvikling",
}
CITY_TOKENS = {
    "oslo", "bergen", "trondheim", "stavanger", "kristiansand", "drammen",
    "sandnes", "fredrikstad", "tromso", "alesund", "kristiansund", "tonsberg",
    "bodo", "haugesund", "moss", "narvik", "arendal", "molde", "hamar",
    "halden", "horten", "lillehammer", "gjovik",
}


def _ascii_tokens(value: str | None) -> list[str]:
    text = str(value or "").casefold().translate(str.maketrans({"æ": "ae", "ø": "o", "å": "a"}))
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    return [t for t in re.findall(r"[a-z0-9]+", text) if t and t not in LEGAL_SUFFIXES]


def generate_domain_candidates(name: str, municipality: str | None = None) -> list[str]:
    """Generate a small, high-value set of plausible .no/.com official domains."""
    tokens = _ascii_tokens(name)
    if not tokens:
        return []
    muni = "".join(_ascii_tokens(municipality))
    bases: list[str] = []

    def add(base: str) -> None:
        base = re.sub(r"[^a-z0-9-]", "", base).strip("-")
        if len(base) >= 3 and base not in bases:
            bases.append(base)

    # Prefer a city-stripped or generic-tail-stripped brand before long legal names.
    trimmed = list(tokens)
    if len(trimmed) > 1 and (trimmed[-1] in CITY_TOKENS or (muni and trimmed[-1] == muni)):
        trimmed = trimmed[:-1]
    if len(trimmed) > 1 and trimmed[-1] in GENERIC_TAILS:
        add("".join(trimmed[:-1]))
        add(trimmed[0])

    add("".join(trimmed))
    if len(trimmed) >= 2:
        add("".join(trimmed[:2]))
        add("-".join(trimmed[:2]))
    if len(trimmed[0]) >= 4 and trimmed[0] not in GENERIC_TAILS:
        add(trimmed[0])
    add("-".join(trimmed))

    urls: list[str] = []
    for base in bases:
        for tld in (".no", ".com"):
            for prefix in ("https://www.", "https://"):
                url = f"{prefix}{base}{tld}"
                if url not in urls:
                    urls.append(url)
    return urls


def discover_and_verify_website(
    profile: dict[str, Any],
    *,
    timeout: float = 5.0,
    max_candidates_to_probe: int = 4,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Probe bounded domain candidates and return only an identity-verified website."""
    metrics = {"requests": 0, "bytes": 0, "latencies_ms": [], "candidates_probed": 0}
    existing = str(profile.get("website") or "").strip()
    candidates = ([existing] if existing else []) + generate_domain_candidates(
        str(profile.get("name") or ""), str(profile.get("municipality") or "") or None
    )
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if metrics["candidates_probed"] >= max_candidates_to_probe:
            break
        metrics["candidates_probed"] += 1
        try:
            record, m = fetch_website(candidate, timeout=timeout)
        except Exception:
            continue
        metrics["requests"] += int(m.get("requests", 0) or 0)
        metrics["bytes"] += int(m.get("bytes", 0) or 0)
        metrics["latencies_ms"].extend(m.get("latencies_ms", []) or [])
        gated = apply_website_identity_gate(profile, record)
        assessment = gated.get("assessment") or {}
        verified = gated.get("website")
        if verified and verified.get("status") == "available" and assessment.get("publishable"):
            return verified, metrics
    return None, metrics
