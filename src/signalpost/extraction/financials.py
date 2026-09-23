"""Conservative, source-backed financial extraction and unit normalization."""

from __future__ import annotations

import re
from typing import Any


def parse_norwegian_number(raw: str | int | float | None, scale_multiplier: float = 1.0) -> float | None:
    """Parse a Norwegian numeric string, preserving signs, scale factors, and nulls.
    
    NEVER converts missing values to zero.
    """
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return float(raw) * scale_multiplier

    cleaned = str(raw).strip()
    if not cleaned or cleaned in {"-", "–", "—", "N/A", "n/a", "null"}:
        return None

    # Handle negative numbers wrapped in parentheses, e.g. (1 250) -> -1250
    is_negative = False
    if cleaned.startswith("(") and cleaned.endswith(")"):
        is_negative = True
        cleaned = cleaned[1:-1].strip()
    elif cleaned.startswith("-") or cleaned.startswith("−"):
        is_negative = True
        cleaned = cleaned[1:].strip()
    elif cleaned.endswith("-"):
        is_negative = True
        cleaned = cleaned[:-1].strip()

    # Remove non-breaking spaces and regular spaces used as thousands separators
    cleaned = cleaned.replace("\u00a0", "").replace(" ", "")

    # Replace Norwegian decimal comma with period
    if "," in cleaned and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned and "." in cleaned:
        # If both exist, standard Norwegian has period as thousands separator, comma as decimal
        if cleaned.rfind(",") > cleaned.rfind("."):
            cleaned = cleaned.replace(".", "").replace(",", ".")

    try:
        val = float(cleaned)
        if is_negative:
            val = -val
        return val * scale_multiplier
    except ValueError:
        return None


def detect_scale_factor(text: str) -> float:
    """Detect scale factor in Norwegian financial notes or table headers."""
    lowered = text.casefold()
    if any(m in lowered for m in ["i hele tusen", "i 1 000", "i 1000", "tusen nok", "nok 1000", "nok 1 000", "tkr", "t.kr"]):
        return 1_000.0
    if any(m in lowered for m in ["i millioner", "i mill", "mnok", "mill. nok"]):
        return 1_000_000.0
    return 1.0


def normalize_financial_statement(record: dict[str, Any], default_scale: float = 1.0) -> dict[str, Any]:
    """Normalize a Brreg annual accounts record into standard monetary units (NOK base)."""
    scale = detect_scale_factor(str(record.get("scale") or "")) if "scale" in record else default_scale

    def _extract_nested(data: dict, *keys: str) -> Any:
        cur: Any = data
        for k in keys:
            if not isinstance(cur, dict):
                return None
            cur = cur.get(k)
        return cur

    # Extract key accounting items
    revenue = parse_norwegian_number(
        record.get("revenue")
        or _extract_nested(record, "resultatregnskapResultat", "driftsresultat", "driftsinntekter", "sumDriftsinntekter"),
        scale,
    )
    operating_result = parse_norwegian_number(
        record.get("operating_result")
        or _extract_nested(record, "resultatregnskapResultat", "driftsresultat", "driftsresultat"),
        scale,
    )
    profit_before_tax = parse_norwegian_number(
        record.get("profit_before_tax")
        or _extract_nested(record, "resultatregnskapResultat", "ordinaertResultatFoerSkattekostnad"),
        scale,
    )
    annual_result = parse_norwegian_number(
        record.get("annual_result")
        or _extract_nested(record, "resultatregnskapResultat", "aarsresultat"),
        scale,
    )
    assets = parse_norwegian_number(
        record.get("assets")
        or _extract_nested(record, "eiendeler", "sumEiendeler"),
        scale,
    )
    equity = parse_norwegian_number(
        record.get("equity")
        or _extract_nested(record, "egenkapitalGjeld", "egenkapital", "sumEgenkapital"),
        scale,
    )
    debt = parse_norwegian_number(
        record.get("debt")
        or _extract_nested(record, "egenkapitalGjeld", "gjeldOversikt", "sumGjeld"),
        scale,
    )

    return {
        "record_id": record.get("id") or record.get("record_id"),
        "account_type": record.get("regnskapstype") or record.get("account_type"),
        "reporting_period": record.get("regnskapsperiode") or record.get("period"),
        "currency": record.get("valuta") or record.get("currency") or "NOK",
        "revenue": revenue,
        "operating_result": operating_result,
        "profit_before_tax": profit_before_tax,
        "annual_result": annual_result,
        "assets": assets,
        "equity": equity,
        "debt": debt,
    }
