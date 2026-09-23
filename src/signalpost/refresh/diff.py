"""Idempotent change detection and historical evidence preservation."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from norway_company_agent.refresh import (
    TRACKED_FIELDS,
    _evidence_for,
    _read,
    diff_datasets,
    diff_profile,
)


def compute_semantic_fingerprint(
    organisation_number: str,
    field: str,
    value: Any,
    reporting_period: str | None = None,
) -> str:
    """Compute stable SHA-256 fingerprint for a semantic fact (excluding retrieval dates)."""
    normalized_val = json.dumps(value, sort_keys=True, ensure_ascii=False)
    payload = f"{organisation_number}:{field}:{normalized_val}:{reporting_period or ''}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def detect_typed_changes(
    previous: dict[str, Any],
    current: dict[str, Any],
) -> list[dict[str, Any]]:
    """Compare previous and current profiles, emitting typed change records.
    
    Guarantees idempotence: identical profiles produce zero change events.
    """
    raw_changes = diff_profile(previous, current)
    typed_changes: list[dict[str, Any]] = []

    for change in raw_changes:
        field = change["field"]
        old_val = change["old_value"]
        new_val = change["new_value"]

        # Classify change type
        if old_val is None and new_val is not None:
            change_type = "new_fact"
        elif "roles" in field:
            change_type = "role_changed"
        elif "financial" in field:
            change_type = "financial_update"
        elif "employees" in field:
            change_type = "workforce_updated"
        elif "website" in field:
            change_type = "website_updated"
        else:
            change_type = "value_updated"

        # Unique stable event id
        event_id = hashlib.sha256(
            f"{change['organisation_number']}:{field}:{change.get('new_content_sha256')}".encode()
        ).hexdigest()[:16]

        typed_changes.append({
            "event_id": f"evt-{event_id}",
            "change_type": change_type,
            **change,
        })

    return typed_changes
