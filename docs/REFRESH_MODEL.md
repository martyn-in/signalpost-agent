# Refresh Model & Idempotent Change Detection

In the Builderr Signalpost challenge, **refresh correctness (20 points)** evaluates an agent's ability to re-crawl companies over time, identify real business changes, preserve historical evidence, and maintain strict idempotency.

---

## 1. Core Refresh Principles

1. **Strict Idempotency**: Running against identical source snapshots must result in:
   - Zero duplicate facts.
   - Zero false change events.
   - 100% preservation of identical semantic fingerprints.
2. **Historical Evidence Preservation**: When a fact changes (e.g. CEO appointment), previous values and their supporting evidence records are never overwritten or deleted. They remain archived with `first_seen_at` and `last_seen_at` bounds.
3. **Source Failure $\ne$ Business Change**: If an external endpoint returns HTTP 404, 500, or a timeout during a refresh run, this is recorded as `unobserved_this_run` or `source_error`. It is **never** treated as evidence that the company's website was decommissioned or that an executive resigned.

---

## 2. Fact Fingerprinting

Every extracted claim is assigned a deterministic **semantic fingerprint**:
$$\text{Fingerprint} = \text{SHA-256}(\text{org\_number} \parallel \text{category} \parallel \text{field} \parallel \text{normalized\_value} \parallel \text{reporting\_period})$$

**Important Normalizations:**
- Strings are trimmed, Unicode normalized (NFKD), and normalized for case.
- Numerical financial values are converted to standard float scales (NOK base).
- Retrieval timestamps and random request IDs are explicitly **excluded** from the semantic fingerprint calculation to ensure snapshot stability.

---

## 3. Change Event Types

When comparing a previous profile snapshot $P_{t-1}$ against a new profile snapshot $P_t$, the diff engine categorizes changes into typed events:

| Change Type | Trigger Condition | Materiality |
| :--- | :--- | :--- |
| **`new_fact`** | Field was previously missing or not found; now observed with valid evidence. | Standard |
| **`value_updated`** | Field value changed (e.g. employee count grew from 25 to 30; registered address changed). | High |
| **`role_changed`** | Executive or board member changed (e.g. new daglig leder appointed in registry). | High |
| **`financial_update`** | New annual account period filed (e.g. 2024 accounts updated to 2025 accounts). | High |
| **`job_closed`** | Job posting previously active is no longer present on the verified careers page after successful 200 OK crawl. | Medium |
| **`unchanged`** | Fingerprint and normalized value match prior run exactly. | None (No event emitted) |

---

## 4. Change Record Schema

```json
{
  "event_id": "evt-923609016-roles-ceo-2026",
  "organisation_number": "923609016",
  "field": "roles.daglig_leder",
  "change_type": "role_changed",
  "old_value": "Ola Nordmann",
  "new_value": "Kari Nordmann",
  "effective_at": "2026-08-15",
  "detected_at": "2026-08-24T06:00:00Z",
  "old_evidence_id": "ev-old-441",
  "new_evidence_id": "ev-new-892",
  "old_content_sha256": "3a8f...",
  "new_content_sha256": "7c1e...",
  "source_url": "https://data.brreg.no/enhetsregisteret/api/enheter/923609016/roller"
}
```
