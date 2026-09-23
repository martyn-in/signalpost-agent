"""Executive and board leadership extraction and role normalization."""

from __future__ import annotations

from typing import Any

ROLE_NORMALIZATION = {
    "daglig leder": "ceo",
    "administrerende direktør": "ceo",
    "generalsekretær": "general_secretary",
    "styreleder": "board_chair",
    "styrets leder": "board_chair",
    "nestleder": "board_deputy_chair",
    "styremedlem": "board_member",
    "varamedlem": "deputy_board_member",
    "revisor": "auditor",
    "regnskapsfører": "accountant",
}


def normalize_role_title(raw_role: str | None) -> str:
    if not raw_role:
        return "other"
    cleaned = raw_role.strip().casefold()
    for norwegian_pattern, normalized in ROLE_NORMALIZATION.items():
        if norwegian_pattern in cleaned:
            return normalized
    return "other"


def extract_people_from_roles_api(roles_body: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse Brønnøysundregistrene /roller JSON response into normalized leadership records."""
    people: list[dict[str, Any]] = []
    groups = roles_body.get("rollegrupper", []) if isinstance(roles_body, dict) else []

    for group in groups:
        group_type = group.get("type", {})
        group_desc = group_type.get("beskrivelse") if isinstance(group_type, dict) else str(group_type)
        last_changed = group.get("sistEndret")

        for role_item in group.get("roller", []):
            role_type = role_item.get("type", {})
            raw_role = role_type.get("beskrivelse") if isinstance(role_type, dict) else str(role_type)
            role_code = role_type.get("kode") if isinstance(role_type, dict) else None

            person = role_item.get("person") or {}
            person_name = person.get("navn") or {}
            entity = role_item.get("enhet") or {}

            full_name = " ".join(
                filter(None, [
                    person_name.get("fornavn"),
                    person_name.get("mellomnavn"),
                    person_name.get("etternavn"),
                ])
            ) or entity.get("navn")

            if not full_name:
                continue

            people.append({
                "name": full_name.strip(),
                "raw_role": raw_role,
                "normalized_role": normalize_role_title(raw_role),
                "role_code": role_code,
                "role_group": group_desc,
                "inactive": bool(role_item.get("avregistrert")),
                "last_changed": last_changed,
            })

    return people
