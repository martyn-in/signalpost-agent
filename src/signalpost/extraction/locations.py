"""Location extraction distinguishing registered offices and operational subunits."""

from __future__ import annotations

from typing import Any


def format_norwegian_address(address_dict: dict[str, Any] | None) -> str | None:
    """Format Brreg address object into a human-readable Norwegian address."""
    if not address_dict or not isinstance(address_dict, dict):
        return None

    lines = list(address_dict.get("adresse") or [])
    postcode = address_dict.get("postnummer")
    city = address_dict.get("poststed") or address_dict.get("kommune")
    country = address_dict.get("land") or "Norge"

    parts = []
    if lines:
        parts.append(", ".join(lines))
    if postcode and city:
        parts.append(f"{postcode} {city}")
    elif city:
        parts.append(city)
    if country and country != "Norge":
        parts.append(country)

    return ", ".join(parts) if parts else None


def extract_locations(
    entity_body: dict[str, Any],
    subunits_body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Extract registered business address, postal address, and operational subunits."""
    business_addr = entity_body.get("forretningsadresse")
    postal_addr = entity_body.get("postadresse")

    locations: list[dict[str, Any]] = []

    # Registered business address
    if business_addr:
        formatted = format_norwegian_address(business_addr)
        if formatted:
            locations.append({
                "type": "registered_office",
                "address": formatted,
                "municipality": business_addr.get("kommune"),
                "municipality_number": business_addr.get("kommunenummer"),
                "postal_code": business_addr.get("postnummer"),
                "city": business_addr.get("poststed"),
            })

    # Postal address (if distinct)
    if postal_addr:
        formatted_postal = format_norwegian_address(postal_addr)
        if formatted_postal and formatted_postal != format_norwegian_address(business_addr):
            locations.append({
                "type": "postal_address",
                "address": formatted_postal,
                "municipality": postal_addr.get("kommune"),
                "municipality_number": postal_addr.get("kommunenummer"),
                "postal_code": postal_addr.get("postnummer"),
                "city": postal_addr.get("poststed"),
            })

    # Subunits (operational branch locations)
    if subunits_body and isinstance(subunits_body, dict):
        subunits_list = (subunits_body.get("_embedded") or {}).get("underenheter") or []
        for sub in subunits_list:
            sub_addr = sub.get("beliggenhetsadresse") or sub.get("postadresse")
            locations.append({
                "type": "subunit",
                "organisation_number": sub.get("organisasjonsnummer"),
                "name": sub.get("navn"),
                "address": format_norwegian_address(sub_addr),
                "employees": sub.get("antallAnsatte"),
                "industry": (sub.get("naeringskode1") or {}).get("kode"),
            })

    return {"locations": locations}
