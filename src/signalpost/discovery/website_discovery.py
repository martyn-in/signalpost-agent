"""Bounded autonomous discovery of official company websites.

Discovery is deliberately conservative: guessed domains are never published directly.
Every candidate is fetched through the safe crawler and must pass the exact-company
identity gate before it can become evidence.
"""

from __future__ import annotations

import re
import unicodedata
import urllib.parse
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
    "tjenester", "utvikling", "forvaltning", "kapital", "finans",
}
GENERIC_PREFIXES = {
    "arkitektfirma", "advokatfirma", "byggmester", "entreprenor", "malermester",
    "rorlegger", "elektro", "tannlege", "regnskapskontor", "revisjon",
    "hotell", "restaurant", "klinikk", "transport", "maskin", "bilverksted",
}
COMPOUND_DOMAIN_ROOTS = {
    "trevarefabrikk": "trevare",
    "elektriske": "elektrisk",
    "rørleggerforretning": "ror",
    "rorleggerforretning": "ror",
}
GENERIC_EMAIL_HOSTS = {
    "gmail.com", "hotmail.com", "outlook.com", "live.com", "icloud.com",
    "yahoo.com", "online.no", "broadpark.no", "start.no",
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


def _norwegian_translit_variants(name: str) -> list[str]:
    """Generate Norwegian name transliteration variants (e.g. å->aa, ø->oe)."""
    raw = str(name or "").casefold()
    variants = [raw]
    if "å" in raw or "ø" in raw or "æ" in raw:
        v1 = raw.replace("å", "aa").replace("ø", "oe").replace("æ", "ae")
        if v1 not in variants:
            variants.append(v1)
    return variants


def _authoritative_site_candidates(value: str) -> list[str]:
    """Return bare + www variants for a registry/contact-derived domain hint."""
    raw = str(value or "").strip()
    if not raw:
        return []
    normalized = raw if re.match(r"^https?://", raw, re.I) else "https://" + raw
    try:
        parsed = urllib.parse.urlparse(normalized)
    except ValueError:
        return [raw]
    host = (parsed.hostname or "").strip(".")
    if not host:
        return [raw]
    scheme = parsed.scheme or "https"
    port = f":{parsed.port}" if parsed.port else ""
    path = parsed.path or "/"
    query = parsed.query
    out = [urllib.parse.urlunparse((scheme, host + port, path, "", query, ""))]
    if not host.casefold().startswith("www."):
        out.append(urllib.parse.urlunparse((scheme, "www." + host + port, path, "", query, "")))
    return out


def generate_domain_candidates(name: str, municipality: str | None = None) -> list[str]:
    """Generate a high-value set of plausible .no/.com official domains."""
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
        rooted = [COMPOUND_DOMAIN_ROOTS.get(t, t) for t in trimmed]
        add("".join(rooted))
        add("".join(trimmed[:2]))
        add("-".join(trimmed[:2]))
    if len(trimmed[0]) >= 4 and trimmed[0] not in GENERIC_TAILS:
        add(trimmed[0])
    add("-".join(trimmed))

    # Generic prefix stripping (e.g. "arkitektfirma jon vikoren" -> "jonvikoren", "vikoren")
    if len(trimmed) >= 2 and trimmed[0] in GENERIC_PREFIXES:
        sub = trimmed[1:]
        add("".join(sub))
        add("-".join(sub))
        if len(sub) >= 2:
            add(sub[-1])

    # Transliteration variant check (aa for å, oe for ø)
    for variant in _norwegian_translit_variants(name):
        var_toks = _ascii_tokens(variant)
        if var_toks and var_toks != tokens:
            add("".join(var_toks))
            if len(var_toks) >= 2:
                add("-".join(var_toks[:2]))

    urls: list[str] = []
    for base in bases:
        for tld in (".no", ".com"):
            url = f"https://{base}{tld}"
            if url not in urls:
                urls.append(url)
    return urls


def discover_and_verify_website(
    profile: dict[str, Any],
    *,
    timeout: float = 5.0,
    max_candidates_to_probe: int = 4,
    budget: Any = None,
) -> tuple[dict[str, Any] | None, dict[str, Any]]:
    """Probe bounded domain candidates and return only an identity-verified website."""
    metrics = {"requests": 0, "bytes": 0, "latencies_ms": [], "candidates_probed": 0}
    existing = str(profile.get("website") or profile.get("hjemmeside") or "").strip()
    candidates: list[str] = [existing] if existing else []

    # Brreg contact fields are authoritative discovery hints. A corporate email
    # domain or subunit homepage is much higher value than a guessed domain, but
    # still has to pass the same exact-company website identity gate.
    reg_live = ((profile.get("evidence") or {}).get("registry_live") or {}).get("value") or {}
    locations = (((profile.get("evidence") or {}).get("locations") or {}).get("value") or {}).get("locations") or []
    hint_rows = [profile, reg_live] + [row for row in locations if isinstance(row, dict)]
    for row in hint_rows:
        site = str(row.get("website") or row.get("hjemmeside") or "").strip()
        if site:
            candidates.extend(_authoritative_site_candidates(site))
        email = str(row.get("email") or row.get("epostadresse") or "").strip().casefold()
        if "@" in email:
            host = email.rsplit("@", 1)[-1].strip(".")
            if host and host not in GENERIC_EMAIL_HOSTS and "." in host:
                candidates.extend(_authoritative_site_candidates(host))

    candidates.extend(generate_domain_candidates(
        str(profile.get("name") or ""), str(profile.get("municipality") or "") or None
    ))
    seen: set[str] = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if metrics["candidates_probed"] >= max_candidates_to_probe:
            break

        # Budget gate: reserve 2 requests for probing this candidate
        if budget is not None and not budget.reserve(2, priority="low"):
            break

        metrics["candidates_probed"] += 1
        try:
            record, m = fetch_website(candidate, timeout=timeout)
        except Exception:
            if budget is not None:
                budget.refund(2)
            continue

        reqs = int(m.get("requests", 0) or 0)
        metrics["requests"] += reqs
        metrics["bytes"] += int(m.get("bytes", 0) or 0)
        metrics["latencies_ms"].extend(m.get("latencies_ms", []) or [])

        # Adjust budget if actual requests differed from reservation
        if budget is not None:
            if reqs < 2:
                budget.refund(2 - reqs)
            elif reqs > 2:
                budget.reserve(reqs - 2)

        gated = apply_website_identity_gate(profile, record)
        assessment = gated.get("assessment") or {}
        verified = gated.get("website")
        if verified and verified.get("status") == "available" and assessment.get("publishable"):
            return verified, metrics
    return None, metrics
