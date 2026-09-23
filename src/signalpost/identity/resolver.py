"""Strict company entity resolution and website verification."""

from __future__ import annotations

import re
import unicodedata
import urllib.parse
from typing import Any

LEGAL_AND_GENERIC_TOKENS = {
    "as", "asa", "ans", "da", "enk", "iks", "sa", "sam", "sti", "stiftelsen",
    "nuf", "ab", "b", "v", "limited", "ltd", "inc", "plc", "the", "og", "and",
}

PARKED_MARKERS = (
    "domain is for sale",
    "domain for sale",
    "hugedomains",
    "parked at",
    "miss hosting",
    "her flytter snart en ny gjest",
    "has been informing visitors",
    "find the best information and most relevant links on all topics related to",
    "buy this domain",
)


def extract_tokens(text: Any) -> list[str]:
    """Normalize text and extract non-generic word tokens."""
    raw = str(text or "").translate(str.maketrans({"ø": "o", "Ø": "O", "å": "a", "Å": "A", "æ": "ae", "Æ": "AE"}))
    normalized = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode().casefold()
    tokens = re.findall(r"[a-z0-9]+", normalized)
    return [t for t in tokens if t not in LEGAL_AND_GENERIC_TOKENS and len(t) > 1]


def extract_norwegian_org_numbers(text: str) -> set[str]:
    """Find all potential 9-digit Norwegian organisation numbers."""
    cleaned = re.sub(r"(?<=\d)\s(?=\d)", "", text)
    matches = re.findall(r"\b[89]\d{8}\b", cleaned)
    return set(matches)


def assess_website_identity(
    company_name: str,
    target_org_number: str,
    page_data: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate whether candidate web page belongs to target Norwegian entity.
    
    Implements hard rejection for conflicting organisation numbers and parked domains.
    """
    target_tokens = extract_tokens(company_name)
    target_org_digits = re.sub(r"\D", "", str(target_org_number or ""))

    title = str(page_data.get("title") or "")
    description = str(page_data.get("description") or "")
    text_sample = str(page_data.get("text") or page_data.get("main_text_excerpt") or "")
    structured_names = page_data.get("structured_names") or []
    if isinstance(structured_names, list):
        structured_text = " ".join(str(s) for s in structured_names)
    else:
        structured_text = ""

    candidate_full_text = f"{title} {description} {structured_text} {text_sample}"
    normalized_candidate = unicodedata.normalize("NFKD", candidate_full_text).encode("ascii", "ignore").decode().casefold()

    reasons: list[str] = []

    # 1. Parked / For-Sale Domain Hard Check
    if any(marker in normalized_candidate for marker in PARKED_MARKERS):
        return {
            "status": "rejected",
            "score": 0.1,
            "publishable": False,
            "reasons": ["Domain is a parked, for-sale, or generic registrar placeholder"],
            "matched_tokens": [],
        }

    # 2. Conflicting Organisation Number Check (HARD REJECTION)
    candidate_org_numbers = extract_norwegian_org_numbers(candidate_full_text)
    if candidate_org_numbers and target_org_digits:
        if target_org_digits not in candidate_org_numbers and any(
            candidate_org != target_org_digits for candidate_org in candidate_org_numbers
        ):
            return {
                "status": "rejected",
                "score": 0.0,
                "publishable": False,
                "reasons": [
                    f"Conflicting organisation number detected: {candidate_org_numbers} vs target {target_org_digits}"
                ],
                "matched_tokens": [],
            }

    # 3. Exact Organisation Number Match (GOLD STANDARD)
    compact_candidate = re.sub(r"\D", "", candidate_full_text)
    if target_org_digits and target_org_digits in compact_candidate:
        return {
            "status": "exact",
            "score": 1.0,
            "publishable": True,
            "reasons": ["Exact target organisation number verified on website"],
            "matched_tokens": target_tokens,
        }

    # 4. Token Overlap & Distinctive Legal Name Match
    candidate_tokens = set(extract_tokens(candidate_full_text))
    overlap = sorted(set(target_tokens) & candidate_tokens)
    ratio = len(overlap) / len(set(target_tokens)) if target_tokens else 0.0

    homepage_identity_parts = [title, description, structured_text]
    homepage_token_sets = [set(extract_tokens(part)) for part in homepage_identity_parts if part]
    exact_homepage_name = bool(target_tokens and any(set(target_tokens).issubset(toks) for toks in homepage_token_sets))
    substantive_content = len(text_sample.strip()) >= 80

    if len(target_tokens) >= 2 and exact_homepage_name:
        score = 0.95
        reasons.append("All normalized legal name tokens appear together in homepage identity headers")
    elif len(target_tokens) == 1 and exact_homepage_name and substantive_content:
        score = 0.90
        reasons.append("Single distinctive legal name token verified in identity headers with substantive content")
    elif ratio >= 0.75 and len(overlap) >= 2:
        score = 0.85
        reasons.append("Majority of legal name tokens present; lacks exact organisation number confirmation")
    elif ratio >= 0.5:
        score = 0.60
        reasons.append("Partial name overlap only; uncertain match")
    else:
        score = 0.30
        reasons.append("Lacks sufficient distinctive legal identity evidence")

    status = "exact" if score >= 0.90 else "review" if score >= 0.80 else "related_or_uncertain"

    return {
        "status": status,
        "score": score,
        "publishable": status == "exact",
        "reasons": reasons,
        "matched_tokens": overlap,
    }
